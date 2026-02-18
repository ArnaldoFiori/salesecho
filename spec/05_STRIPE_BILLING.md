# 05 — STRIPE: ASSINATURA E BILLING (v6)

## Status
PENDENTE — aguardando aprovação

## Decisões Canônicas

| Decisão | Valor |
|---------|-------|
| Gateway | Stripe |
| Modelo | Recorrente mensal |
| Unidade de cobrança | Vendedor cadastrado (ativo ou não) |
| Moeda | BRL |
| Trial | 30 dias, sem cartão |
| Checkout | Stripe Checkout (hosted) |
| Portal do cliente | Stripe Customer Portal (hosted) |
| Webhooks | Stripe → backend FastAPI |
| Plano | Preço unitário por vendedor/mês (price_per_seller) |

---

## Modelo de Pricing

| Item | Valor |
|------|-------|
| Preço por vendedor/mês | Configurável via Stripe Dashboard (ex: R$ 29,90/vendedor) |
| Produto Stripe | 1 produto "SalesEcho — Plano por Vendedor" |
| Price Stripe | 1 price com `unit_amount` = preço por vendedor |
| Quantity | = número de sellers cadastrados na org (ativos ou não) |
| Mínimo | 1 vendedor |
| Desconto volume | Não no MVP |

### Criação no Stripe Dashboard (manual, uma vez)

1. Criar Product: "SalesEcho — Plano por Vendedor"
2. Criar Price: recorrente mensal, BRL, `unit_amount` = valor por vendedor
3. Anotar `STRIPE_PRICE_ID` para env var

---

## Fluxo 1 — Trial → Assinatura (primeiro pagamento)

### Passo a passo

1. Trial ativo, gestor clica "Assinar" no portal (`/account`)
2. Frontend chama `POST /api/billing/checkout`
3. Backend:
   a. Cria Stripe Customer (se não existe) com email do org_admin
   b. Cria Stripe Checkout Session:
      - `mode: "subscription"`
      - `line_items: [{ price: STRIPE_PRICE_ID, quantity: seller_count }]`
      - `subscription_data.trial_period_days: null` (trial já aconteceu no app)
      - `success_url: app.salesecho.com.br/account?checkout=success`
      - `cancel_url: app.salesecho.com.br/account?checkout=cancel`
      - `customer: stripe_customer_id`
      - `metadata: { org_id: "uuid" }`
   c. Salva `stripe_customer_id` em `subscriptions`
   d. Retorna `checkout_url`
4. Frontend redireciona para Stripe Checkout (hosted)
5. Gestor preenche cartão e confirma
6. Stripe envia webhook `checkout.session.completed`
7. Backend processa webhook:
   a. Extrai `subscription_id` da session
   b. Atualiza `subscriptions`:
      - `stripe_subscription_id = subscription_id`
      - `status = 'active'`
      - `current_period_end` = data do Stripe
      - `seller_limit = NULL` (sem limite quando pagante, ou manter quantidade contratada)
      - `trial_ends_at = NULL`

---

## Fluxo 2 — Atualização de Quantity (add/remove vendedores)

### Quando acontece

Sempre que org_admin cadastra ou desativa um vendedor.

### Passo a passo

1. Org_admin cadastra novo seller via `POST /api/sellers`
2. Backend cria seller no DB
3. Backend verifica se org tem `stripe_subscription_id` ativo
4. Se sim: atualiza quantity no Stripe

```python
async def sync_seller_quantity(org_id: str):
    """Sincroniza quantity no Stripe com seller_count real."""
    # Contar sellers cadastrados (ativos ou não)
    seller_count = await db.fetchval(
        "SELECT COUNT(*) FROM users WHERE org_id = :org_id AND role = 'seller'",
        {"org_id": org_id}
    )
    seller_count = max(seller_count, 1)  # mínimo 1

    sub = await db.fetchone(
        "SELECT stripe_subscription_id FROM subscriptions WHERE org_id = :org_id",
        {"org_id": org_id}
    )
    if not sub or not sub["stripe_subscription_id"]:
        return  # Trial ou sem Stripe — não sincroniza

    # Buscar subscription item do Stripe
    stripe_sub = stripe.Subscription.retrieve(sub["stripe_subscription_id"])
    item_id = stripe_sub["items"]["data"][0]["id"]

    # Atualizar quantity
    stripe.SubscriptionItem.modify(
        item_id,
        quantity=seller_count,
        proration_behavior="create_prorations"  # cobra proporcional imediato
    )
```

### Proration (cobrança proporcional)

| Ação | Comportamento Stripe |
|------|---------------------|
| Adicionar vendedor | Proration: cobra proporcional dos dias restantes no ciclo atual |
| Remover vendedor (desativar) | Proration: crédito proporcional aplicado na próxima fatura |
| Reativar vendedor | Proration: cobra proporcional novamente |

---

## Fluxo 3 — Ciclo de Cobrança Mensal

```
Stripe cobra automaticamente
    │
    ├── Sucesso → webhook: invoice.payment_succeeded
    │   └── Backend: status mantém 'active', atualiza current_period_end
    │
    ├── Falha → webhook: invoice.payment_failed
    │   └── Stripe retenta automaticamente (Smart Retries)
    │       ├── Retentativa sucesso → invoice.payment_succeeded
    │       └── Retentativas esgotadas → customer.subscription.updated (status=past_due)
    │           └── Backend: status → 'past_due'
    │
    └── Assinatura cancelada (pelo Stripe ou gestor) → customer.subscription.deleted
        └── Backend: status → 'canceled'
```

---

## Fluxo 4 — Inadimplência

Conforme Spec 01:

| Fase | Tempo | Status DB | Acesso |
|------|-------|-----------|--------|
| Pagamento falhou | Dia 0 | `active` (Stripe retenta) | Normal |
| Retentativas esgotadas | ~Dia 7 | `past_due` | Read-only (30 dias) |
| 30 dias sem pagar | Dia 37 | `past_due` (>30d check no app) | Bloqueio total |
| Cancelamento Stripe | Varia | `canceled` | Bloqueio, dados preservados |

### Lógica no backend (middleware/guard)

```python
async def check_org_access(org_id: str) -> dict:
    """Retorna nível de acesso da org."""
    sub = await db.fetchone(
        "SELECT status, current_period_end, trial_ends_at FROM subscriptions WHERE org_id = :org_id",
        {"org_id": org_id}
    )

    if sub["status"] == "trial":
        if sub["trial_ends_at"] > now():
            return {"access": "full", "warning": "trial"}
        else:
            return {"access": "blocked", "reason": "trial_expired"}

    if sub["status"] == "active":
        return {"access": "full"}

    if sub["status"] == "past_due":
        days_overdue = (now() - sub["current_period_end"]).days
        if days_overdue <= 30:
            return {"access": "read_only", "reason": "past_due", "days_overdue": days_overdue}
        else:
            return {"access": "blocked", "reason": "past_due_exceeded"}

    if sub["status"] in ("canceled", "expired"):
        return {"access": "blocked", "reason": sub["status"]}

    return {"access": "blocked", "reason": "unknown"}
```

---

## Fluxo 5 — Stripe Customer Portal (gerenciar assinatura)

Gestor acessa via botão "Gerenciar assinatura" em `/account`.

### O que o portal permite

| Ação | Habilitado |
|------|-----------|
| Atualizar cartão | Sim |
| Ver faturas | Sim |
| Cancelar assinatura | Sim |
| Reativar após cancelamento | Sim |
| Mudar plano | Não (plano único no MVP) |

### Endpoint

```python
@app.post("/api/billing/portal")
async def create_portal_session(user = Depends(get_current_user)):
    sub = await get_subscription(user.org_id)
    if not sub.stripe_customer_id:
        raise HTTPException(400, "Sem assinatura ativa")

    session = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url="https://app.salesecho.com.br/account"
    )
    return {"portal_url": session.url}
```

### Configuração do Portal (Stripe Dashboard, uma vez)

1. Settings → Billing → Customer Portal
2. Habilitar: Update payment method, View invoices, Cancel subscription
3. Desabilitar: Switch plans (plano único)
4. Redirect URL: `https://app.salesecho.com.br/account`

---

## Webhooks Stripe → Backend

### Endpoint

```
POST /api/webhook/stripe
```

### Verificação de assinatura

```python
@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(400, "Invalid signature")

    await handle_stripe_event(event)
    return Response(status_code=200)
```

### Eventos processados

| Evento Stripe | Ação no backend |
|---------------|-----------------|
| `checkout.session.completed` | Criar/atualizar subscription (status=active, salvar IDs Stripe) |
| `invoice.payment_succeeded` | Atualizar `current_period_end`, confirmar status=active |
| `invoice.payment_failed` | Log (Stripe retenta automaticamente) |
| `customer.subscription.updated` | Sincronizar status (active/past_due/canceled) + `current_period_end` |
| `customer.subscription.deleted` | Status → canceled |

### Handler

```python
async def handle_stripe_event(event: dict):
    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        org_id = data["metadata"]["org_id"]
        subscription_id = data["subscription"]
        customer_id = data["customer"]

        # Buscar detalhes da subscription
        stripe_sub = stripe.Subscription.retrieve(subscription_id)

        await db.execute(
            """UPDATE subscriptions SET
                stripe_customer_id = :customer_id,
                stripe_subscription_id = :subscription_id,
                status = 'active',
                current_period_end = to_timestamp(:period_end),
                trial_ends_at = NULL,
                updated_at = now()
            WHERE org_id = :org_id""",
            {
                "customer_id": customer_id,
                "subscription_id": subscription_id,
                "period_end": stripe_sub["current_period_end"],
                "org_id": org_id
            }
        )

    elif event_type == "invoice.payment_succeeded":
        subscription_id = data.get("subscription")
        if not subscription_id:
            return
        stripe_sub = stripe.Subscription.retrieve(subscription_id)
        await db.execute(
            """UPDATE subscriptions SET
                status = 'active',
                current_period_end = to_timestamp(:period_end),
                updated_at = now()
            WHERE stripe_subscription_id = :sub_id""",
            {
                "period_end": stripe_sub["current_period_end"],
                "sub_id": subscription_id
            }
        )

    elif event_type == "customer.subscription.updated":
        subscription_id = data["id"]
        stripe_status = data["status"]
        status_map = {
            "active": "active",
            "past_due": "past_due",
            "canceled": "canceled",
            "unpaid": "past_due",
            "incomplete": "past_due",
            "incomplete_expired": "canceled",
            "trialing": "trial",  # não deve ocorrer (trial é interno)
        }
        db_status = status_map.get(stripe_status, "active")
        await db.execute(
            """UPDATE subscriptions SET
                status = :status,
                current_period_end = to_timestamp(:period_end),
                updated_at = now()
            WHERE stripe_subscription_id = :sub_id""",
            {
                "status": db_status,
                "period_end": data["current_period_end"],
                "sub_id": subscription_id
            }
        )

    elif event_type == "customer.subscription.deleted":
        subscription_id = data["id"]
        await db.execute(
            """UPDATE subscriptions SET
                status = 'canceled',
                updated_at = now()
            WHERE stripe_subscription_id = :sub_id""",
            {"sub_id": subscription_id}
        )

    elif event_type == "invoice.payment_failed":
        # Log apenas — Stripe retenta automaticamente
        subscription_id = data.get("subscription")
        logger.warning(f"Payment failed for subscription {subscription_id}")
```

---

## Contratos API — Billing

### POST /api/billing/checkout

Criar sessão de checkout para assinar.

**Headers:** `Authorization: Bearer <jwt>`

**Request:**
```json
{}
```

**Response (200):**
```json
{
    "checkout_url": "https://checkout.stripe.com/c/pay/cs_live_..."
}
```

**Erros:**

| Status | Causa |
|--------|-------|
| 400 | Org já tem assinatura ativa |
| 403 | Acesso negado |

---

### POST /api/billing/portal

Criar sessão do Customer Portal.

**Headers:** `Authorization: Bearer <jwt>`

**Request:**
```json
{}
```

**Response (200):**
```json
{
    "portal_url": "https://billing.stripe.com/p/session/..."
}
```

**Erros:**

| Status | Causa |
|--------|-------|
| 400 | Org não tem stripe_customer_id (nunca assinou) |

---

### POST /api/webhook/stripe

Webhook do Stripe (chamado pelo Stripe, não pelo frontend).

**Headers:** `Stripe-Signature: t=...,v1=...`

**Request:** corpo raw do Stripe Event.

**Response:** `200 OK` (body vazio)

---

## Configuração Stripe (env vars)

| Variável | Descrição |
|----------|-----------|
| `STRIPE_SECRET_KEY` | API key (sk_live_ ou sk_test_) |
| `STRIPE_PUBLISHABLE_KEY` | Publishable key (pk_live_ ou pk_test_) |
| `STRIPE_WEBHOOK_SECRET` | Webhook signing secret (whsec_) |
| `STRIPE_PRICE_ID` | ID do Price recorrente mensal (price_) |

---

## Setup Stripe (checklist manual, uma vez)

| Passo | Ação |
|-------|------|
| 1 | Criar conta Stripe (stripe.com) |
| 2 | Criar Product "SalesEcho — Plano por Vendedor" |
| 3 | Criar Price recorrente mensal em BRL |
| 4 | Configurar Customer Portal (Settings → Billing → Customer Portal) |
| 5 | Criar Webhook endpoint apontando para `https://api.salesecho.com.br/api/webhook/stripe` |
| 6 | Selecionar eventos: `checkout.session.completed`, `invoice.payment_succeeded`, `invoice.payment_failed`, `customer.subscription.updated`, `customer.subscription.deleted` |
| 7 | Anotar webhook secret |
| 8 | Configurar env vars no backend |

---

## Fluxo de Teste (Stripe Test Mode)

| Cartão teste | Resultado |
|-------------|-----------|
| `4242 4242 4242 4242` | Sucesso |
| `4000 0000 0000 9995` | Pagamento recusado |
| `4000 0000 0000 0341` | Falha no attach |

Usar `stripe listen --forward-to localhost:8000/api/webhook/stripe` para testar webhooks localmente.

---

## Diagrama de Estados — Subscription

```
                    ┌─────────┐
        Signup ──>  │  trial  │
                    └────┬────┘
                         │
              ┌──────────┼──────────┐
              │                     │
         Assinou               Não assinou
              │                     │
              ▼                     ▼
        ┌──────────┐         ┌──────────┐
        │  active  │         │ expired  │ ──> dados deletados (7d)
        └────┬─────┘         └──────────┘
             │
    ┌────────┼────────┐
    │                 │
 Pagou            Não pagou
    │                 │
    ▼                 ▼
 (mantém           ┌──────────┐
  active)          │ past_due │ ──> 30d read-only
                   └────┬─────┘     depois bloqueio
                        │
               ┌────────┼────────┐
               │                 │
           Regularizou       Cancelou/Stripe
               │                 │
               ▼                 ▼
         ┌──────────┐     ┌───────────┐
         │  active  │     │ canceled  │ ──> dados preservados
         └──────────┘     └───────────┘
```
