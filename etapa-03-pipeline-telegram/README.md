# Etapa 03 — Backend: Pipeline Telegram

## Objetivo
Bot Telegram recebendo áudios, transcrevendo via Groq Whisper, sumarizando via Groq Llama, salvando no DB.

## Spec de referência
- `spec/03_PIPELINE_TELEGRAM.md` (v2)

## Entregável
- `POST /api/webhook/telegram` funcional com validação de secret
- Comandos `/start` e `/help`
- Vinculação seller via compartilhamento de contato
- Sessão em DB (pending_sessions): texto → áudio
- Pipeline: download → transcrição → sumarização → DB
- Dedup por (seller_id, telegram_message_id)
- Validação transcrição mínima (< 10 palavras → error)

## Validação
Enviar áudio pelo Telegram → verificar recording com status `summarized` no Supabase.

## Status
⏳ Pendente
