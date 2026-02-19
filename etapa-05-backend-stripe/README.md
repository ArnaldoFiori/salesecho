# Etapa 05 — Backend: Stripe Billing

## Objetivo
Integração Stripe completa: checkout, webhooks, sync quantity, portal.

## Spec de referência
- `spec/05_STRIPE_BILLING.md` (v2)

## Entregável
- `POST /api/billing/checkout` — criar Checkout Session (cartão + boleto + PIX)
- `POST /api/billing/portal` — criar Customer Portal session
- `POST /api/webhook/stripe` — processar 6 eventos
- `sync_seller_quantity()` — atualizar quantity ao add/remove seller
- Status `pending_payment` funcional para boleto

## Validação
Stripe test mode: criar checkout → pagar com cartão teste → verificar subscription `active` no DB.

## Status
⏳ Pendente
