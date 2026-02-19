# Etapa 01 — DDL no Supabase

## Objetivo
Criar banco de dados completo: enums, tabelas, índices, RLS, triggers e função de onboarding.

## Spec de referência
- `spec/02_DDL.md` (v2)

## Entregável
- `001_initial_schema.sql` executado no Supabase SQL Editor
- 7 tabelas criadas, RLS ativo, trigger de onboarding funcional

## Validação
```sql
-- Verificar tabelas criadas
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' ORDER BY table_name;

-- Resultado esperado:
-- customers, organizations, pending_sessions, recordings, subscriptions, support_audit, users
```

## Status
⏳ Pendente
