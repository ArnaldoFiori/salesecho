# Etapa 06 — Frontend: Auth + Layout

## Objetivo
SPA React + Vite com autenticação Supabase, layout base, rotas protegidas.

## Spec de referência
- `spec/01_AUTH_ONBOARDING.md` (v2)
- `spec/04_PORTAL_GESTOR.md`
- `spec/08_LGPD_TERMOS.md`

## Entregável
- Projeto React + Vite + Tailwind inicializado
- Supabase Auth client configurado
- Telas: Login, Signup (com blocklist email + checkbox termos), Forgot Password, Reset Password
- Layout base com sidebar/nav
- PrivateRoute, AdminRoute, SubscriptionGuard
- Páginas estáticas: `/termos`, `/privacidade`
- Refresh token automático via `onAuthStateChange`

## Validação
Signup → confirmar email → login → ver dashboard vazio.

## Status
⏳ Pendente
