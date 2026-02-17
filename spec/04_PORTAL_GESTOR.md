# 04 — PORTAL DO GESTOR (v6)

## Status
PENDENTE — aguardando aprovação

## Decisões Canônicas

| Decisão | Valor |
|---------|-------|
| Framework frontend | React (Vite SPA) |
| Estilo | Tailwind CSS |
| Auth frontend | Supabase Auth JS SDK |
| Hosting | Vercel ou Cloudflare Pages (free) |
| Domínio | app.salesecho.com.br (portal) / www.salesecho.com.br (landing) |
| Acesso | org_admin via browser, seller NÃO acessa portal |
| Responsividade | Desktop-first, responsivo para tablet (vendedor não usa) |

---

## Mapa de Telas

```
www.salesecho.com.br (landing page — marketing, não neste spec)

app.salesecho.com.br
├── /login ..................... Tela de login
├── /signup .................... Cadastro empresa
├── /forgot-password ........... Recuperação de senha
├── /reset-password ............ Redefinir senha (link do email)
│
├── /dashboard ................. Dashboard principal (home)
├── /recordings ................ Lista de registros/visitas
├── /recordings/:id ............ Detalhe de um registro
├── /sellers ................... Lista de vendedores
├── /sellers/new ............... Cadastro de vendedor
├── /sellers/:id ............... Editar vendedor
├── /account ................... Conta e assinatura
│
└── /admin (system_admin only)
    ├── /admin/orgs ............ Lista de organizações
    └── /admin/orgs/:id ........ Detalhe de org
```

---

## Tela 1 — Login (`/login`)

### Layout

| Elemento | Detalhe |
|----------|---------|
| Logo | SalesEcho centralizado |
| Campo email | Input text, placeholder "Email corporativo" |
| Campo senha | Input password, placeholder "Senha" |
| Botão | "Entrar" (primary) |
| Link | "Esqueci minha senha" → `/forgot-password` |
| Link | "Criar conta" → `/signup` |

### Comportamento

1. Submit → `supabase.auth.signInWithPassword({ email, password })`
2. Sucesso → redirect `/dashboard`
3. Erro → mensagem inline: "Email ou senha incorretos"
4. Se já logado → redirect automático `/dashboard`

---

## Tela 2 — Cadastro (`/signup`)

### Layout

Conforme Spec 01 — Fluxo 1 (Cadastro Empresa).

| Campo | Tipo | Validação |
|-------|------|-----------|
| Nome completo | text | obrigatório, min 3 chars |
| Cargo | text | obrigatório |
| Email corporativo | email | obrigatório, domínios pessoais bloqueados |
| Nome da empresa | text | obrigatório |
| Nº estimado de vendedores | number | obrigatório, min 1 |
| Senha | password | min 8 chars |
| Confirmar senha | password | deve coincidir |
| Checkbox termos | boolean | obrigatório |

**Aviso obrigatório** (exibido acima do botão):
> "Durante o período de teste (30 dias), você pode cadastrar até 5 vendedores gratuitamente. Ao final do período, caso não assine um plano, sua conta e todos os dados serão permanentemente excluídos."

### Comportamento

1. Validação de domínio de email no frontend (lista blocklist)
2. Submit → `supabase.auth.signUp({ email, password, options: { data: {...} } })`
3. Sucesso → tela "Verifique seu email para confirmar a conta"
4. Erro email duplicado → "Email já cadastrado"

---

## Tela 3 — Forgot Password (`/forgot-password`)

| Elemento | Detalhe |
|----------|---------|
| Campo email | Input text |
| Botão | "Enviar link de recuperação" |
| Link | "Voltar ao login" |

### Comportamento

1. Submit → `supabase.auth.resetPasswordForEmail(email)`
2. Sempre exibe: "Se este email estiver cadastrado, você receberá um link" (não revela se existe)

---

## Tela 4 — Dashboard (`/dashboard`)

Tela principal após login. Visão geral da org.

### Cards Resumo (topo)

| Card | Valor | Fonte |
|------|-------|-------|
| Vendedores ativos | COUNT de sellers is_active=true | `GET /api/stats` |
| Visitas hoje | COUNT de recordings criadas hoje | `GET /api/stats` |
| Visitas esta semana | COUNT de recordings últimos 7 dias | `GET /api/stats` |
| Visitas este mês | COUNT de recordings últimos 30 dias | `GET /api/stats` |

### Últimos Registros (abaixo dos cards)

Tabela com os 10 registros mais recentes:

| Coluna | Fonte |
|--------|-------|
| Data/hora | `recordings.created_at` |
| Vendedor | `users.name` |
| Cliente | `customers.name` |
| Produto | `recordings.product_raw` |
| Status | Badge colorido (`summarized`=verde, `error`=vermelho, `transcribing`=amarelo) |

Clique na linha → navega para `/recordings/:id`

### Alerta de Trial/Inadimplência

| Condição | Banner |
|----------|--------|
| Trial, faltam ≤7 dias | "Seu período de teste expira em X dias. Assine para manter seus dados." + botão "Assinar" |
| Trial expirado (7d graça) | "Seu período de teste expirou. Assine em até X dias ou seus dados serão excluídos." |
| past_due | "Pagamento pendente. Regularize para manter o acesso." |

---

## Tela 5 — Lista de Registros (`/recordings`)

### Filtros (topo)

| Filtro | Tipo | Opções |
|--------|------|--------|
| Vendedor | Select | Todos / lista de sellers da org |
| Cliente | Select | Todos / lista de customers da org |
| Período | Date range | Data início / Data fim |
| Status | Select | Todos / summarized / transcribed / error |

### Tabela

| Coluna | Ordenável | Fonte |
|--------|-----------|-------|
| Data/hora | Sim (default DESC) | `recordings.created_at` |
| Vendedor | Sim | `users.name` |
| Cliente | Sim | `customers.name` |
| Produto | Não | `recordings.product_raw` |
| Duração | Sim | `recordings.audio_duration_sec` |
| Status | Sim | `recordings.status` |

### Paginação

| Param | Default |
|-------|---------|
| page_size | 20 |
| Tipo | Offset-based (`?page=1&page_size=20`) |

### Botão Export

"Exportar Excel" → download de XLSX com todos os registros filtrados (sem paginação).

---

## Tela 6 — Detalhe do Registro (`/recordings/:id`)

### Seções

**Cabeçalho:**

| Campo | Valor |
|-------|-------|
| Data/hora | `created_at` formatado |
| Vendedor | `users.name` |
| Cliente | `customers.name` |
| Produto | `product_raw` |
| Duração | `audio_duration_sec` formatado (mm:ss) |
| Status | Badge colorido |

**Transcrição:**

Bloco de texto com `transcript_text`. Scroll se longo.

**Resumo IA:**

Bloco de texto com `summary_text` (markdown renderizado).

**Erro (se status=error):**

Banner vermelho com `error_message`.

---

## Tela 7 — Lista de Vendedores (`/sellers`)

### Tabela

| Coluna | Fonte |
|--------|-------|
| Nome | `users.name` |
| Telefone | `users.phone` |
| Status | Badge: ativo (verde) / inativo (cinza) |
| Telegram vinculado | Ícone: ✓ se `telegram_chat_id` preenchido, ✗ se null |
| Visitas (mês) | COUNT recordings últimos 30d |

### Ações

| Ação | Botão |
|------|-------|
| Novo vendedor | "Adicionar Vendedor" → `/sellers/new` |
| Editar | Ícone lápis → `/sellers/:id` |
| Desativar/Ativar | Toggle inline |

### Limite de vendedores

Se `seller_count >= seller_limit`: botão "Adicionar Vendedor" desabilitado + tooltip "Limite atingido. Faça upgrade do plano."

---

## Tela 8 — Cadastro de Vendedor (`/sellers/new`)

### Formulário

| Campo | Tipo | Validação |
|-------|------|-----------|
| Nome completo | text | obrigatório, min 3 chars |
| Celular | tel | obrigatório, formato BR (com máscara) |

### Comportamento

1. Frontend normaliza telefone para exibição com máscara `(XX) XXXXX-XXXX`
2. Submit → `POST /api/sellers`
3. Backend normaliza `phone_normalized` (somente dígitos com DDI)
4. Verifica limite de vendedores (`seller_count < seller_limit`)
5. Sucesso → redirect `/sellers` com toast "Vendedor cadastrado"
6. Erro limite → "Limite de vendedores atingido"
7. Erro telefone duplicado → "Telefone já cadastrado nesta organização"

---

## Tela 9 — Editar Vendedor (`/sellers/:id`)

Mesmo formulário do cadastro, preenchido. Campos adicionais (read-only):

| Campo | Valor |
|-------|-------|
| Telegram vinculado | Sim/Não (se sim, mostra chat_id) |
| Data de cadastro | `created_at` |
| Última visita | MAX(`recordings.created_at`) |

Botão "Desvincular Telegram" → limpa `telegram_chat_id` (vendedor precisará re-vincular).

---

## Tela 10 — Conta e Assinatura (`/account`)

### Seção: Dados da Empresa

| Campo | Editável | Fonte |
|-------|----------|-------|
| Nome empresa | Sim | `organizations.name` |
| Nome gestor | Sim | `users.name` |
| Email | Não (read-only) | `users.email` |
| Cargo | Sim | `users.job_title` |

Botão "Salvar" → `PUT /api/account`

### Seção: Assinatura

| Info | Fonte |
|------|-------|
| Status | Badge: trial/active/past_due |
| Plano | "X vendedores" |
| Próxima cobrança | `subscriptions.current_period_end` |
| Trial expira em | `subscriptions.trial_ends_at` (só se trial) |

Botão "Gerenciar assinatura" → redirect Stripe Customer Portal (Spec 05)

### Seção: Segurança

Botão "Alterar senha" → `supabase.auth.updateUser({ password })`

---

## Tela 11 — Admin: Lista de Orgs (`/admin/orgs`) — system_admin only

### Tabela

| Coluna | Fonte |
|--------|-------|
| Nome empresa | `organizations.name` |
| Gestor | `users.name` WHERE role=org_admin |
| Status assinatura | `subscriptions.status` |
| Vendedores | COUNT users WHERE role=seller |
| Visitas (mês) | COUNT recordings últimos 30d |
| Criada em | `organizations.created_at` |

Clique → `/admin/orgs/:id`

### Regra

system_admin: **somente leitura**. Não edita dados de negócio. Toda visualização gera log em `support_audit`.

---

## Contratos API — Backend (FastAPI)

### GET /api/stats

Dashboard stats da org logada.

**Headers:** `Authorization: Bearer <jwt>`

**Response:**
```json
{
    "sellers_active": 8,
    "recordings_today": 12,
    "recordings_week": 47,
    "recordings_month": 183
}
```

---

### GET /api/recordings

Lista de recordings da org.

**Headers:** `Authorization: Bearer <jwt>`

**Query params:**

| Param | Tipo | Default |
|-------|------|---------|
| page | int | 1 |
| page_size | int | 20 |
| seller_id | uuid | null (todos) |
| customer_id | uuid | null (todos) |
| status | string | null (todos) |
| date_from | date | null |
| date_to | date | null |
| sort_by | string | "created_at" |
| sort_order | string | "desc" |

**Response:**
```json
{
    "items": [
        {
            "id": "uuid",
            "created_at": "2026-03-01T14:30:00Z",
            "seller_name": "Pedro Alves",
            "customer_name": "Empresa XYZ",
            "product": "Software Premium",
            "audio_duration_sec": 180,
            "status": "summarized"
        }
    ],
    "total": 183,
    "page": 1,
    "page_size": 20,
    "pages": 10
}
```

---

### GET /api/recordings/:id

Detalhe de um recording.

**Headers:** `Authorization: Bearer <jwt>`

**Response:**
```json
{
    "id": "uuid",
    "created_at": "2026-03-01T14:30:00Z",
    "seller_name": "Pedro Alves",
    "customer_name": "Empresa XYZ",
    "product": "Software Premium",
    "audio_duration_sec": 180,
    "status": "summarized",
    "transcript_text": "Texto completo da transcrição...",
    "summary_text": "**Contexto**: Visita ao cliente...",
    "error_message": null
}
```

**404** se recording não pertence à org do usuário.

---

### GET /api/recordings/export

Export XLSX de recordings filtrados.

**Headers:** `Authorization: Bearer <jwt>`

**Query params:** mesmos de `GET /api/recordings` (exceto page/page_size).

**Response:** `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

**Colunas do Excel:**

| Coluna | Fonte |
|--------|-------|
| Data | `created_at` |
| Vendedor | `seller_name` |
| Cliente | `customer_name` |
| Produto | `product_raw` |
| Duração (min) | `audio_duration_sec / 60` |
| Transcrição | `transcript_text` |
| Resumo IA | `summary_text` |
| Status | `status` |

---

### GET /api/sellers

Lista de sellers da org.

**Headers:** `Authorization: Bearer <jwt>`

**Response:**
```json
{
    "items": [
        {
            "id": "uuid",
            "name": "Pedro Alves",
            "phone": "+5511999998888",
            "is_active": true,
            "telegram_linked": true,
            "recordings_month": 23,
            "created_at": "2026-02-15T10:00:00Z"
        }
    ],
    "seller_count": 8,
    "seller_limit": 15
}
```

---

### POST /api/sellers

Cadastrar novo vendedor.

**Headers:** `Authorization: Bearer <jwt>`

**Request:**
```json
{
    "name": "Pedro Alves",
    "phone": "11999998888"
}
```

**Response (201):**
```json
{
    "id": "uuid",
    "name": "Pedro Alves",
    "phone": "+5511999998888",
    "phone_normalized": "5511999998888",
    "is_active": true,
    "telegram_linked": false
}
```

**Erros:**

| Status | Causa |
|--------|-------|
| 400 | Validação (nome curto, telefone inválido) |
| 409 | Telefone duplicado na org |
| 403 | Limite de vendedores atingido |

---

### PUT /api/sellers/:id

Atualizar vendedor.

**Headers:** `Authorization: Bearer <jwt>`

**Request:**
```json
{
    "name": "Pedro Alves Silva",
    "phone": "11999997777",
    "is_active": true
}
```

**Response (200):** seller atualizado.

---

### DELETE /api/sellers/:id/telegram

Desvincular Telegram do vendedor.

**Headers:** `Authorization: Bearer <jwt>`

**Response (200):**
```json
{
    "message": "Telegram desvinculado. Vendedor precisará re-vincular."
}
```

---

### GET /api/account

Dados da conta do gestor.

**Headers:** `Authorization: Bearer <jwt>`

**Response:**
```json
{
    "user": {
        "name": "João Silva",
        "email": "joao@empresa.com.br",
        "job_title": "Diretor Comercial"
    },
    "organization": {
        "name": "Empresa ABC"
    },
    "subscription": {
        "status": "trial",
        "trial_ends_at": "2026-04-01T00:00:00Z",
        "current_period_end": null,
        "seller_count": 3,
        "seller_limit": 5,
        "stripe_portal_url": null
    }
}
```

---

### PUT /api/account

Atualizar dados da conta.

**Headers:** `Authorization: Bearer <jwt>`

**Request:**
```json
{
    "user_name": "João Silva Jr",
    "job_title": "CEO",
    "org_name": "Empresa ABC Ltda"
}
```

**Response (200):** conta atualizada.

---

### GET /api/admin/orgs (system_admin only)

Lista todas as organizações.

**Headers:** `Authorization: Bearer <jwt>`

**Response:**
```json
{
    "items": [
        {
            "id": "uuid",
            "name": "Empresa ABC",
            "admin_name": "João Silva",
            "admin_email": "joao@empresa.com.br",
            "subscription_status": "active",
            "seller_count": 8,
            "recordings_month": 183,
            "created_at": "2026-02-01T00:00:00Z"
        }
    ]
}
```

**403** se role != system_admin. Toda chamada gera log em `support_audit`.

---

## Proteção de Rotas (Frontend)

```javascript
// PrivateRoute: redireciona para /login se não autenticado
// AdminRoute: redireciona para /dashboard se role != system_admin
// SubscriptionGuard: exibe banner se trial/past_due, bloqueia se expired

const routes = [
    { path: "/login", element: <Login />, public: true },
    { path: "/signup", element: <Signup />, public: true },
    { path: "/forgot-password", element: <ForgotPassword />, public: true },
    { path: "/reset-password", element: <ResetPassword />, public: true },
    { path: "/dashboard", element: <PrivateRoute><SubscriptionGuard><Dashboard /></SubscriptionGuard></PrivateRoute> },
    { path: "/recordings", element: <PrivateRoute><SubscriptionGuard><Recordings /></SubscriptionGuard></PrivateRoute> },
    { path: "/recordings/:id", element: <PrivateRoute><SubscriptionGuard><RecordingDetail /></SubscriptionGuard></PrivateRoute> },
    { path: "/sellers", element: <PrivateRoute><SubscriptionGuard><Sellers /></SubscriptionGuard></PrivateRoute> },
    { path: "/sellers/new", element: <PrivateRoute><SubscriptionGuard><SellerForm /></SubscriptionGuard></PrivateRoute> },
    { path: "/sellers/:id", element: <PrivateRoute><SubscriptionGuard><SellerForm /></SubscriptionGuard></PrivateRoute> },
    { path: "/account", element: <PrivateRoute><Account /></PrivateRoute> },
    { path: "/admin/orgs", element: <AdminRoute><AdminOrgs /></AdminRoute> },
    { path: "/admin/orgs/:id", element: <AdminRoute><AdminOrgDetail /></AdminRoute> },
];
```

---

## Comportamento do SubscriptionGuard

| Status | Comportamento |
|--------|--------------|
| `trial` | Acesso normal + banner countdown |
| `active` | Acesso normal |
| `past_due` (≤30d) | Acesso read-only: pode ver dados, não pode cadastrar vendedores. Banner de alerta |
| `past_due` (>30d) | Bloqueio total: redirect para `/account` com mensagem |
| `expired` | Bloqueio total: redirect para `/account` com mensagem de dados serão deletados |
| `canceled` | Bloqueio total: redirect para `/account` |
