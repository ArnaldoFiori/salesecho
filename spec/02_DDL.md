# 02 — DDL COMPLETO (v6)

## Status
PENDENTE — aguardando aprovação

## Decisões Canônicas

| Decisão | Valor |
|---------|-------|
| Banco | Supabase (PostgreSQL 15+) |
| Multi-tenancy | RLS por `org_id` em todas as tabelas de negócio |
| Auth | Supabase Auth (`auth.users`) — tabela gerenciada, não criada por nós |
| UUIDs | `gen_random_uuid()` nativo do PostgreSQL |
| Timestamps | `timestamptz`, default `now()` |
| Soft delete | Não — hard delete (simplicidade MVP) |
| Enums | PostgreSQL ENUM types |

---

## Enums

```sql
CREATE TYPE user_role AS ENUM ('system_admin', 'org_admin', 'seller');

CREATE TYPE subscription_status AS ENUM ('trial', 'active', 'past_due', 'canceled', 'expired');

CREATE TYPE recording_status AS ENUM ('received', 'transcribing', 'transcribed', 'summarized', 'error');
```

---

## Tabelas

### 1. organizations

Raiz do multi-tenancy. Uma org = uma empresa cliente.

```sql
CREATE TABLE organizations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    estimated_sellers INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_organizations_created_at ON organizations (created_at);
```

---

### 2. users

Usuários do sistema. Vinculados a `auth.users` via `auth_user_id`. Sellers não têm login no portal.

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_user_id    UUID UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    email           TEXT,
    role            user_role NOT NULL DEFAULT 'seller',
    phone           TEXT,
    phone_normalized TEXT,
    telegram_chat_id BIGINT UNIQUE,
    job_title       TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- auth_user_id é NULL para sellers (não têm login)
-- phone_normalized: resultado de normalize_phone() para match com Telegram

CREATE INDEX idx_users_org_id ON users (org_id);
CREATE INDEX idx_users_auth_user_id ON users (auth_user_id);
CREATE INDEX idx_users_phone_normalized ON users (phone_normalized);
CREATE INDEX idx_users_telegram_chat_id ON users (telegram_chat_id);
CREATE INDEX idx_users_org_role ON users (org_id, role);
```

---

### 3. subscriptions

Uma subscription por org. Controla trial, pagamento e acesso.

```sql
CREATE TABLE subscriptions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                  UUID NOT NULL UNIQUE REFERENCES organizations(id) ON DELETE CASCADE,
    status                  subscription_status NOT NULL DEFAULT 'trial',
    stripe_customer_id      TEXT UNIQUE,
    stripe_subscription_id  TEXT UNIQUE,
    trial_ends_at           TIMESTAMPTZ,
    current_period_end      TIMESTAMPTZ,
    seller_limit            INTEGER NOT NULL DEFAULT 5,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- trial: seller_limit=5, trial_ends_at=now()+30d
-- active: seller_limit conforme plano Stripe
-- past_due: 30d tolerância read-only
-- expired: trial expirado sem pagamento → dados serão deletados
-- canceled: assinante cancelou → dados preservados

CREATE INDEX idx_subscriptions_status ON subscriptions (status);
CREATE INDEX idx_subscriptions_trial_ends ON subscriptions (trial_ends_at) WHERE status = 'trial';
```

---

### 4. customers

Clientes/prospects mencionados pelos vendedores nos áudios. Resolução por org_id + nome normalizado.

```sql
CREATE TABLE customers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    name_normalized TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- name_normalized: LOWER(TRIM(name)) para match case-insensitive
-- Resolução: busca por org_id + name_normalized; se não existe, cria

CREATE UNIQUE INDEX idx_customers_org_name ON customers (org_id, name_normalized);
```

---

### 5. recordings

Cada envio de áudio pelo vendedor via Telegram.

```sql
CREATE TABLE recordings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    seller_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    customer_id         UUID REFERENCES customers(id) ON DELETE SET NULL,
    telegram_message_id BIGINT NOT NULL,
    telegram_file_id    TEXT NOT NULL,
    customer_name_raw   TEXT NOT NULL,
    product_raw         TEXT NOT NULL,
    audio_duration_sec  INTEGER,
    audio_local_path    TEXT,
    audio_expires_at    TIMESTAMPTZ,
    status              recording_status NOT NULL DEFAULT 'received',
    transcript_text     TEXT,
    transcript_model    TEXT,
    summary_text        TEXT,
    summary_model       TEXT,
    error_message       TEXT,
    processed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- customer_name_raw: nome digitado pelo vendedor antes de resolver
-- product_raw: produto digitado pelo vendedor
-- audio_local_path: caminho temporário (fallback 24h)
-- audio_expires_at: now()+24h, cron limpa após expirar
-- transcript_text/summary_text: resultado do processamento inline
-- error_message: preenchido quando status='error'

CREATE INDEX idx_recordings_org_id ON recordings (org_id);
CREATE INDEX idx_recordings_seller_id ON recordings (seller_id);
CREATE INDEX idx_recordings_customer_id ON recordings (customer_id);
CREATE INDEX idx_recordings_status ON recordings (status) WHERE status IN ('received', 'transcribing', 'error');
CREATE INDEX idx_recordings_created_at ON recordings (org_id, created_at DESC);
CREATE INDEX idx_recordings_audio_cleanup ON recordings (audio_expires_at) WHERE audio_local_path IS NOT NULL;

-- Dedup: mesmo vendedor + mesmo telegram_message_id = duplicata
CREATE UNIQUE INDEX idx_recordings_dedup ON recordings (seller_id, telegram_message_id);
```

---

### 6. support_audit

Log de ações do system_admin ao acessar dados de outras orgs.

```sql
CREATE TABLE support_audit (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    action      TEXT NOT NULL,
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_support_audit_org ON support_audit (org_id, created_at DESC);
CREATE INDEX idx_support_audit_user ON support_audit (user_id, created_at DESC);
```

---

## RLS Policies

### Habilitar RLS em todas as tabelas

```sql
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE recordings ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_audit ENABLE ROW LEVEL SECURITY;
```

### Função auxiliar: org_id do usuário logado

```sql
CREATE OR REPLACE FUNCTION get_user_org_id()
RETURNS UUID AS $$
    SELECT org_id FROM users WHERE auth_user_id = auth.uid()
$$ LANGUAGE sql SECURITY DEFINER STABLE;

CREATE OR REPLACE FUNCTION get_user_role()
RETURNS user_role AS $$
    SELECT role FROM users WHERE auth_user_id = auth.uid()
$$ LANGUAGE sql SECURITY DEFINER STABLE;
```

### Policies — organizations

```sql
-- org_admin vê somente própria org
CREATE POLICY "org_admin_select_own_org"
    ON organizations FOR SELECT
    USING (id = get_user_org_id());

-- system_admin vê todas
CREATE POLICY "system_admin_select_all_orgs"
    ON organizations FOR SELECT
    USING (get_user_role() = 'system_admin');
```

### Policies — users

```sql
-- org_admin vê/gerencia sellers da própria org
CREATE POLICY "org_admin_select_org_users"
    ON users FOR SELECT
    USING (org_id = get_user_org_id());

CREATE POLICY "org_admin_insert_sellers"
    ON users FOR INSERT
    WITH CHECK (
        org_id = get_user_org_id()
        AND role = 'seller'
    );

CREATE POLICY "org_admin_update_sellers"
    ON users FOR UPDATE
    USING (
        org_id = get_user_org_id()
        AND role = 'seller'
    );

-- system_admin vê todos
CREATE POLICY "system_admin_select_all_users"
    ON users FOR SELECT
    USING (get_user_role() = 'system_admin');
```

### Policies — subscriptions

```sql
CREATE POLICY "org_admin_select_own_subscription"
    ON subscriptions FOR SELECT
    USING (org_id = get_user_org_id());

CREATE POLICY "system_admin_select_all_subscriptions"
    ON subscriptions FOR SELECT
    USING (get_user_role() = 'system_admin');
```

### Policies — customers

```sql
CREATE POLICY "org_select_own_customers"
    ON customers FOR SELECT
    USING (org_id = get_user_org_id());

CREATE POLICY "org_insert_own_customers"
    ON customers FOR INSERT
    WITH CHECK (org_id = get_user_org_id());

CREATE POLICY "system_admin_select_all_customers"
    ON customers FOR SELECT
    USING (get_user_role() = 'system_admin');
```

### Policies — recordings

```sql
CREATE POLICY "org_select_own_recordings"
    ON recordings FOR SELECT
    USING (org_id = get_user_org_id());

CREATE POLICY "system_admin_select_all_recordings"
    ON recordings FOR SELECT
    USING (get_user_role() = 'system_admin');
```

### Policies — support_audit

```sql
-- Somente system_admin vê audit logs
CREATE POLICY "system_admin_select_audit"
    ON support_audit FOR SELECT
    USING (get_user_role() = 'system_admin');

CREATE POLICY "system_admin_insert_audit"
    ON support_audit FOR INSERT
    WITH CHECK (get_user_role() = 'system_admin');
```

---

## Triggers

### updated_at automático

```sql
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_recordings_updated_at
    BEFORE UPDATE ON recordings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

### Trigger de onboarding (pós-signup)

```sql
CREATE OR REPLACE FUNCTION handle_new_user_signup()
RETURNS TRIGGER AS $$
DECLARE
    new_org_id UUID;
BEGIN
    -- Criar organization
    INSERT INTO organizations (name, estimated_sellers)
    VALUES (
        NEW.raw_user_meta_data->>'company_name',
        (NEW.raw_user_meta_data->>'estimated_sellers')::INTEGER
    )
    RETURNING id INTO new_org_id;

    -- Criar user (org_admin)
    INSERT INTO users (auth_user_id, org_id, name, email, role, job_title)
    VALUES (
        NEW.id,
        new_org_id,
        NEW.raw_user_meta_data->>'full_name',
        NEW.email,
        'org_admin',
        NEW.raw_user_meta_data->>'job_title'
    );

    -- Criar subscription (trial)
    INSERT INTO subscriptions (org_id, status, trial_ends_at, seller_limit)
    VALUES (
        new_org_id,
        'trial',
        now() + INTERVAL '30 days',
        5
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user_signup();
```

---

## Cron Jobs (via pg_cron ou backend)

| Job | Frequência | Ação |
|-----|-----------|------|
| Limpar áudios expirados | A cada 1h | `DELETE audio_local_path WHERE audio_expires_at < now()` |
| Expirar trials | Diário 00:00 UTC | `UPDATE subscriptions SET status='expired' WHERE status='trial' AND trial_ends_at < now()` |
| Deletar dados de trials expirados | Diário 01:00 UTC | `DELETE FROM organizations WHERE id IN (SELECT org_id FROM subscriptions WHERE status='expired' AND trial_ends_at < now() - INTERVAL '7 days')` — 7 dias de graça após expiração |
| Marcar inadimplência | Diário 00:00 UTC | `UPDATE subscriptions SET status='past_due' WHERE status='active' AND current_period_end < now()` |

---

## Diagrama de Relacionamentos

```
auth.users (Supabase gerenciado)
    │
    └──> users.auth_user_id (NULL para sellers)
            │
            ├──> users.org_id ──> organizations.id
            │                         │
            │                         ├──> subscriptions.org_id
            │                         ├──> customers.org_id
            │                         └──> recordings.org_id
            │
            ├──> recordings.seller_id
            └──> support_audit.user_id

recordings.customer_id ──> customers.id
```

---

## Notas de Implementação

1. **Backend (FastAPI) usa service_role key** para operações de escrita no pipeline Telegram (bypass RLS). O frontend usa anon key com RLS ativo.

2. **Normalização de customer**: `name_normalized = LOWER(TRIM(customer_name_raw))`. Match por `org_id + name_normalized`. Se não existe, INSERT automático.

3. **Dedup de recordings**: índice único em `(seller_id, telegram_message_id)`. Se duplicata, retorna 200 OK sem reprocessar.

4. **phone_normalized**: preenchido via trigger ou aplicação ao inserir/atualizar phone. Formato: somente dígitos com DDI (ex: `5511999998888`).

5. **Cascade deletes**: ao deletar `organizations`, cascateia para `users`, `subscriptions`, `customers`, `recordings`, `support_audit`.

6. **Trial expirado + 7 dias de graça**: dados são deletados 7 dias após expiração do trial (janela para o gestor assinar). Aviso no portal durante esses 7 dias.
