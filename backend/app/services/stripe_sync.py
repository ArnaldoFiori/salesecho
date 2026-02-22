import logging
import stripe
from app.config import settings
from app import database as db

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


async def sync_seller_quantity(org_id: str):
    """Sincroniza quantity no Stripe com seller_count real."""
    seller_count = await db.fetchval(
        "SELECT COUNT(*) FROM users WHERE org_id = $1 AND role = 'seller'",
        [org_id],
    )
    seller_count = max(seller_count, 1)

    sub = await db.fetchone(
        "SELECT stripe_subscription_id FROM subscriptions WHERE org_id = $1",
        [org_id],
    )
    if not sub or not sub["stripe_subscription_id"]:
        return

    try:
        stripe_sub = stripe.Subscription.retrieve(sub["stripe_subscription_id"])
        item_id = stripe_sub["items"]["data"][0]["id"]

        stripe.SubscriptionItem.modify(
            item_id,
            quantity=seller_count,
            proration_behavior="create_prorations",
        )
        logger.info(f"Stripe quantity updated to {seller_count} for org {org_id}")
    except Exception as e:
        logger.error(f"Failed to sync seller quantity for org {org_id}: {e}")
