# Etapa 10 — Smoke Test End-to-End

## Objetivo
Validar fluxo completo em produção.

## Checklist

| # | Teste | Resultado esperado |
|---|-------|-------------------|
| 1 | Signup com email corporativo | Org + user + subscription criados, email recebido |
| 2 | Signup com gmail.com | Rejeição: "Use um email corporativo" |
| 3 | Confirmar email + login | Acesso ao dashboard (vazio) |
| 4 | Cadastrar seller (com telefone) | Seller criado, aparece na lista |
| 5 | Tentar cadastrar 6º seller (trial) | Rejeição: limite de 5 |
| 6 | Seller envia /start no Telegram | Bot pede compartilhamento de contato |
| 7 | Seller compartilha contato | Vinculação OK, boas-vindas + aviso LGPD |
| 8 | Seller envia texto com #gravar | Sessão aberta, bot confirma |
| 9 | Seller envia áudio | Áudio processado, status summarized |
| 10 | Gestor vê recording no portal | Transcrição + resumo visíveis |
| 11 | Export XLSX | Download funcional com dados corretos |
| 12 | Stripe Checkout (cartão teste) | Subscription active |
| 13 | Stripe Customer Portal | Abre, mostra fatura |
| 14 | Health check deep | Todos os checks "ok" |
| 15 | UptimeRobot | Monitores verdes |

## Status
⏳ Pendente
