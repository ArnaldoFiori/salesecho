# 03 — PIPELINE TELEGRAM (v6)

## Status
APROVADO (v2: correções Spec 12)

## Decisões Canônicas

| Decisão | Valor |
|---------|-------|
| Canal de entrada | Telegram Bot API (webhook) |
| Formato de envio | Texto (cliente\nproduto\n#gravar) + áudio (voz ou arquivo) |
| Sessão de correlação | **Tabela `pending_sessions` no Supabase** (persiste em restart) |
| TTL da sessão | 10 minutos |
| Transcrição | Groq Whisper Large v3 Turbo |
| Sumarização | Groq Llama 3.3 70B Versatile |
| Áudio temp | `/tmp/salesecho/audio/{recording_id}.ext` — TTL 24h |
| Dedup | Unique index `(seller_id, telegram_message_id)` |
| Validação webhook | **Header `X-Telegram-Bot-Api-Secret-Token`** |

---

## Webhook Endpoint

```
POST /api/webhook/telegram
```

### Validação de Autenticidade

```python
@app.post("/api/webhook/telegram")
async def telegram_webhook(request: Request):
    # Validar secret token (configurado no setWebhook)
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(403, "Invalid webhook secret")

    payload = await request.json()
    # Responder 200 imediatamente (Telegram espera <60s)
    background_tasks.add_task(process_telegram_update, payload)
    return Response(status_code=200)
```

### Configuração do Webhook (uma vez)

```python
# Registrar webhook com secret token
import httpx

async def set_webhook():
    await httpx.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
        json={
            "url": f"{BACKEND_URL}/api/webhook/telegram",
            "secret_token": TELEGRAM_WEBHOOK_SECRET
        }
    )
```

---

## Comandos do Bot

| Comando | Resposta |
|---------|---------|
| `/start` | Fluxo de vinculação (pede compartilhamento de contato) |
| `/help` | Instruções de uso |
| Texto com `#gravar` | Inicia sessão de gravação |
| Áudio (voice/document) | Processa se sessão ativa |
| Qualquer outro | Mensagem de ajuda |

### /start

```python
async def handle_start(chat_id: int):
    keyboard = {
        "keyboard": [[{
            "text": "📱 Compartilhar meu contato",
            "request_contact": True
        }]],
        "one_time_keyboard": True,
        "resize_keyboard": True
    }
    await send_message(
        chat_id,
        "Olá! Para vincular sua conta, compartilhe seu contato "
        "usando o botão abaixo.",
        reply_markup=keyboard
    )
```

### /help

```python
async def handle_help(chat_id: int):
    await send_message(
        chat_id,
        "📋 *Como registrar uma visita:*\n\n"
        "1️⃣ Envie uma mensagem com:\n"
        "   Nome do Cliente\n"
        "   Produto\n"
        "   #gravar\n\n"
        "2️⃣ Em seguida, envie o áudio da visita\n\n"
        "⏱ Você tem 10 minutos entre o texto e o áudio.\n"
        "🎙 Áudio máximo: 10 minutos.",
        parse_mode="Markdown"
    )
```

---

## Fluxo Completo do Pipeline

```
Vendedor envia mensagem no Telegram
    │
    ├── /start → Fluxo de vinculação (pede contato)
    ├── /help → Instruções de uso
    ├── Contato compartilhado → Vinculação seller (normalize_phone → match)
    │
    ├── Texto com #gravar
    │   ├── Seller não vinculado? → "Número não cadastrado..."
    │   ├── Subscription inativa? → "Sua empresa não tem acesso ativo..."
    │   ├── Parse: linha1=cliente, linha2=produto
    │   ├── Validação: ambos obrigatórios
    │   └── UPSERT pending_sessions (chat_id, customer_name, product)
    │       └── Responde: "✅ Sessão aberta para {cliente} / {produto}. Envie o áudio."
    │
    ├── Áudio (voice ou document)
    │   ├── Seller não vinculado? → ignora
    │   ├── Busca pending_sessions WHERE chat_id = X AND created_at > now()-10min
    │   │   └── Não encontrou? → "Envie primeiro: NomeCliente\nProduto\n#gravar"
    │   ├── Dedup check: (seller_id, telegram_message_id) já existe? → 200 OK, ignora
    │   ├── INSERT recording (status='received')
    │   ├── DELETE pending_sessions WHERE chat_id = X
    │   ├── Responde: "🎙 Áudio recebido! Processando..."
    │   └── Background:
    │       ├── Download áudio do Telegram
    │       ├── Transcrição (Groq Whisper)
    │       │   └── Se transcrição < 10 palavras → status='error', msg="Não foi possível identificar fala"
    │       ├── Sumarização (Groq Llama)
    │       ├── Resolve customer (org_id + name_normalized)
    │       └── UPDATE recording (status='summarized')
    │
    └── Qualquer outro texto
        └── Responde: "Use /help para ver como registrar uma visita."
```

---

## Sessão — Tabela pending_sessions

Substitui `dict` em memória. Persiste entre restarts/deploys do container.

```python
async def upsert_session(chat_id: int, customer_name: str, product: str):
    """Cria ou atualiza sessão. UPSERT por chat_id (unique)."""
    await db.execute(
        """INSERT INTO pending_sessions (telegram_chat_id, customer_name, product)
        VALUES (:chat_id, :customer, :product)
        ON CONFLICT (telegram_chat_id)
        DO UPDATE SET customer_name = :customer, product = :product, created_at = now()""",
        {"chat_id": chat_id, "customer": customer_name, "product": product}
    )

async def get_session(chat_id: int) -> dict | None:
    """Busca sessão ativa (< 10 min)."""
    row = await db.fetchone(
        """SELECT customer_name, product FROM pending_sessions
        WHERE telegram_chat_id = :chat_id
        AND created_at > now() - INTERVAL '10 minutes'""",
        {"chat_id": chat_id}
    )
    return dict(row) if row else None

async def delete_session(chat_id: int):
    """Remove sessão após uso."""
    await db.execute(
        "DELETE FROM pending_sessions WHERE telegram_chat_id = :chat_id",
        {"chat_id": chat_id}
    )
```

---

## Vinculação Seller ↔ Telegram

1. Vendedor envia `/start` ou primeira mensagem
2. Bot pede para compartilhar contato (botão `request_contact`)
3. Telegram envia `message.contact.phone_number`
4. Backend normaliza: `normalize_phone(phone_number)`
5. Busca: `SELECT * FROM users WHERE phone_normalized = :phone AND role = 'seller'`

```python
async def handle_contact(chat_id: int, contact: dict):
    phone = contact.get("phone_number", "")
    normalized = normalize_phone(phone)

    seller = await db.fetchone(
        """SELECT u.id, u.name, u.org_id, o.name as org_name
        FROM users u JOIN organizations o ON u.org_id = o.id
        WHERE u.phone_normalized = :phone AND u.role = 'seller' AND u.is_active = true""",
        {"phone": normalized}
    )

    if not seller:
        await send_message(chat_id,
            "❌ Número não cadastrado. Peça ao seu gestor para "
            "cadastrá-lo no portal SalesEcho.")
        return

    # Vincular chat_id
    await db.execute(
        "UPDATE users SET telegram_chat_id = :chat_id WHERE id = :id",
        {"chat_id": chat_id, "id": seller["id"]}
    )

    # Mensagem de boas-vindas + aviso LGPD
    await send_message(chat_id,
        f"✅ Olá {seller['name']}! Você está vinculado à empresa "
        f"{seller['org_name']}.\n\n"
        "ℹ️ Seus áudios serão transcritos e resumidos por IA para "
        "relatórios da sua empresa. Os áudios originais são deletados "
        "em até 24 horas. Em caso de dúvidas, fale com seu gestor.\n\n"
        "Use /help para ver como registrar uma visita.")
```

---

## Download de Áudio

```python
async def download_audio(file_id: str, recording_id: str) -> str:
    """Baixa áudio do Telegram e salva localmente."""
    async with httpx.AsyncClient() as client:
        # Obter file_path
        resp = await client.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile",
            params={"file_id": file_id}
        )
        file_path = resp.json()["result"]["file_path"]
        ext = file_path.split(".")[-1] if "." in file_path else "ogg"

        # Download
        resp = await client.get(
            f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        )

        local_path = f"{AUDIO_TEMP_DIR}/{recording_id}.{ext}"
        with open(local_path, "wb") as f:
            f.write(resp.content)

        return local_path
```

---

## Transcrição — Groq Whisper

```python
async def transcribe_audio(local_path: str) -> tuple[str, str]:
    """Transcreve áudio via Groq Whisper. Retorna (texto, modelo)."""
    model = "whisper-large-v3-turbo"

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                with open(local_path, "rb") as f:
                    resp = await client.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                        files={"file": (os.path.basename(local_path), f)},
                        data={"model": model, "language": "pt"}
                    )

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 30))
                    logger.warning(f"Groq rate limit, retry in {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue

                resp.raise_for_status()
                text = resp.json()["text"]

                # Validar transcrição mínima
                word_count = len(text.strip().split())
                if word_count < 10:
                    raise ValueError(
                        f"Transcrição muito curta ({word_count} palavras). "
                        "Não foi possível identificar fala no áudio."
                    )

                return text, model

        except httpx.HTTPStatusError as e:
            if attempt == 2:
                raise
            await asyncio.sleep(2 ** attempt)

    raise RuntimeError("Transcrição falhou após 3 tentativas")
```

---

## Sumarização — Groq Llama

```python
SUMMARY_PROMPT = """Você é assistente de vendas. Analise a transcrição de uma visita comercial e gere um resumo estruturado.

Vendedor: {seller_name}
Cliente: {customer_name}
Produto: {product}
Transcrição: {transcript}

Gere o resumo com EXATAMENTE estas seções:
- **Contexto**: situação geral da visita (1-2 frases)
- **Necessidades**: o que o cliente precisa ou deseja
- **Produto**: o que foi apresentado/discutido sobre o produto
- **Objeções**: resistências ou preocupações do cliente
- **Próximos passos**: ações combinadas, follow-up

Se alguma seção não se aplica, escreva "Não identificado".
Seja conciso e objetivo. Máximo 300 palavras no total."""

async def summarize_transcript(
    transcript: str, seller_name: str, customer_name: str, product: str
) -> tuple[str, str]:
    """Sumariza transcrição via Groq Llama. Retorna (resumo, modelo)."""
    model = "llama-3.3-70b-versatile"

    prompt = SUMMARY_PROMPT.format(
        seller_name=seller_name,
        customer_name=customer_name,
        product=product,
        transcript=transcript
    )

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 1024
                    }
                )

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 30))
                    await asyncio.sleep(retry_after)
                    continue

                resp.raise_for_status()
                summary = resp.json()["choices"][0]["message"]["content"]
                return summary, model

        except httpx.HTTPStatusError as e:
            if attempt == 2:
                raise
            await asyncio.sleep(2 ** attempt)

    raise RuntimeError("Sumarização falhou após 3 tentativas")
```

---

## Resolução de Customer

```python
async def resolve_customer(org_id: str, customer_name_raw: str) -> str:
    """Resolve ou cria customer. Retorna customer_id."""
    name_normalized = customer_name_raw.strip().lower()

    row = await db.fetchone(
        """SELECT id FROM customers
        WHERE org_id = :org_id AND name_normalized = :name""",
        {"org_id": org_id, "name": name_normalized}
    )

    if row:
        return row["id"]

    row = await db.fetchone(
        """INSERT INTO customers (org_id, name, name_normalized)
        VALUES (:org_id, :name, :name_normalized)
        ON CONFLICT (org_id, name_normalized) DO UPDATE SET name = EXCLUDED.name
        RETURNING id""",
        {"org_id": org_id, "name": customer_name_raw.strip(), "name_normalized": name_normalized}
    )
    return row["id"]
```

---

## Pipeline Background Completo

```python
async def process_recording(recording_id: str, file_id: str,
                            seller: dict, session: dict):
    """Pipeline completo: download → transcrição → sumarização → DB."""
    try:
        # 1. Download
        local_path = await download_audio(file_id, recording_id)
        expires_at = datetime.utcnow() + timedelta(hours=AUDIO_TTL_HOURS)
        await db.execute(
            """UPDATE recordings SET
                audio_local_path = :path, audio_expires_at = :expires,
                status = 'transcribing', updated_at = now()
            WHERE id = :id""",
            {"path": local_path, "expires": expires_at, "id": recording_id}
        )
        pipeline_metrics.record(True)  # download ok

        # 2. Transcrição
        transcript, t_model = await transcribe_audio(local_path)
        await db.execute(
            """UPDATE recordings SET
                transcript_text = :text, transcript_model = :model,
                status = 'transcribed', updated_at = now()
            WHERE id = :id""",
            {"text": transcript, "model": t_model, "id": recording_id}
        )
        pipeline_metrics.record(True)

        # 3. Sumarização
        summary, s_model = await summarize_transcript(
            transcript, seller["name"],
            session["customer_name"], session["product"]
        )

        # 4. Resolver customer
        customer_id = await resolve_customer(
            seller["org_id"], session["customer_name"]
        )

        # 5. Finalizar
        await db.execute(
            """UPDATE recordings SET
                summary_text = :summary, summary_model = :s_model,
                customer_id = :customer_id, status = 'summarized',
                processed_at = now(), updated_at = now()
            WHERE id = :id""",
            {"summary": summary, "s_model": s_model,
             "customer_id": customer_id, "id": recording_id}
        )
        pipeline_metrics.record(True)

        # Notificar vendedor
        await send_message(seller["telegram_chat_id"],
            f"✅ Visita registrada!\n"
            f"Cliente: {session['customer_name']}\n"
            f"Produto: {session['product']}")

    except Exception as e:
        logger.error(f"Pipeline error for recording {recording_id}: {e}", exc_info=True)
        pipeline_metrics.record(False)
        await db.execute(
            """UPDATE recordings SET
                status = 'error', error_message = :error, updated_at = now()
            WHERE id = :id""",
            {"error": str(e)[:500], "id": recording_id}
        )
        await send_message(seller["telegram_chat_id"],
            "❌ Erro ao processar seu áudio. Tente novamente.")
```

---

## Verificação de Subscription Ativa

Antes de processar qualquer mensagem de vendedor, verificar se a org tem acesso:

```python
async def check_seller_access(seller_id: str) -> bool:
    """Verifica se seller tem org com subscription ativa."""
    row = await db.fetchone(
        """SELECT s.status FROM subscriptions s
        JOIN users u ON u.org_id = s.org_id
        WHERE u.id = :seller_id""",
        {"seller_id": seller_id}
    )
    if not row:
        return False
    return row["status"] in ("trial", "active", "pending_payment")
```
