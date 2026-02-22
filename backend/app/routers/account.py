from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth import CurrentUser, require_org_admin
from app import database as db

router = APIRouter(prefix="/api", tags=["account"])


class AccountUpdate(BaseModel):
    user_name: str | None = None
    job_title: str | None = None
    org_name: str | None = None


@router.get("/account")
async def get_account(user: CurrentUser = Depends(require_org_admin)):
    u = await db.fetchone(
        "SELECT name, email, job_title FROM users WHERE id = $1",
        [user.user_id],
    )
    org = await db.fetchone(
        "SELECT name FROM organizations WHERE id = $1",
        [user.org_id],
    )
    sub = await db.fetchone(
        """SELECT status::text, trial_ends_at, current_period_end, seller_limit,
                  stripe_customer_id
           FROM subscriptions WHERE org_id = $1""",
        [user.org_id],
    )

    seller_count = await db.fetchval(
        "SELECT COUNT(*) FROM users WHERE org_id = $1 AND role = 'seller'",
        [user.org_id],
    )

    return {
        "user": {
            "name": u["name"] if u else None,
            "email": u["email"] if u else None,
            "job_title": u["job_title"] if u else None,
        },
        "organization": {
            "name": org["name"] if org else None,
        },
        "subscription": {
            "status": sub["status"] if sub else None,
            "trial_ends_at": sub["trial_ends_at"].isoformat() if sub and sub["trial_ends_at"] else None,
            "current_period_end": sub["current_period_end"].isoformat() if sub and sub["current_period_end"] else None,
            "seller_count": seller_count,
            "seller_limit": sub["seller_limit"] if sub else 5,
            "has_stripe": bool(sub and sub["stripe_customer_id"]),
        },
    }


@router.put("/account")
async def update_account(body: AccountUpdate, user: CurrentUser = Depends(require_org_admin)):
    if body.user_name is not None:
        await db.execute(
            "UPDATE users SET name = $1, updated_at = now() WHERE id = $2",
            [body.user_name.strip(), user.user_id],
        )

    if body.job_title is not None:
        await db.execute(
            "UPDATE users SET job_title = $1, updated_at = now() WHERE id = $2",
            [body.job_title.strip(), user.user_id],
        )

    if body.org_name is not None:
        await db.execute(
            "UPDATE organizations SET name = $1, updated_at = now() WHERE id = $2",
            [body.org_name.strip(), user.org_id],
        )

    return {"message": "Conta atualizada"}
