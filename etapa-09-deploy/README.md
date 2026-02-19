# Etapa 09 — Deploy

## Objetivo
Colocar tudo em produção: Render, Vercel, DNS, webhooks, UptimeRobot.

## Spec de referência
- `spec/07_INFRA_DEPLOY.md` (v2)
- `spec/10_MONITORAMENTO_ALERTAS.md`

## Entregável
- Backend no Render (Starter) com todas as env vars
- Frontend no Vercel com custom domain
- DNS configurado no Registro.br (api, app, www)
- Webhook Telegram apontando para produção (com secret_token)
- Webhook Stripe apontando para produção
- UptimeRobot: 2 monitores (backend + frontend)
- Alertas Telegram para admin funcionando
- Health check deep verificando DB + Groq + Stripe

## Validação
```bash
curl https://api.salesecho.com.br/health/deep
# {"status":"ok","checks":{"database":"ok","groq":"ok","stripe":"ok"}}
```

## Status
⏳ Pendente
