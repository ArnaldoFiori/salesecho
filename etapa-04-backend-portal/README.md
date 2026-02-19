# Etapa 04 — Backend: Rotas do Portal

## Objetivo
API completa para o frontend consumir: recordings, sellers, stats, account, admin.

## Spec de referência
- `spec/04_PORTAL_GESTOR.md`

## Entregável
- `GET /api/stats` — dashboard stats
- `GET /api/recordings` — listagem com filtros e paginação
- `GET /api/recordings/:id` — detalhe
- `GET /api/recordings/export` — XLSX
- `GET /api/sellers` — listagem
- `POST /api/sellers` — criar seller (com limite)
- `PUT /api/sellers/:id` — editar
- `DELETE /api/sellers/:id/telegram` — desvincular
- `GET /api/account` — dados conta
- `PUT /api/account` — atualizar
- `GET /api/admin/orgs` — system_admin only
- `GET /api/admin/metrics` — system_admin only

## Validação
Todos os endpoints respondendo com dados corretos filtrados por org_id (RLS).

## Status
⏳ Pendente
