from fastapi import APIRouter, Depends
from app.auth import CurrentUser, require_system_admin
from app import database as db

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/orgs")
async def list_orgs(user: CurrentUser = Depends(require_system_admin)):
    # Audit log
    await db.execute(
        """INSERT INTO support_audit (admin_user_id, action, target_table, details)
           VALUES ($1, 'list_orgs', 'organizations', '{}')""",
        [user.user_id],
    )

    rows = await db.fetchall("""
        SELECT o.id, o.name, o.created_at,
               s.status::text as subscription_status,
               (SELECT u.name FROM users u WHERE u.org_id = o.id AND u.role = 'org_admin' LIMIT 1) as admin_name,
               (SELECT u.email FROM users u WHERE u.org_id = o.id AND u.role = 'org_admin' LIMIT 1) as admin_email,
               (SELECT COUNT(*) FROM users u WHERE u.org_id = o.id AND u.role = 'seller') as seller_count,
               (SELECT COUNT(*) FROM recordings r WHERE r.org_id = o.id
                AND r.created_at >= CURRENT_DATE - INTERVAL '30 days') as recordings_month
        FROM organizations o
        LEFT JOIN subscriptions s ON s.org_id = o.id
        ORDER BY o.created_at DESC
    """)

    items = []
    for r in rows:
        items.append({
            "id": str(r["id"]),
            "name": r["name"],
            "admin_name": r["admin_name"],
            "admin_email": r["admin_email"],
            "subscription_status": r["subscription_status"],
            "seller_count": r["seller_count"],
            "recordings_month": r["recordings_month"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        })

    return {"items": items}


@router.get("/metrics")
async def get_metrics(user: CurrentUser = Depends(require_system_admin)):
    total_orgs = await db.fetchval("SELECT COUNT(*) FROM organizations")
    total_sellers = await db.fetchval("SELECT COUNT(*) FROM users WHERE role = 'seller'")
    total_recordings = await db.fetchval("SELECT COUNT(*) FROM recordings")
    recordings_today = await db.fetchval(
        "SELECT COUNT(*) FROM recordings WHERE created_at >= CURRENT_DATE"
    )
    error_count = await db.fetchval(
        "SELECT COUNT(*) FROM recordings WHERE status = 'error' AND created_at >= CURRENT_DATE - INTERVAL '7 days'"
    )

    return {
        "total_orgs": total_orgs,
        "total_sellers": total_sellers,
        "total_recordings": total_recordings,
        "recordings_today": recordings_today,
        "errors_last_7d": error_count,
    }
