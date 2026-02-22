from fastapi import APIRouter, Depends
from app.auth import get_current_user, CurrentUser, require_org_admin
from app import database as db

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
async def get_stats(user: CurrentUser = Depends(require_org_admin)):
    sellers_active = await db.fetchval(
        "SELECT COUNT(*) FROM users WHERE org_id = $1 AND role = 'seller' AND is_active = true",
        [user.org_id],
    )

    recordings_today = await db.fetchval(
        "SELECT COUNT(*) FROM recordings WHERE org_id = $1 AND created_at >= CURRENT_DATE",
        [user.org_id],
    )

    recordings_week = await db.fetchval(
        "SELECT COUNT(*) FROM recordings WHERE org_id = $1 AND created_at >= CURRENT_DATE - INTERVAL '7 days'",
        [user.org_id],
    )

    recordings_month = await db.fetchval(
        "SELECT COUNT(*) FROM recordings WHERE org_id = $1 AND created_at >= CURRENT_DATE - INTERVAL '30 days'",
        [user.org_id],
    )

    return {
        "sellers_active": sellers_active,
        "recordings_today": recordings_today,
        "recordings_week": recordings_week,
        "recordings_month": recordings_month,
    }
