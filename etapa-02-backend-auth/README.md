# Etapa 02 — Backend: Estrutura + Auth

## Objetivo
Criar projeto FastAPI com estrutura de pastas, config, CORS, rate limiting, JWT validation, health check.

## Spec de referência
- `spec/01_AUTH_ONBOARDING.md` (v2)
- `spec/07_INFRA_DEPLOY.md` (v2)

## Entregável
- `backend/` funcional com `uvicorn`
- `GET /health` respondendo 200
- JWT do Supabase validando
- `get_current_user()` retornando user_id, org_id, role
- CORS e rate limiting configurados

## Validação
```bash
curl http://localhost:8000/health
# {"status":"ok","timestamp":"..."}
```

## Status
⏳ Pendente
