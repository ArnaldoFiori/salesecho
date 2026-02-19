# 07 — INFRA & DEPLOY (v6)

## Status
APROVADO (v2: correções Spec 12)

## Decisões Canônicas

| Decisão | Valor |
|---------|-------|
| Backend hosting | Render (Starter $7 → Standard $25) |
| Frontend hosting | Vercel free tier |
| Banco de dados | **Supabase Pro ($25/mês)** — não usar Free (hiberna após 7d) |
| Domínio backend | api.salesecho.com.br |
| Domínio frontend | app.salesecho.com.br |
| Domínio landing | www.salesecho.com.br |
| Registro domínio | Registro.br |
| SSL | Automático (Render, Vercel, Supabase) |
| CI/CD | GitHub Actions (free tier) |
| Branch | master |
| Keep-alive | UptimeRobot gratuito (impede hibernação do Render Starter) |

---

## Estrutura de Pastas do Repositório

```
salesecho/
├── spec/                           # Specs técnicas (01-12)
├── business/                       # Docs de negócio
│
├── backend/                        # FastAPI (Python)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # Entrypoint FastAPI
│   │   ├── config.py               # Settings (env vars)
│   │   ├── database.py             # Conexão Supabase/PostgreSQL
│   │   ├── auth.py                 # JWT decode, get_current_user
│   │   ├── middleware.py            # CORS, rate limit, subscription guard
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── webhook_telegram.py
│   │   │   ├── webhook_stripe.py
│   │   │   ├── recordings.py
│   │   │   ├── sellers.py
│   │   │   ├── billing.py
│   │   │   ├── account.py
│   │   │   ├── stats.py
│   │   │   └── admin.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── telegram.py
│   │   │   ├── transcription.py
│   │   │   ├── summarization.py
│   │   │   ├── customer_resolver.py
│   │   │   ├── phone.py
│   │   │   ├── stripe_service.py
│   │   │   └── email.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── audio.py
│   │       └── metrics.py
│   ├── tests/
│   │   └── ...
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── render.yaml
│   └── .env.example
│
├── frontend/                        # React + Vite SPA
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── routes.jsx
│   │   ├── lib/
│   │   │   ├── supabase.js
│   │   │   └── api.js
│   │   ├── hooks/
│   │   │   ├── useAuth.js
│   │   │   └── useSubscription.js
│   │   ├── components/
│   │   │   ├── Layout.jsx
│   │   │   ├── PrivateRoute.jsx
│   │   │   ├── AdminRoute.jsx
│   │   │   └── SubscriptionGuard.jsx
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
│   │       ├── Terms.jsx
│   │       ├── Privacy.jsx
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
├── supabase/
│   └── migrations/
│       └── 001_initial_schema.sql
│
├── .github/
│   └── workflows/
│       ├── backend.yml
│       └── frontend.yml
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
python-multipart==0.0.*
stripe==11.*
supabase==2.*
pyjwt[crypto]==2.*
python-dotenv==1.*
openpyxl==3.*
pydantic==2.*
slowapi==0.1.*
```

---

## CORS — Configuração Obrigatória

```python
# app/middleware.py
from fastapi.middleware.cors import CORSMiddleware

def setup_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            FRONTEND_URL,                    # https://app.salesecho.com.br
            "http://localhost:5173",          # dev local
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

---

## Rate Limiting

Proteção contra abuso usando `slowapi` (baseado em `limits`).

```python
# app/middleware.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

def setup_rate_limit(app):
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

### Limites por endpoint

| Endpoint | Limite | Justificativa |
|----------|--------|--------------|
| `POST /api/webhook/telegram` | 120/min por IP | Telegram pode enviar rajadas |
| `POST /auth/login` (Supabase) | 10/min por IP | Anti brute-force |
| `POST /api/billing/checkout` | 5/min por IP | Evitar criação excessiva |
| `GET /api/recordings` | 60/min por IP | Uso normal |
| `GET /api/recordings/export` | 5/min por IP | Export é pesado |
| Default (demais rotas) | 60/min por IP | Uso geral |

```python
# Exemplo de uso nos routers
from app.middleware import limiter

@app.post("/api/webhook/telegram")
@limiter.limit("120/minute")
async def telegram_webhook(request: Request):
    ...

@app.get("/api/recordings/export")
@limiter.limit("5/minute")
async def export_recordings(request: Request, ...):
    ...
```

---

## Keep-Alive — Impedir Hibernação do Render Starter

Render Starter hiberna após 15 min sem requests. Cold start leva ~30s. Webhooks do Telegram podem falhar.

### Solução: UptimeRobot (gratuito)

| Monitor | URL | Intervalo |
|---------|-----|-----------|
| Backend health | `https://api.salesecho.com.br/health` | 5 min |
| Frontend | `https://app.salesecho.com.br` | 5 min |

UptimeRobot faz GET a cada 5 min → Render nunca hiberna.

### Alternativa: upgrade para Render Standard ($25/mês)

Render Standard não hiberna. Considerar quando receita justificar.

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
| `RESEND_API_KEY` | Resend Dashboard | `re_...` |
| `AUDIO_TEMP_DIR` | Config | `/tmp/salesecho/audio` |
| `AUDIO_TTL_HOURS` | Config | `24` |
| `FRONTEND_URL` | Config | `https://app.salesecho.com.br` |
| `BACKEND_URL` | Config | `https://api.salesecho.com.br` |
| `ADMIN_TELEGRAM_CHAT_ID` | Telegram | `123456789` |
| `ALERT_ENABLED` | Config | `true` |

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
      - key: RESEND_API_KEY
        sync: false
      - key: ADMIN_TELEGRAM_CHAT_ID
        sync: false
      - key: ALERT_ENABLED
        value: "true"
      - key: FRONTEND_URL
        value: https://app.salesecho.com.br
      - key: BACKEND_URL
        value: https://api.salesecho.com.br
    plan: starter
    healthCheckPath: /health
    autoDeploy: true
    branch: master
```

### Health check

```python
@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
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

### Configuração

1. Importar repo `ArnaldoFiori/salesecho`
2. Root directory: `frontend`
3. Build command: `npm run build`
4. Output directory: `dist`
5. Env vars: todas as `VITE_*`
6. Custom domain: `app.salesecho.com.br`

---

## Deploy — Supabase

### Setup

1. Criar projeto Supabase **(plano Pro, $25/mês)**
2. Executar migration `001_initial_schema.sql` no SQL Editor
3. Auth → Email templates: customizar com branding
4. Auth → URL Configuration → Site URL: `https://app.salesecho.com.br`
5. Auth → URL Configuration → Redirect URLs: `https://app.salesecho.com.br/**`
6. Auth → JWT Settings: confirmar expiry = 3600 (1h)

**Por que Supabase Pro:** o plano Free pausa o banco após 7 dias sem atividade. Um webhook do Telegram em horário de baixo uso (madrugada/fim de semana) pode encontrar o banco pausado e falhar silenciosamente. Pro nunca pausa.

---

## DNS (Registro.br)

| Registro | Tipo | Valor |
|----------|------|-------|
| `app.salesecho.com.br` | CNAME | `cname.vercel-dns.com` |
| `api.salesecho.com.br` | CNAME | `salesecho-api.onrender.com` |
| `www.salesecho.com.br` | CNAME | `cname.vercel-dns.com` |

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
| 1 | Criar projeto Supabase **Pro**, executar DDL |
| 2 | Registrar domínio salesecho.com.br |
| 3 | Criar bot Telegram via @BotFather |
| 4 | Criar contas Groq, Stripe, Resend |
| 5 | Deploy backend no Render (com env vars) |
| 6 | Deploy frontend no Vercel (com env vars) |
| 7 | Configurar DNS no Registro.br |
| 8 | Configurar webhook Telegram com `secret_token` |
| 9 | Configurar webhook Stripe |
| 10 | Configurar UptimeRobot (2 monitores: backend + frontend) |
| 11 | Configurar Resend (verificar domínio, SPF, DKIM, DMARC) |
| 12 | Smoke test: signup → login → cadastrar seller → enviar áudio Telegram |
