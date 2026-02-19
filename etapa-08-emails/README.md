# Etapa 08 — Emails Transacionais

## Objetivo
Configurar Resend + templates + cron jobs para emails do negócio.

## Spec de referência
- `spec/09_EMAILS_TRANSACIONAIS.md`

## Entregável
- Resend configurado (domínio verificado, SPF, DKIM, DMARC)
- `send_email()` funcional
- Templates: bem-vindo, trial expirando (7d/3d/1d), trial expirou, pagamento confirmado/falhou, boleto gerado, dados serão excluídos
- Cron jobs: trial expirando, trial expirou, dados excluídos
- Supabase Auth email templates customizados (confirmação, reset)

## Validação
Signup → receber email de boas-vindas. Simular trial expirando → receber alerta.

## Status
⏳ Pendente
