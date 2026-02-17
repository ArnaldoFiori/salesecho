# 03 — PIPELINE TELEGRAM → TRANSCRIÇÃO → RELATÓRIO (v6)

## Status
PENDENTE — aguardando aprovação

## Decisões Canônicas

| Decisão | Valor |
|---------|-------|
| Canal de entrada | Telegram Bot API (webhook) |
| Código de validação | `#gravar` fixo, igual para todos |
| Transcrição | Groq Whisper (whisper-large-v3-turbo) |
| Sumarização | Groq Llama (llama-3.3-70b-versatile) |
| Storage áudio | Temporário 24h no filesystem do backend |
| Confirmação ao vendedor | Nativa do Telegram (mensagem de resposta do bot) |
| Processamento | Síncrono fire-and-forget (webhook retorna 200 imediato, processa em background) |
| Dedup | Índice único `(seller_id, telegram_message_id)` |

---

## Visão Geral do Fluxo

```
Vendedor (Telegram)
    │
    ├── 1. Envia mensagem texto: "Nome Cliente\nProduto\n#gravar"
    ├── 2. Envia áudio (voice note ou audio file)
    │
    ▼
Bot Telegram (webhook POST /api/webhook/telegram)
    │
    ├── 3. Valida vendedor (telegram_chat_id → users)
    ├── 4. Valida org ativa (subscription.status)
    ├── 5. Parseia mensagem texto (extrai cliente + produto + #gravar)
    ├── 6. Recebe áudio → download → salva temporário
    ├── 7. Dedup check
    │
    ▼
Pipeline de Processamento (background task)
    │
    ├── 8. Transcrição (Groq Whisper)
    ├── 9. Sumarização (Groq Llama)
    ├── 10. Resolve/cria customer
    ├── 11. Salva recording completo
    ├── 12. Responde vendedor no Telegram
    │
    ▼
Portal do Gestor (leitura via RLS)
```

---

## Fluxo Detalhado

### Passo 1 — Vendedor envia mensagem de texto

O vendedor envia uma mensagem de texto no Telegram com o formato:

```
Nome do Cliente
Produto
#gravar
```

**Regras de parsing:**

| Regra | Detalhe |
|-------|---------|
| Separador | Quebra de linha (`\n`) |
| Linha 1 | Nome do cliente (obrigatório, min 2 chars) |
| Linha 2 | Produto (obrigatório, min 2 chars) |
| Linha 3 | Deve conter `#gravar` (case-insensitive) |
| Espaços | `TRIM()` em cada linha |
| Linhas extras | Ignoradas |

**Mensagem inválida:** bot responde com formato esperado e não processa.

```python
def parse_visit_message(text: str) -> dict | None:
    """Retorna {customer_name, product} ou None se inválido."""
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
    if len(lines) < 3:
        return None
    if '#gravar' not in lines[2].lower():
        return None
    customer_name = lines[0]
    product = lines[1]
    if len(customer_name) < 2 or len(product) < 2:
        return None
    return {"customer_name": customer_name, "product": product}
```

### Passo 2 — Vendedor envia áudio

Após a mensagem de texto, o vendedor envia um áudio (voice note ou arquivo de áudio).

**Formatos aceitos:** `.ogg` (voice note padrão Telegram), `.mp3`, `.m4a`, `.wav`, `.opus`

**Limites:**

| Limite | Valor |
|--------|-------|
| Duração máxima | 10 minutos (600 segundos) |
| Tamanho máximo | 20MB (limite Telegram Bot API) |
| Duração mínima | 3 segundos |

### Passo 3 — Validação do vendedor

```python
async def identify_seller(telegram_chat_id: int) -> dict | None:
    """Busca seller por telegram_chat_id. Retorna user + org ou None."""
    result = await db.execute(
        """
        SELECT u.id, u.name, u.org_id, u.is_active,
               o.name as org_name,
               s.status as sub_status, s.seller_limit
        FROM users u
        JOIN organizations o ON o.id = u.org_id
        JOIN subscriptions s ON s.org_id = u.org_id
        WHERE u.telegram_chat_id = :chat_id
          AND u.role = 'seller'
        """,
        {"chat_id": telegram_chat_id}
    )
    return result
```

**Cenários de rejeição:**

| Cenário | Resposta ao vendedor |
|---------|---------------------|
| `telegram_chat_id` não encontrado | "Número não cadastrado. Peça ao seu gestor para cadastrá-lo no portal SalesEcho." |
| `is_active = false` | "Sua conta está desativada. Entre em contato com seu gestor." |
| `sub_status = 'expired'` | "A conta da sua empresa expirou. Entre em contato com seu gestor." |
| `sub_status = 'past_due'` (>30d) | "A conta da sua empresa está suspensa. Entre em contato com seu gestor." |
| `sub_status = 'canceled'` | "A conta da sua empresa foi cancelada. Entre em contato com seu gestor." |

### Passo 4 — Verificação de acesso da org

```python
def is_org_active(sub_status: str) -> bool:
    """Verifica se a org pode receber novos áudios."""
    return sub_status in ('trial', 'active', 'past_due')
    # past_due: ainda aceita áudios nos primeiros 30 dias
```

### Passo 5 — Estado de sessão do vendedor

O bot precisa correlacionar a mensagem de texto com o áudio subsequente. Estratégia: **cache em memória com TTL**.

```python
# Redis ou dict em memória (MVP)
# Chave: telegram_chat_id
# Valor: {customer_name, product, timestamp}
# TTL: 10 minutos

pending_sessions: dict[int, dict] = {}

async def handle_text_message(chat_id: int, text: str):
    parsed = parse_visit_message(text)
    if parsed is None:
        await send_telegram_message(chat_id, INVALID_FORMAT_MSG)
        return
    pending_sessions[chat_id] = {
        **parsed,
        "timestamp": time.time()
    }
    await send_telegram_message(
        chat_id,
        f"✓ Cliente: {parsed['customer_name']}\n"
        f"✓ Produto: {parsed['product']}\n\n"
        f"Agora envie o áudio da visita."
    )

async def handle_audio_message(chat_id: int, message: dict):
    session = pending_sessions.pop(chat_id, None)
    if session is None or (time.time() - session["timestamp"]) > 600:
        await send_telegram_message(
            chat_id,
            "Envie primeiro a mensagem de texto com:\n"
            "Nome do Cliente\nProduto\n#gravar\n\n"
            "Depois envie o áudio."
        )
        return
    # Processa áudio com session (customer_name + product)
    await process_recording(chat_id, session, message)
```

### Passo 6 — Download e armazenamento temporário do áudio

```python
async def download_telegram_audio(file_id: str, recording_id: str) -> str:
    """Baixa áudio do Telegram e salva localmente. Retorna path."""
    # 1. Obter file_path via Telegram API
    file_info = await telegram_api.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

    # 2. Download
    audio_bytes = await http_client.get(file_url)

    # 3. Salvar temporário
    ext = Path(file_info.file_path).suffix or ".ogg"
    local_path = f"/tmp/salesecho/audio/{recording_id}{ext}"
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    Path(local_path).write_bytes(audio_bytes)

    return local_path
```

**Limpeza:** cron job a cada 1h deleta arquivos com `audio_expires_at < now()`.

### Passo 7 — Dedup check

```python
async def check_dedup(seller_id: str, telegram_message_id: int) -> bool:
    """Retorna True se é duplicata."""
    try:
        await db.execute(
            "INSERT INTO recordings (seller_id, telegram_message_id, ...) VALUES (...)"
        )
        return False  # Novo registro
    except UniqueViolationError:
        return True  # Duplicata — ignorar
```

Se duplicata: webhook retorna 200 OK sem processar.

### Passo 8 — Transcrição (Groq Whisper)

```python
async def transcribe_audio(local_path: str) -> dict:
    """Transcreve áudio via Groq Whisper API."""
    # Status: received → transcribing
    async with aiohttp.ClientSession() as session:
        with open(local_path, "rb") as f:
            form = aiohttp.FormData()
            form.add_field("file", f, filename=Path(local_path).name)
            form.add_field("model", "whisper-large-v3-turbo")
            form.add_field("language", "pt")
            form.add_field("response_format", "verbose_json")

            resp = await session.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                data=form,
                timeout=aiohttp.ClientTimeout(total=120)
            )
            result = await resp.json()

    # Status: transcribing → transcribed
    return {
        "text": result["text"],
        "duration": result.get("duration"),
        "model": "whisper-large-v3-turbo"
    }
```

**Tratamento de erro:**

| Erro | Ação |
|------|------|
| Timeout (>120s) | Status → `error`, `error_message = "transcription_timeout"` |
| HTTP 429 (rate limit) | Retry com backoff exponencial (1s, 2s, 4s), máx 3 tentativas |
| HTTP 5xx | Retry com backoff, máx 3 tentativas |
| HTTP 4xx (exceto 429) | Status → `error`, `error_message = "transcription_failed: {status}"` |
| Texto vazio após transcrição | Status → `error`, `error_message = "empty_transcription"` |

### Passo 9 — Sumarização (Groq Llama)

```python
SUMMARY_PROMPT = """Você é um assistente de vendas. Analise a transcrição de um áudio de visita comercial e gere um resumo estruturado.

Dados da visita:
- Cliente: {customer_name}
- Produto: {product}

Transcrição do áudio:
{transcript}

Gere um resumo com as seguintes seções (omita seções sem informação):
1. **Contexto**: situação geral da visita
2. **Necessidades do cliente**: o que o cliente precisa/busca
3. **Produto apresentado**: o que foi oferecido e como
4. **Objeções**: resistências ou dúvidas do cliente
5. **Próximos passos**: ações combinadas ou pendências
6. **Observações**: qualquer outro ponto relevante

Seja conciso e objetivo. Máximo 200 palavras."""

async def summarize_transcript(
    transcript: str,
    customer_name: str,
    product: str
) -> dict:
    """Gera resumo via Groq Llama."""
    # Status: transcribed → summarizing (implícito, não tem enum próprio)
    prompt = SUMMARY_PROMPT.format(
        customer_name=customer_name,
        product=product,
        transcript=transcript
    )

    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": "Você é um assistente de vendas que gera resumos concisos de visitas comerciais."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.3
            },
            timeout=aiohttp.ClientTimeout(total=60)
        )
        result = await resp.json()

    # Status: → summarized
    return {
        "text": result["choices"][0]["message"]["content"],
        "model": "llama-3.3-70b-versatile"
    }
```

**Tratamento de erro:** mesma estratégia da transcrição (retry + backoff). Se falhar após 3 tentativas, status → `error`, `error_message = "summarization_failed"`.

### Passo 10 — Resolver/criar customer

```python
async def resolve_customer(org_id: str, customer_name_raw: str) -> str:
    """Retorna customer_id. Cria se não existe."""
    name_normalized = customer_name_raw.strip().lower()

    # Tenta buscar
    result = await db.fetchone(
        "SELECT id FROM customers WHERE org_id = :org_id AND name_normalized = :name",
        {"org_id": org_id, "name": name_normalized}
    )
    if result:
        return result["id"]

    # Cria novo
    result = await db.fetchone(
        """INSERT INTO customers (org_id, name, name_normalized)
           VALUES (:org_id, :name, :name_normalized)
           ON CONFLICT (org_id, name_normalized) DO UPDATE SET name = EXCLUDED.name
           RETURNING id""",
        {"org_id": org_id, "name": customer_name_raw.strip(), "name_normalized": name_normalized}
    )
    return result["id"]
```

### Passo 11 — Salvar recording completo

```python
async def save_recording(recording_id: str, data: dict):
    """Atualiza recording com resultado do processamento."""
    await db.execute(
        """UPDATE recordings SET
            customer_id = :customer_id,
            transcript_text = :transcript_text,
            transcript_model = :transcript_model,
            summary_text = :summary_text,
            summary_model = :summary_model,
            audio_duration_sec = :audio_duration_sec,
            status = :status,
            processed_at = now(),
            updated_at = now()
        WHERE id = :id""",
        {
            "id": recording_id,
            "customer_id": data["customer_id"],
            "transcript_text": data["transcript_text"],
            "transcript_model": data["transcript_model"],
            "summary_text": data["summary_text"],
            "summary_model": data["summary_model"],
            "audio_duration_sec": data["audio_duration_sec"],
            "status": "summarized"
        }
    )
```

### Passo 12 — Resposta ao vendedor

```python
SUCCESS_MSG = """✅ Visita registrada com sucesso!

📋 Cliente: {customer_name}
📦 Produto: {product}
⏱ Duração: {duration}

Resumo:
{summary}"""

ERROR_MSG = """❌ Erro ao processar seu áudio. Tente enviar novamente.

Se o problema persistir, entre em contato com seu gestor."""

async def notify_seller(chat_id: int, result: dict):
    if result["status"] == "summarized":
        msg = SUCCESS_MSG.format(
            customer_name=result["customer_name"],
            product=result["product"],
            duration=format_duration(result["audio_duration_sec"]),
            summary=result["summary_text"]
        )
    else:
        msg = ERROR_MSG
    await send_telegram_message(chat_id, msg)
```

---

## Webhook — Contrato API

### POST /api/webhook/telegram

Recebe updates do Telegram Bot API.

**Request:** payload padrão Telegram Update (enviado pelo Telegram).

**Response:** sempre `200 OK` com body vazio (o Telegram exige resposta rápida).

**Processamento interno (background):**

```python
@app.post("/api/webhook/telegram")
async def telegram_webhook(request: Request):
    """Webhook endpoint. Retorna 200 imediato, processa em background."""
    payload = await request.json()
    background_tasks.add_task(process_telegram_update, payload)
    return Response(status_code=200)

async def process_telegram_update(payload: dict):
    message = payload.get("message", {})
    chat_id = message.get("chat", {}).get("id")

    if not chat_id:
        return

    # Identificar vendedor
    seller = await identify_seller(chat_id)

    # Mensagem de texto
    if "text" in message:
        if seller is None:
            # Tentativa de vinculação (primeiro contato)
            await handle_first_contact(chat_id, message)
            return
        await handle_text_message(chat_id, message["text"])
        return

    # Áudio (voice note ou audio file)
    audio = message.get("voice") or message.get("audio")
    if audio and seller:
        await handle_audio_message(chat_id, message)
        return
```

---

## Fluxo de Vinculação (primeiro contato)

Conforme Spec 01, quando o vendedor envia a primeira mensagem:

```python
async def handle_first_contact(chat_id: int, message: dict):
    """Tenta vincular telegram_chat_id ao seller via número de celular."""
    # Telegram envia contact info se o user compartilhou
    contact = message.get("contact")
    if contact:
        phone = normalize_phone(contact.get("phone_number", ""))
    else:
        # Sem contact: tentar extrair do payload (user phone não está sempre disponível)
        phone = None

    if not phone:
        await send_telegram_message(
            chat_id,
            "Bem-vindo ao SalesEcho! Para vincular sua conta, "
            "envie seu contato usando o botão abaixo.",
            reply_markup={"keyboard": [[{"text": "Compartilhar contato", "request_contact": True}]], "one_time_keyboard": True}
        )
        return

    # Buscar seller pelo telefone normalizado
    seller = await db.fetchone(
        "SELECT id, name, org_id FROM users WHERE phone_normalized = :phone AND role = 'seller' AND is_active = true",
        {"phone": phone}
    )

    if seller:
        await db.execute(
            "UPDATE users SET telegram_chat_id = :chat_id WHERE id = :id",
            {"chat_id": chat_id, "id": seller["id"]}
        )
        org = await db.fetchone("SELECT name FROM organizations WHERE id = :id", {"id": seller["org_id"]})
        await send_telegram_message(
            chat_id,
            f"✅ Olá {seller['name']}! Você está vinculado à empresa {org['name']}.\n\n"
            f"Para registrar uma visita, envie:\n"
            f"Nome do Cliente\nProduto\n#gravar\n\n"
            f"Depois envie o áudio."
        )
    else:
        await send_telegram_message(
            chat_id,
            "Número não cadastrado. Peça ao seu gestor para cadastrá-lo no portal SalesEcho."
        )
```

---

## Mensagens do Bot (catálogo completo)

| Código | Mensagem |
|--------|----------|
| `WELCOME_LINKED` | "✅ Olá {nome}! Você está vinculado à empresa {org}. Para registrar uma visita, envie: Nome do Cliente\nProduto\n#gravar\n\nDepois envie o áudio." |
| `NOT_REGISTERED` | "Número não cadastrado. Peça ao seu gestor para cadastrá-lo no portal SalesEcho." |
| `SHARE_CONTACT` | "Bem-vindo ao SalesEcho! Para vincular sua conta, envie seu contato usando o botão abaixo." |
| `ACCOUNT_INACTIVE` | "Sua conta está desativada. Entre em contato com seu gestor." |
| `ORG_EXPIRED` | "A conta da sua empresa expirou. Entre em contato com seu gestor." |
| `ORG_SUSPENDED` | "A conta da sua empresa está suspensa. Entre em contato com seu gestor." |
| `INVALID_FORMAT` | "Formato inválido. Envie:\n\nNome do Cliente\nProduto\n#gravar\n\nDepois envie o áudio." |
| `TEXT_RECEIVED` | "✓ Cliente: {customer_name}\n✓ Produto: {product}\n\nAgora envie o áudio da visita." |
| `AUDIO_NO_SESSION` | "Envie primeiro a mensagem de texto com:\nNome do Cliente\nProduto\n#gravar\n\nDepois envie o áudio." |
| `AUDIO_TOO_SHORT` | "Áudio muito curto (mínimo 3 segundos). Envie novamente." |
| `AUDIO_TOO_LONG` | "Áudio muito longo (máximo 10 minutos). Envie um áudio mais curto." |
| `PROCESSING` | "⏳ Processando seu áudio..." |
| `SUCCESS` | "✅ Visita registrada! (ver Passo 12)" |
| `ERROR` | "❌ Erro ao processar seu áudio. Tente enviar novamente." |

---

## Tratamento de Erros — Resumo

| Etapa | Erro | Retry | Fallback |
|-------|------|-------|----------|
| Download áudio | Timeout/HTTP error | 2 tentativas | Status `error`, notifica vendedor |
| Transcrição | Timeout (>120s) | 3 tentativas, backoff | Status `error`, notifica vendedor |
| Transcrição | Rate limit (429) | 3 tentativas, backoff | Status `error`, notifica vendedor |
| Transcrição | Texto vazio | Sem retry | Status `error`, notifica vendedor |
| Sumarização | Timeout/erro | 3 tentativas, backoff | Status `error`, notifica vendedor |
| Salvar DB | Erro SQL | Sem retry | Log + status `error` |
| Notificar vendedor | Telegram API error | 2 tentativas | Log (não crítico) |

---

## Referências v3 Aproveitáveis

| Função v3 | Reuso em v6 |
|-----------|-------------|
| `parse_visit_message()` | Adaptar — v3 parseava formato similar |
| `transcribe_audio()` | Adaptar — mudar de OpenAI para Groq endpoint |
| `generate_summary()` | Adaptar — mudar modelo e prompt |
| `normalize_phone()` | Copiar direto |
| Rate limit/retry logic | Copiar padrão de backoff |

---

## Configurações (env vars)

| Variável | Descrição |
|----------|-----------|
| `TELEGRAM_BOT_TOKEN` | Token do bot Telegram |
| `TELEGRAM_WEBHOOK_SECRET` | Secret para validar requests do Telegram |
| `GROQ_API_KEY` | API key do Groq |
| `AUDIO_TEMP_DIR` | Diretório temporário para áudios (default: `/tmp/salesecho/audio`) |
| `AUDIO_TTL_HOURS` | TTL dos áudios temporários (default: 24) |
| `AUDIO_MAX_DURATION_SEC` | Duração máxima do áudio (default: 600) |
| `AUDIO_MIN_DURATION_SEC` | Duração mínima do áudio (default: 3) |
