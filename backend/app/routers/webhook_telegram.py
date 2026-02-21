import logging
import os
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Response
from app.config import settings
from app import database as db
from app.services.telegram import send_message, download_file
from app.services.transcription import transcribe_audio
from app.services.summarization import summarize_transcript
from app.services.customer_resolver import resolve_customer
from app.services.phone import normalize_phone
from app.utils.metrics import pipeline_metrics

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/webhook/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    # Validar secret token
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if secret != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(403, "Invalid webhook secret")

    payload = await request.json()
    message = payload.get("message", {})

    if not message:
        return Response(status_code=200)

    chat_id = message.get("chat", {}).get("id")
    if not chat_id:
        return Response(status_code=200)

    # Processar em background
    background_tasks.add_task(process_update, message, chat_id)
    return Response(status_code=200)


async def process_update(message: dict, chat_id: int):
    try:
        # Contato compartilhado
        if "contact" in message:
            await handle_contact(chat_id, message["contact"])
            return

        text = message.get("text", "")

        # Comandos
        if text.startswith("/start"):
            await handle_start(chat_id)
            return

        if text.startswith("/help"):
            await handle_help(chat_id)
            return

        # Texto com #gravar
        if "#gravar" in text.lower():
            await handle_gravar(chat_id, text)
            return

        # Áudio (voice ou document de áudio)
        voice = message.get("voice")
        audio = message.get("audio")
        document = message.get("document")

        file_id = None
        duration = None

        if voice:
            file_id = voice["file_id"]
            duration = voice.get("duration")
        elif audio:
            file_id = audio["file_id"]
            duration = audio.get("duration")
        elif document and document.get("mime_type", "").startswith("audio/"):
            file_id = document["file_id"]

        if file_id:
            await handle_audio(chat_id, file_id, duration, message.get("message_id", 0))
            return

        # Qualquer outro texto
        await send_message(chat_id, "Use /help para ver como registrar uma visita.", parse_mode=None)

    except Exception as e:
        logger.error(f"Error processing update for chat {chat_id}: {e}", exc_info=True)


async def handle_start(chat_id: int):
    keyboard = {
        "keyboard": [[{
            "text": "📱 Compartilhar meu contato",
            "request_contact": True,
        }]],
        "one_time_keyboard": True,
        "resize_keyboard": True,
    }
    await send_message(
        chat_id,
        "Olá! Para vincular sua conta, compartilhe seu contato usando o botão abaixo.",
        parse_mode=None,
        reply_markup=keyboard,
    )


async def handle_help(chat_id: int):
    await send_message(
        chat_id,
        "📋 *Como registrar uma visita:*\n\n"
        "1️⃣ Envie uma mensagem com:\n"
        "   Nome do Cliente\n"
        "   Produto\n"
        "   \\#gravar\n\n"
        "2️⃣ Em seguida, envie o áudio da visita\n\n"
        "⏱ Você tem 10 minutos entre o texto e o áudio.\n"
        "🎙 Áudio máximo: 10 minutos.",
    )


async def handle_contact(chat_id: int, contact: dict):
    phone = contact.get("phone_number", "")
    if not phone:
        await send_message(chat_id, "❌ Não consegui ler o número do contato.", parse_mode=None)
        return

    normalized = normalize_phone(phone)

    seller = await db.fetchone(
        """SELECT u.id, u.name, u.org_id, o.name as org_name
        FROM users u JOIN organizations o ON u.org_id = o.id
        WHERE u.phone_normalized = $1 AND u.role = 'seller' AND u.is_active = true""",
        [normalized],
    )

    if not seller:
        await send_message(
            chat_id,
            "❌ Número não cadastrado. Peça ao seu gestor para cadastrá-lo no portal SalesEcho.",
            parse_mode=None,
        )
        return

    # Vincular chat_id
    await db.execute(
        "UPDATE users SET telegram_chat_id = $1 WHERE id = $2",
        [chat_id, seller["id"]],
    )

    await send_message(
        chat_id,
        f"✅ Olá {seller['name']}! Você está vinculado à empresa {seller['org_name']}.\n\n"
        "ℹ️ Seus áudios serão transcritos e resumidos por IA para relatórios da sua empresa. "
        "Os áudios originais são deletados em até 24 horas. "
        "Em caso de dúvidas, fale com seu gestor.\n\n"
        "Use /help para ver como registrar uma visita.",
        parse_mode=None,
    )


async def handle_gravar(chat_id: int, text: str):
    # Verificar se seller está vinculado
    seller = await db.fetchone(
        "SELECT id, org_id, name FROM users WHERE telegram_chat_id = $1 AND role = 'seller' AND is_active = true",
        [chat_id],
    )
    if not seller:
        await send_message(
            chat_id,
            "❌ Número não vinculado. Envie /start para se cadastrar.",
            parse_mode=None,
        )
        return

    # Verificar subscription ativa
    sub = await db.fetchone(
        "SELECT status FROM subscriptions WHERE org_id = $1",
        [seller["org_id"]],
    )
    if not sub or sub["status"] not in ("trial", "active", "pending_payment"):
        await send_message(chat_id, "❌ Sua empresa não tem acesso ativo ao SalesEcho.", parse_mode=None)
        return

    # Parse: linhas antes de #gravar
    lines = []
    for line in text.split("\n"):
        if "#gravar" in line.lower():
            # Pegar texto antes de #gravar na mesma linha
            before = line[:line.lower().index("#gravar")].strip()
            if before:
                lines.append(before)
            break
        if line.strip():
            lines.append(line.strip())

    if len(lines) < 2:
        await send_message(
            chat_id,
            "❌ Formato incorreto. Envie:\n\nNome do Cliente\nProduto\n\\#gravar",
        )
        return

    customer_name = lines[0]
    product = lines[1]

    # UPSERT pending_session
    await db.execute(
        """INSERT INTO pending_sessions (telegram_chat_id, customer_name, product)
        VALUES ($1, $2, $3)
        ON CONFLICT (telegram_chat_id)
        DO UPDATE SET customer_name = $2, product = $3, created_at = now()""",
        [chat_id, customer_name, product],
    )

    await send_message(
        chat_id,
        f"✅ Sessão aberta para *{customer_name}* / *{product}*. Envie o áudio agora.",
    )


async def handle_audio(chat_id: int, file_id: str, duration: int | None, message_id: int):
    # Verificar seller vinculado
    seller = await db.fetchone(
        "SELECT id, org_id, name FROM users WHERE telegram_chat_id = $1 AND role = 'seller' AND is_active = true",
        [chat_id],
    )
    if not seller:
        return  # Ignora áudio de user não vinculado

    # Buscar sessão ativa (< 10 min)
    session = await db.fetchone(
        """SELECT customer_name, product FROM pending_sessions
        WHERE telegram_chat_id = $1
        AND created_at > now() - INTERVAL '10 minutes'""",
        [chat_id],
    )
    if not session:
        await send_message(
            chat_id,
            "❌ Nenhuma sessão ativa. Envie primeiro:\n\nNome do Cliente\nProduto\n\\#gravar",
        )
        return

    # Dedup check
    existing = await db.fetchone(
        "SELECT id FROM recordings WHERE seller_id = $1 AND telegram_message_id = $2",
        [seller["id"], message_id],
    )
    if existing:
        return  # Duplicata, ignora

    # Criar recording
    recording = await db.fetchone(
        """INSERT INTO recordings (org_id, seller_id, telegram_message_id, telegram_file_id,
            customer_name_raw, product_raw, audio_duration_sec, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, 'received')
        RETURNING id""",
        [seller["org_id"], seller["id"], message_id, file_id,
         session["customer_name"], session["product"], duration],
    )
    recording_id = str(recording["id"])

    # Limpar sessão
    await db.execute(
        "DELETE FROM pending_sessions WHERE telegram_chat_id = $1",
        [chat_id],
    )

    await send_message(chat_id, "🎙 Áudio recebido! Processando...", parse_mode=None)

    # Pipeline background
    await process_recording(recording_id, file_id, seller, session)


async def process_recording(recording_id: str, file_id: str, seller: dict, session: dict):
    try:
        # 1. Download
        os.makedirs(settings.AUDIO_TEMP_DIR, exist_ok=True)
        local_base = f"{settings.AUDIO_TEMP_DIR}/{recording_id}"
        local_path = await download_file(file_id, local_base)

        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.AUDIO_TTL_HOURS)
        await db.execute(
            """UPDATE recordings SET audio_local_path = $1, audio_expires_at = $2,
                status = 'transcribing', updated_at = now()
            WHERE id = $3""",
            [local_path, expires_at, recording_id],
        )
        pipeline_metrics.record(True)

        # 2. Transcrição
        transcript, t_model = await transcribe_audio(local_path)
        await db.execute(
            """UPDATE recordings SET transcript_text = $1, transcript_model = $2,
                status = 'transcribed', updated_at = now()
            WHERE id = $3""",
            [transcript, t_model, recording_id],
        )
        pipeline_metrics.record(True)

        # 3. Sumarização
        summary, s_model = await summarize_transcript(
            transcript, seller["name"], session["customer_name"], session["product"],
        )

        # 4. Resolver customer
        customer_id = await resolve_customer(str(seller["org_id"]), session["customer_name"])

        # 5. Finalizar
        await db.execute(
            """UPDATE recordings SET summary_text = $1, summary_model = $2,
                customer_id = $3, status = 'summarized',
                processed_at = now(), updated_at = now()
            WHERE id = $4""",
            [summary, s_model, customer_id, recording_id],
        )
        pipeline_metrics.record(True)

        # Notificar vendedor
        chat_id = await db.fetchval(
            "SELECT telegram_chat_id FROM users WHERE id = $1",
            [seller["id"]],
        )
        if chat_id:
            await send_message(
                chat_id,
                f"✅ Visita registrada!\nCliente: {session['customer_name']}\nProduto: {session['product']}",
                parse_mode=None,
            )

        # Limpar áudio local
        try:
            os.remove(local_path)
        except OSError:
            pass

    except Exception as e:
        logger.error(f"Pipeline error for recording {recording_id}: {e}", exc_info=True)
        pipeline_metrics.record(False)
        await db.execute(
            """UPDATE recordings SET status = 'error', error_message = $1, updated_at = now()
            WHERE id = $2""",
            [str(e)[:500], recording_id],
        )
        chat_id = await db.fetchval(
            "SELECT telegram_chat_id FROM users WHERE id = $1",
            [seller["id"]],
        )
        if chat_id:
            await send_message(chat_id, "❌ Erro ao processar seu áudio. Tente novamente.", parse_mode=None)
