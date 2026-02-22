from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from app.auth import CurrentUser, require_org_admin
from app import database as db
from app.services.phone import normalize_phone
from app.services.stripe_sync import sync_seller_quantity

router = APIRouter(prefix="/api", tags=["sellers"])


class SellerCreate(BaseModel):
    name: str
    phone: str

    @field_validator("name")
    @classmethod
    def name_min(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("Nome deve ter pelo menos 3 caracteres")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, v):
        import re
        digits = re.sub(r'\D', '', v)
        if len(digits) < 10 or len(digits) > 13:
            raise ValueError("Telefone inválido")
        return v


class SellerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    is_active: bool | None = None


@router.get("/sellers")
async def list_sellers(user: CurrentUser = Depends(require_org_admin)):
    rows = await db.fetchall(
        """SELECT u.id, u.name, u.phone, u.is_active,
                  u.telegram_chat_id, u.created_at,
                  (SELECT COUNT(*) FROM recordings r
                   WHERE r.seller_id = u.id
                   AND r.created_at >= CURRENT_DATE - INTERVAL '30 days') as recordings_month
           FROM users u
           WHERE u.org_id = $1 AND u.role = 'seller'
           ORDER BY u.name""",
        [user.org_id],
    )

    sub = await db.fetchone(
        "SELECT seller_limit FROM subscriptions WHERE org_id = $1",
        [user.org_id],
    )

    items = []
    for r in rows:
        items.append({
            "id": str(r["id"]),
            "name": r["name"],
            "phone": r["phone"],
            "is_active": r["is_active"],
            "telegram_linked": r["telegram_chat_id"] is not None,
            "recordings_month": r["recordings_month"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        })

    return {
        "items": items,
        "seller_count": len(items),
        "seller_limit": sub["seller_limit"] if sub else 5,
    }


@router.post("/sellers", status_code=201)
async def create_seller(body: SellerCreate, user: CurrentUser = Depends(require_org_admin)):
    # Check limit
    count = await db.fetchval(
        "SELECT COUNT(*) FROM users WHERE org_id = $1 AND role = 'seller'",
        [user.org_id],
    )
    sub = await db.fetchone(
        "SELECT seller_limit FROM subscriptions WHERE org_id = $1",
        [user.org_id],
    )
    limit = sub["seller_limit"] if sub and sub["seller_limit"] else 5
    if count >= limit:
        raise HTTPException(403, f"Limite de {limit} vendedores atingido")

    phone_normalized = normalize_phone(body.phone)

    # Check duplicate phone in org
    existing = await db.fetchone(
        "SELECT id FROM users WHERE org_id = $1 AND phone_normalized = $2 AND role = 'seller'",
        [user.org_id, phone_normalized],
    )
    if existing:
        raise HTTPException(409, "Telefone já cadastrado nesta organização")

    row = await db.fetchone(
        """INSERT INTO users (org_id, name, role, phone, phone_normalized, is_active)
           VALUES ($1, $2, 'seller', $3, $4, true)
           RETURNING id, name, phone, phone_normalized, is_active, telegram_chat_id""",
        [user.org_id, body.name.strip(), body.phone, phone_normalized],
    )

    await sync_seller_quantity(user.org_id)

    return {
        "id": str(row["id"]),
        "name": row["name"],
        "phone": row["phone"],
        "phone_normalized": row["phone_normalized"],
        "is_active": row["is_active"],
        "telegram_linked": row["telegram_chat_id"] is not None,
    }


@router.put("/sellers/{seller_id}")
async def update_seller(seller_id: str, body: SellerUpdate, user: CurrentUser = Depends(require_org_admin)):
    existing = await db.fetchone(
        "SELECT id FROM users WHERE id = $1 AND org_id = $2 AND role = 'seller'",
        [seller_id, user.org_id],
    )
    if not existing:
        raise HTTPException(404, "Seller not found")

    updates = []
    params = []
    idx = 1

    if body.name is not None:
        if len(body.name.strip()) < 3:
            raise HTTPException(400, "Nome deve ter pelo menos 3 caracteres")
        updates.append(f"name = ${idx}")
        params.append(body.name.strip())
        idx += 1

    if body.phone is not None:
        phone_normalized = normalize_phone(body.phone)
        dup = await db.fetchone(
            "SELECT id FROM users WHERE org_id = $1 AND phone_normalized = $2 AND role = 'seller' AND id != $3",
            [user.org_id, phone_normalized, seller_id],
        )
        if dup:
            raise HTTPException(409, "Telefone já cadastrado nesta organização")
        updates.append(f"phone = ${idx}")
        params.append(body.phone)
        idx += 1
        updates.append(f"phone_normalized = ${idx}")
        params.append(phone_normalized)
        idx += 1

    if body.is_active is not None:
        updates.append(f"is_active = ${idx}")
        params.append(body.is_active)
        idx += 1

    if not updates:
        raise HTTPException(400, "Nenhum campo para atualizar")

    updates.append("updated_at = now()")
    query = f"UPDATE users SET {', '.join(updates)} WHERE id = ${idx} AND org_id = ${idx + 1}"
    params.extend([seller_id, user.org_id])

    await db.execute(query, params)
    await sync_seller_quantity(user.org_id)
    return {"message": "Seller atualizado"}


@router.delete("/sellers/{seller_id}/telegram")
async def unlink_telegram(seller_id: str, user: CurrentUser = Depends(require_org_admin)):
    existing = await db.fetchone(
        "SELECT id FROM users WHERE id = $1 AND org_id = $2 AND role = 'seller'",
        [seller_id, user.org_id],
    )
    if not existing:
        raise HTTPException(404, "Seller not found")

    await db.execute(
        "UPDATE users SET telegram_chat_id = NULL, updated_at = now() WHERE id = $1",
        [seller_id],
    )
    return {"message": "Telegram desvinculado. Vendedor precisará re-vincular."}
