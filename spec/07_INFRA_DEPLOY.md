# 07 — INFRA & DEPLOY (v6)

## Status
PENDENTE — aguardando aprovação

## Decisões Canônicas

| Decisão | Valor |
|---------|-------|
| Backend hosting | Render (Starter $7 → Standard $25) |
| Frontend hosting | Vercel free tier |
| Banco de dados | Supabase (Free → Pro $25) |
| Domínio backend | api.salesecho.com.br |
| Domínio frontend | app.salesecho.com.br |
| Domínio landing | www.salesecho.com.br |
| Registro domínio | Registro.br |
| SSL | Automático (Render, Vercel, Supabase) |
| CI/CD | GitHub Actions (free tier) |
| Branch | master |

---

## Estrutura de Pastas do Repositório

```
salesecho/
├── spec/                           # Specs técnicas (01-05)
│   ├── 01_AUTH_ONBOARDING.md
│   ├── 02_DDL.md
│   ├── 03_PIPELINE_TELEGRAM.md
│   ├── 04_PORTAL_GESTOR.md
│   └── 05_STRIPE_BILLING.md
│
├── business/                       # Docs de negócio
│   └── 06_BUSINESS_CUSTOS.md
│
├── backend/                        # FastAPI (Python)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # Entrypoint FastAPI
│   │   ├── config.py               # Settings (env vars)
│   │   ├── database.py             # Conexão Supabase/PostgreSQL
│   │   ├── auth.py                 # JWT decode, get_current_user
│   │   ├── middleware.py            # CORS, subscription guard
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── webhook_telegram.py  # POST /api/webhook/telegram
│   │   │   ├── webhook_stripe.py    # POST /api/webhook/stripe
│   │   │   ├── recordings.py        # CRUD recordings
│   │   │   ├── sellers.py           # CRUD sellers
│   │   │   ├── billing.py           # Checkout, portal
│   │   │   ├── account.py           # Dados da conta
│   │   │   ├── stats.py             # Dashboard stats
│   │   │   └── admin.py             # system_admin endpoints
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── telegram.py          # Bot API (send message, download)
│   │   │   ├── transcription.py     # Groq Whisper
│   │   │   ├── summarization.py     # Groq Llama
│   │   │   ├── customer_resolver.py # Resolve/cria customer
│   │   │   ├── phone.py             # normalize_phone()
│   │   │   └── stripe_service.py    # Sync quantity, handlers
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py           # Pydantic models (request/response)
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── audio.py             # Cleanup, duration check
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── render.yaml                  # Render blueprint
│   └── .env.example
│
├── frontend/                        # React + Vite SPA
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── routes.jsx               # React Router config
│   │   ├── lib/
│   │   │   ├── supabase.js          # Supabase client init
│   │   │   └── api.js               # Axios/fetch wrapper → backend
│   │   ├── hooks/
│   │   │   ├── useAuth.js
│   │   │   └── useSubscription.js
│   │   ├── components/
│   │   │   ├── Layout.jsx
│   │   │   ├── PrivateRoute.jsx
│   │   │   ├── AdminRoute.jsx
│   │   │   ├── SubscriptionGuard.jsx
│   │   │   └── ...
│   │   └── pages/
│   │       ├── Login.jsx
│   │       ├── Signup.jsx
│   │       ├── ForgotPassword.jsx
│   │       ├── Dashboard.jsx
│   │       ├── Recordings.jsx
│   │       ├── RecordingDetail.jsx
│   │       ├── Sellers.jsx
│   │       ├── SellerForm.jsx
│   │       ├── Account.jsx
│   │       └── admin/
│   │           ├── AdminOrgs.jsx
│   │           └── AdminOrgDetail.jsx
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── package.json
│   ├── vercel.json
│   └── .env.example
│
├── supabase/                        # Migrations SQL
│   └── migrations/
│       └── 001_initial_schema.sql   # DDL completo (Spec 02)
│
├── .github/
│   └── workflows/
│       ├── backend.yml              # CI backend (lint + test)
│       └── frontend.yml             # CI frontend (lint + build)
│
├── .gitignore
└── README.md
```

---

## Dockerfile (Backend)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Diretório para áudios temporários
RUN mkdir -p /tmp/salesecho/audio

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## requirements.txt

```
fastapi==0.115.*
uvicorn[standard]==0.34.*
httpx==0.28.*
aiohttp==3.11.*
python-multipart==0.0.*
stripe==11.*
supabase==2.*
pyjwt[crypto]==2.*
python-dotenv==1.*
openpyxl==3.*
pydantic==2.*
```

---

## Env Vars Consolidadas

### Backend (.env)

| Variável | Origem | Exemplo |
|----------|--------|---------|
| `SUPABASE_URL` | Supabase Dashboard | `https://xxxx.supabase.co` |
| `SUPABASE_ANON_KEY` | Supabase Dashboard | `eyJ...` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Dashboard | `eyJ...` |
| `SUPABASE_JWT_SECRET` | Supabase Dashboard | `super-secret-jwt` |
| `DATABASE_URL` | Supabase Dashboard | `postgresql://...` |
| `TELEGRAM_BOT_TOKEN` | @BotFather | `123456:ABC-DEF` |
| `TELEGRAM_WEBHOOK_SECRET` | Gerado (uuid4) | `a1b2c3d4...` |
| `GROQ_API_KEY` | console.groq.com | `gsk_...` |
| `STRIPE_SECRET_KEY` | Stripe Dashboard | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | Stripe Dashboard | `whsec_...` |
| `STRIPE_PRICE_ID` | Stripe Dashboard | `price_...` |
| `AUDIO_TEMP_DIR` | Config | `/tmp/salesecho/audio` |
| `AUDIO_TTL_HOURS` | Config | `24` |
| `FRONTEND_URL` | Config | `https://app.salesecho.com.br` |
| `BACKEND_URL` | Config | `https://api.salesecho.com.br` |

### Frontend (.env)

| Variável | Exemplo |
|----------|---------|
| `VITE_SUPABASE_URL` | `https://xxxx.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | `eyJ...` |
| `VITE_API_URL` | `https://api.salesecho.com.br` |
| `VITE_STRIPE_PUBLISHABLE_KEY` | `pk_live_...` |

---

## Deploy — Render (Backend)

### render.yaml

```yaml
services:
  - type: web
    name: salesecho-api
    runtime: docker
    dockerfilePath: backend/Dockerfile
    dockerContext: backend
    envVars:
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_SERVICE_ROLE_KEY
        sync: false
      - key: DATABASE_URL
        sync: false
      - key: TELEGRAM_BOT_TOKEN
        sync: false
      - key: TELEGRAM_WEBHOOK_SECRET
        sync: false
      - key: GROQ_API_KEY
        sync: false
      - key: STRIPE_SECRET_KEY
        sync: false
      - key: STRIPE_WEBHOOK_SECRET
        sync: false
      - key: STRIPE_PRICE_ID
        sync: false
      - key: FRONTEND_URL
        value: https://app.salesecho.com.br
    plan: starter
    healthCheckPath: /health
    autoDeploy: true
    branch: master
```

### Health check endpoint

```python
@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

## Deploy — Vercel (Frontend)

### vercel.json

```json
{
    "rewrites": [
        { "source": "/(.*)", "destination": "/index.html" }
    ],
    "headers": [
        {
            "source": "/(.*)",
            "headers": [
                { "key": "X-Frame-Options", "value": "DENY" },
                { "key": "X-Content-Type-Options", "value": "nosniff" }
            ]
        }
    ]
}
```

### Configuração Vercel

1. Importar repo `ArnaldoFiori/salesecho`
2. Root directory: `frontend`
3. Build command: `npm run build`
4. Output directory: `dist`
5. Env vars: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL`, `VITE_STRIPE_PUBLISHABLE_KEY`
6. Custom domain: `app.salesecho.com.br`

---

## Deploy — Supabase

### Setup inicial

1. Criar projeto no Supabase Dashboard
2. Executar migration `001_initial_schema.sql` no SQL Editor
3. Anotar URL, anon key, service role key, JWT secret
4. Configurar Auth → Email templates (confirmação, reset password)
5. Configurar Auth → URL Configuration → Site URL: `https://app.salesecho.com.br`
6. Configurar Auth → URL Configuration → Redirect URLs: `https://app.salesecho.com.br/**`

---

## DNS (Registro.br)

| Registro | Tipo | Valor |
|----------|------|-------|
| `app.salesecho.com.br` | CNAME | `cname.vercel-dns.com` |
| `api.salesecho.com.br` | CNAME | `salesecho-api.onrender.com` |
| `www.salesecho.com.br` | CNAME | `cname.vercel-dns.com` (landing page) |

---

## GitHub Actions — CI

### backend.yml

```yaml
name: Backend CI
on:
  push:
    paths: ['backend/**']
  pull_request:
    paths: ['backend/**']

jobs:
  lint-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r backend/requirements.txt
      - run: pip install ruff pytest
      - run: ruff check backend/
      - run: cd backend && python -m pytest tests/ -v
```

### frontend.yml

```yaml
name: Frontend CI
on:
  push:
    paths: ['frontend/**']
  pull_request:
    paths: ['frontend/**']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: cd frontend && npm ci
      - run: cd frontend && npm run build
```

---

## Ordem de Deploy (primeira vez)

| Passo | Ação |
|-------|------|
| 1 | Criar projeto Supabase, executar DDL |
| 2 | Registrar domínio salesecho.com.br |
| 3 | Criar bot Telegram via @BotFather |
| 4 | Criar contas Groq, Stripe |
| 5 | Deploy backend no Render (com env vars) |
| 6 | Deploy frontend no Vercel (com env vars) |
| 7 | Configurar DNS no Registro.br |
| 8 | Configurar webhook Telegram: `POST /setWebhook` apontando para `https://api.salesecho.com.br/api/webhook/telegram` |
| 9 | Configurar webhook Stripe apontando para `https://api.salesecho.com.br/api/webhook/stripe` |
| 10 | Smoke test: signup → login → cadastrar seller → enviar áudio Telegram |
