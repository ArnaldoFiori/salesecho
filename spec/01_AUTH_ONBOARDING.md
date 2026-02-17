# 17 — AUTH & ONBOARDING (v6)

## Status
APROVADO

## Decisões Canônicas

| Decisão | Valor |
|---------|-------|
| Mecanismo auth | Supabase Auth nativo (email+senha) |
| Forgot password | Supabase Auth built-in (email) |
| Token | JWT emitido pelo Supabase Auth |
| Multi-tenancy | RLS por `org_id` no Supabase |
| Gateway pagamento | Stripe (recorrente mensal) |
| Unidade cobrança | Vendedor cadastrado (ativo ou não) |

---

## Roles

| Role | Acesso | Criação | Login portal |
|------|--------|---------|--------------|
| system_admin | Qualquer org (auditado) | Manual no Supabase | Sim |
| org_admin | Somente própria org | Auto-cadastro em salesecho.com.br | Sim |
| seller | Somente Telegram | Cadastrado pelo org_admin | Não |

---

## Fluxo 1 — Cadastro Empresa (org_admin)

### Passo a passo

1. Gestor acessa `www.salesecho.com.br`
2. Clica "Criar conta" → formulário:

| Campo | Tipo | Validação |
|-------|------|-----------|
| Nome completo | text | obrigatório, min 3 chars |
| Cargo | text | obrigatório |
| Email corporativo | email | obrigatório, domínios pessoais bloqueados* |
| Nome da empresa | text | obrigatório |
| Nº estimado de vendedores | number | obrigatório, min 1 |
| Senha | password | min 8 chars |
| Confirmar senha | password | deve coincidir |
| Checkbox: aceite de termos | boolean | obrigatório |

*Domínios bloqueados (herdado v3):
`gmail.com, googlemail.com, hotmail.com, outlook.com, live.com, msn.com, yahoo.com, yahoo.com.br, bol.com.br, uol.com.br, icloud.com, me.com, protonmail.com, proton.me, aol.com, zoho.com, gmx.com, gmx.de, terra.com.br, ig.com.br`

3. Frontend chama Supabase Auth `signUp(email, password)`
4. Backend (trigger ou edge function) cria:
   - Registro em `organizations` (name, estimated_sellers)
   - Registro em `users` (role=org_admin, org_id=nova org)
   - Registro em `subscriptions` (status=trial, trial_ends_at=now+30d)
5. Supabase Auth envia email de confirmação
6. Gestor confirma email → acesso liberado
7. Aviso **obrigatório** exibido no cadastro:

> "Durante o período de teste (30 dias), você pode cadastrar até 5 vendedores gratuitamente. Ao final do período, caso não assine um plano, sua conta e todos os dados serão permanentemente excluídos."

---

## Fluxo 2 — Login

1. Gestor acessa portal → tela de login
2. Email + senha → Supabase Auth `signInWithPassword`
3. JWT retornado contém `user_id`
4. Frontend armazena JWT (Supabase SDK gerencia refresh)
5. Toda request ao backend inclui JWT no header `Authorization: Bearer <token>`
6. Backend valida JWT → resolve `user_id` → busca `org_id` na tabela `users`
7. Toda query filtrada por `org_id` (RLS)

### Regras de acesso pós-login

| Estado da subscription | Comportamento |
|------------------------|---------------|
| trial (ativo) | Acesso total, máx 5 vendedores |
| trial (expirado) | Bloqueio total, mensagem "assine ou dados serão deletados" |
| active | Acesso total, sem limite de vendedores |
| past_due (≤30d) | Acesso read-only (vê dados, não cria visitas) |
| past_due (>30d) | Bloqueio total, dados preservados |
| canceled | Bloqueio total, dados preservados por 90d depois deletados |

---

## Fluxo 3 — Forgot Password

1. Gestor clica "Esqueci minha senha" na tela de login
2. Informa email
3. Frontend chama Supabase Auth `resetPasswordForEmail(email)`
4. Supabase envia link de reset por email
5. Gestor clica link → define nova senha
6. Redirecionado para login

---

## Fluxo 4 — Cadastro de Vendedores (pelo org_admin)

1. Org_admin logado acessa portal → seção "Vendedores"
2. Clica "Adicionar vendedor" → formulário:

| Campo | Tipo | Validação |
|-------|------|-----------|
| Nome completo | text | obrigatório, min 3 chars |
| Número celular | tel | obrigatório, formato brasileiro, único por org |

3. Backend cria registro em `users` (role=seller, org_id do admin)
4. Validação de limite:
   - Se subscription=trial → máx 5 vendedores
   - Se subscription=active → sem limite (cobra por vendedor cadastrado)
5. Seller **não** tem login no portal
6. Seller **não** é criado no Supabase Auth (sem email/senha)

### CRUD vendedores (org_admin)

| Ação | Endpoint | Regra |
|------|----------|-------|
| Listar | GET /api/sellers | Filtrado por org_id (RLS) |
| Criar | POST /api/sellers | Valida limite trial |
| Editar | PUT /api/sellers/{id} | Só nome e telefone |
| Desativar | PATCH /api/sellers/{id}/deactivate | Soft delete (is_active=false) |

Nota: vendedor desativado **continua contando** para cobrança do mês corrente. Para de contar no mês seguinte.

---

## Fluxo 5 — Vinculação Seller ↔ Telegram

1. Vendedor envia primeira mensagem ao bot do Telegram
2. Bot extrai `chat_id` do payload Telegram
3. Backend busca na tabela `users` por número de celular (normalizado)
4. Se encontrou match:
   - Grava `telegram_chat_id` no registro do seller
   - Bot responde: "Olá {nome}, você está vinculado à empresa {org}. Envie seus áudios no formato: Nome Cliente / Produto / #gravar + áudio"
5. Se **não** encontrou:
   - Bot responde: "Número não cadastrado. Peça ao seu gestor para cadastrá-lo no portal SalesEcho."
   - Mensagem ignorada (não persiste)

### Normalização de telefone (herdado v3)

```python
def normalize_phone(phone: str) -> str:
    phone = phone.replace('+', '').replace('-', '').replace(' ', '')
    phone = phone.replace('(', '').replace(')', '')
    if phone.startswith('55') and len(phone) >= 12:
        return phone
    return phone
```

---

## Fluxo 6 — System Admin

| Ação | Como |
|------|------|
| Criar system_admin | INSERT manual na tabela `users` + Supabase Auth |
| Acesso | Login normal no portal |
| Diferencial | Vê todas as orgs, com filtro por org_id |
| Auditoria | Toda ação logada em `support_audit` (user_id, org_id, action, timestamp) |
| Limite | Não pode editar dados de negócio (visitas, vendedores), só visualizar |

---

## Tabelas envolvidas (referência — DDL completo no spec 18)

```
organizations (id, name, estimated_sellers, created_at)
users (id, auth_user_id, org_id, name, role, phone, telegram_chat_id, is_active, created_at)
subscriptions (id, org_id, status, stripe_customer_id, stripe_subscription_id, trial_ends_at, current_period_end, created_at)
support_audit (id, user_id, org_id, action, metadata, created_at)
```

---

## Contratos API — Auth

### POST /auth/signup (via Supabase Auth SDK — frontend direto)

Request:
```json
{
  "email": "gestor@empresa.com.br",
  "password": "********",
  "options": {
    "data": {
      "full_name": "João Silva",
      "job_title": "Diretor Comercial",
      "company_name": "Empresa ABC",
      "estimated_sellers": 15
    }
  }
}
```

Response: Supabase Auth padrão (user object + JWT)

Trigger (database function): cria org + user + subscription automaticamente.

### POST /auth/signin (via Supabase Auth SDK — frontend direto)

Request:
```json
{
  "email": "gestor@empresa.com.br",
  "password": "********"
}
```

Response: Supabase Auth padrão (session + JWT)

### POST /auth/reset-password (via Supabase Auth SDK — frontend direto)

Request:
```json
{
  "email": "gestor@empresa.com.br"
}
```

Response: 200 OK (email enviado)

### GET /api/me

Headers: `Authorization: Bearer <jwt>`

Response:
```json
{
  "user_id": "uuid",
  "org_id": "uuid",
  "name": "João Silva",
  "role": "org_admin",
  "org_name": "Empresa ABC",
  "subscription": {
    "status": "trial",
    "trial_ends_at": "2026-04-01T00:00:00Z",
    "seller_count": 3,
    "seller_limit": 5
  }
}
```

---

## Referências v3 aproveitáveis

| Função v3 | Reuso |
|-----------|-------|
| `is_corporate_email()` | Copiar direto — lista de domínios bloqueados |
| `normalize_phone()` | Copiar direto |
| `validate_cnpj()` | Removido — v6 não exige CNPJ no MVP |
| `db_create_tenant()` | Lógica migrada para Supabase trigger |
| `db_add_seller()` | Migrar para FastAPI endpoint |
| Templates Tailwind (login, register) | Design como referência, reescrever em React |
