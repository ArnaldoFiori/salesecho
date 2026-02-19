from fastapi import Depends, HTTPException, Request
import jwt
from app.config import settings
from app import database as db


class CurrentUser:
    def __init__(self, user_id: str, auth_user_id: str, org_id: str, role: str, name: str, email: str | None):
        self.user_id = user_id
        self.auth_user_id = auth_user_id
        self.org_id = org_id
        self.role = role
        self.name = name
        self.email = email


def _extract_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    return auth_header[7:]


def _decode_jwt(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


async def get_current_user(request: Request) -> CurrentUser:
    token = _extract_token(request)
    payload = _decode_jwt(token)
    auth_user_id = payload.get("sub")
    if not auth_user_id:
        raise HTTPException(401, "Invalid token: no sub")

    user = await db.fetchone(
        "SELECT id, auth_user_id, org_id, role::text, name, email "
        "FROM users WHERE auth_user_id = $1",
        [auth_user_id],
    )
    if not user:
        raise HTTPException(401, "User not found")

    return CurrentUser(
        user_id=str(user["id"]),
        auth_user_id=str(user["auth_user_id"]),
        org_id=str(user["org_id"]),
        role=user["role"],
        name=user["name"],
        email=user["email"],
    )


async def require_org_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role not in ("org_admin", "system_admin"):
        raise HTTPException(403, "Requires org_admin or system_admin role")
    return user


async def require_system_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != "system_admin":
        raise HTTPException(403, "Requires system_admin role")
    return user
