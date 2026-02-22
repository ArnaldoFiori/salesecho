import logging
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from app.auth import CurrentUser, require_org_admin
from app.config import settings
from app import database as db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["billing"])

stripe.api_key = settings.STRIPE_SECRET_KEY


@router.post("/billing/checkout")
async def create_checkout(user: CurrentUser = Depends(require_org_admin)):
    sub = await db.fetchone(
        "SELECT id, status::text, stripe_customer_id, stripe_subscription_id FROM subscriptions WHERE org_id = $1",
        [user.org_id],
    )
    if not sub:
        raise HTTPException(400, "Subscription not found")

    if sub["stripe_subscription_id"] and sub["status"] == "active":
        raise HTTPException(400, "Org já tem assinatura ativa")

    # Criar ou reutilizar Stripe Customer
    customer_id = sub["stripe_customer_id"]
    if not customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=user.name,
            metadata={"org_id": user.org_id},
        )
        customer_id = customer.id
        await db.execute(
            "UPDATE subscriptions SET stripe_customer_id = $1 WHERE org_id = $2",
            [customer_id, user.org_id],
        )

    # Contar sellers
    seller_count = await db.fetchval(
        "SELECT COUNT(*) FROM users WHERE org_id = $1 AND role = 'seller'",
        [user.org_id],
    )
    seller_count = max(seller_count, 1)

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{
            "price": settings.STRIPE_PRICE_ID,
            "quantity": seller_count,
        }],
        subscription_data={
            "metadata": {"org_id": user.org_id},
        },
        success_url=f"{settings.FRONTEND_URL}/account?checkout=success",
        cancel_url=f"{settings.FRONTEND_URL}/account?checkout=cancel",
        metadata={"org_id": user.org_id},
        payment_method_types=["card"],
    )

    return {"checkout_url": session.url}


@router.post("/billing/portal")
async def create_portal(user: CurrentUser = Depends(require_org_admin)):
    sub = await db.fetchone(
        "SELECT stripe_customer_id FROM subscriptions WHERE org_id = $1",
        [user.org_id],
    )
    if not sub or not sub["stripe_customer_id"]:
        raise HTTPException(400, "Sem assinatura ativa")

    session = stripe.billing_portal.Session.create(
        customer=sub["stripe_customer_id"],
        return_url=f"{settings.FRONTEND_URL}/account",
    )
    return {"portal_url": session.url}


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")

    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("STRIPE_WEBHOOK_SECRET not set, skipping verification")
        try:
            event = stripe.Event.construct_from(
                stripe.util.convert_to_stripe_object(
                    stripe.util.json.loads(payload)
                ),
                stripe.api_key,
            )
        except Exception:
            raise HTTPException(400, "Invalid payload")
    else:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            raise HTTPException(400, "Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(400, "Invalid signature")

    await handle_stripe_event(event)
    return Response(status_code=200)


async def handle_stripe_event(event):
    event_type = event["type"]
    data = event["data"]["object"]
    logger.info(f"Stripe event: {event_type}")

    if event_type == "checkout.session.completed":
        org_id = data.get("metadata", {}).get("org_id")
        subscription_id = data.get("subscription")
        customer_id = data.get("customer")

        if not org_id or not subscription_id:
            logger.warning("checkout.session.completed missing org_id or subscription_id")
            return

        stripe_sub = stripe.Subscription.retrieve(subscription_id)

        await db.execute(
            """UPDATE subscriptions SET
                stripe_customer_id = $1,
                stripe_subscription_id = $2,
                status = 'active',
                current_period_end = to_timestamp($3::double precision),
                trial_ends_at = NULL,
                updated_at = now()
            WHERE org_id = $4""",
            [customer_id, subscription_id,
             float(stripe_sub["current_period_end"]), org_id],
        )
        logger.info(f"Subscription activated for org {org_id}")

    elif event_type == "invoice.payment_succeeded":
        subscription_id = data.get("subscription")
        if not subscription_id:
            return
        stripe_sub = stripe.Subscription.retrieve(subscription_id)
        await db.execute(
            """UPDATE subscriptions SET
                status = 'active',
                current_period_end = to_timestamp($1::double precision),
                updated_at = now()
            WHERE stripe_subscription_id = $2""",
            [float(stripe_sub["current_period_end"]), subscription_id],
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
            "trialing": "trial",
        }
        db_status = status_map.get(stripe_status, "active")
        await db.execute(
            """UPDATE subscriptions SET
                status = $1,
                current_period_end = to_timestamp($2::double precision),
                updated_at = now()
            WHERE stripe_subscription_id = $3""",
            [db_status, float(data["current_period_end"]), subscription_id],
        )

    elif event_type == "customer.subscription.deleted":
        subscription_id = data["id"]
        await db.execute(
            """UPDATE subscriptions SET
                status = 'canceled',
                updated_at = now()
            WHERE stripe_subscription_id = $1""",
            [subscription_id],
        )

    elif event_type == "invoice.payment_failed":
        subscription_id = data.get("subscription")
        logger.warning(f"Payment failed for subscription {subscription_id}")
