# 12 — CHANGELOG DE CORREÇÕES (v6)

## Status
APROVADO — registro das correções aplicadas nos specs originais

## Objetivo

Este documento registra todas as correções identificadas na análise cruzada dos specs 01-11 e as decisões tomadas. Todas as correções já foram aplicadas diretamente nos specs afetados (abordagem B: specs auto-contidos).

---

## Correções Aplicadas

### 🔴 CRÍTICAS

| # | Problema | Spec afetado | Correção aplicada |
|---|---------|-------------|-------------------|
| 1 | Sessão do bot em memória (`dict`) perde dados em restart/deploy | 03 | Substituído por tabela `pending_sessions` no Supabase (DDL no Spec 02). TTL 10 min, cleanup via cron 1h. |
| 2 | Render Starter hiberna após 15 min sem requests | 07 | Adicionado UptimeRobot (free) com health check a cada 5 min. Documentada dependência. |
| 3 | Supabase Free pausa após 7 dias sem atividade | 07 | Decisão: **usar Supabase Pro ($25/mês) desde o MVP**. Justificativa documentada. |
| 4 | DDL não incluía `pending_payment` no enum | 02 | Enum `subscription_status` atualizado com `pending_payment` entre `trial` e `active`. |

### 🟡 MÉDIAS

| # | Problema | Spec afetado | Correção aplicada |
|---|---------|-------------|-------------------|
| 5 | CORS não especificado | 07 | Adicionada config completa: `allow_origins=[FRONTEND_URL, localhost:5173]`, `allow_credentials=True`. |
| 6 | Rate limiting inexistente | 07 | Adicionado `slowapi` com limites por endpoint (120/min webhook, 10/min login, 60/min geral). |
| 7 | Webhook Telegram sem validação de autenticidade | 03 | Adicionada validação do header `X-Telegram-Bot-Api-Secret-Token`. Config via `setWebhook` com `secret_token`. |
| 8 | Blocklist de domínios de email indefinida | 01 | Lista completa definida: gmail, hotmail, outlook, yahoo, uol, bol, terra, etc. (20 domínios). Mensagem de rejeição especificada. |
| 9 | `normalize_phone()` sem implementação | 01 | Implementação completa: strip não-dígitos → remove zero líder → adiciona DDI 55. Resultado: `5511999998888`. |
| 10 | JWT lifetime não documentado | 01 | Documentado: access 1h, refresh 7d (defaults Supabase). Frontend usa `onAuthStateChange()` para refresh automático. |
| 11 | Comandos /start e /help não definidos | 03 | `/start` → fluxo de vinculação com botão `request_contact`. `/help` → instruções de uso formatadas. Mensagem default para texto não reconhecido. |
| 12 | Múltiplos org_admins indefinido | 01, 02 | **Decisão: 1 org_admin por org no MVP.** Sem constraint no DB, controlado pela aplicação. Documentado em ambos os specs. |

### 🟢 MENORES

| # | Problema | Spec afetado | Correção aplicada |
|---|---------|-------------|-------------------|
| 13 | Timezone misturado (UTC + BRT) nos cron jobs | 02 | Padronizado: **tudo UTC no banco e cron jobs**. Conversão para BRT apenas no frontend. Tabela de cron jobs em Spec 02 mostra horários UTC com equivalência BRT em comentário. |
| 14 | Áudio sem fala (transcrição vazia ou curta) | 03 | Adicionada validação: se transcrição < 10 palavras → status `error`, mensagem "Não foi possível identificar fala no áudio." |

---

## Decisões Aceitas (sem correção necessária no MVP)

| # | Item | Decisão |
|---|------|---------|
| 15 | Customer duplicado por typo | Aceito no MVP. Normalização é `LOWER(TRIM())`. Merge manual de customers no roadmap pós-MVP. |
| 16 | Sem paginação no GET /api/sellers | Aceito. Org com >100 sellers é cenário distante. |
| 17 | Sem campo `created_by` em users | Aceito. Apenas 1 org_admin por org, rastreabilidade implícita. |
| 18 | Export XLSX sem detalhamento | Aceito. Implementação direta com openpyxl, sem gap funcional. |

---

## Env Vars Adicionadas

| Variável | Spec | Motivo |
|----------|------|--------|
| `RESEND_API_KEY` | 07, 09 | Envio de emails transacionais |
| `ADMIN_TELEGRAM_CHAT_ID` | 07, 10 | Alertas operacionais para system_admin |
| `ALERT_ENABLED` | 07, 10 | Toggle de alertas (true/false) |

---

## Dependência Adicionada

| Package | Spec | Motivo |
|---------|------|--------|
| `slowapi==0.1.*` | 07 | Rate limiting |

---

## Specs Atualizados (v2)

| Spec | Versão | Alterações |
|------|--------|-----------|
| 01_AUTH_ONBOARDING | v2 | Blocklist de emails, normalize_phone(), JWT lifetime, 1 org_admin |
| 02_DDL | v2 | `pending_payment` no enum, tabela `pending_sessions`, cron cleanup sessões, timezone UTC |
| 03_PIPELINE_TELEGRAM | v2 | Sessão em DB, validação webhook secret, /start, /help, transcrição mínima, check subscription |
| 05_STRIPE_BILLING | v2 | Cartão + Boleto + PIX (já aplicado anteriormente) |
| 07_INFRA_DEPLOY | v2 | CORS, rate limiting, keep-alive UptimeRobot, Supabase Pro, env vars consolidadas |

---

## Specs Inalterados

| Spec | Motivo |
|------|--------|
| 04_PORTAL_GESTOR | Sem correções necessárias |
| 06_BUSINESS_CUSTOS | Sem correções necessárias (atualizar custo Supabase Pro se recalcular) |
| 08_LGPD_TERMOS | Sem correções necessárias |
| 09_EMAILS_TRANSACIONAIS | Sem correções necessárias |
| 10_MONITORAMENTO_ALERTAS | Sem correções necessárias |
| 11_LANDING_PAGE | Sem correções necessárias |
