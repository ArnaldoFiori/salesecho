from fastapi import Depends, HTTPException, Request
import jwt
from jwt import PyJWKClient
from app.config import settings
from app import database as db

jwks_client = PyJWKClient(f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json")

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
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(token, signing_key.key, algorithms=["ES256"], audience="authenticated")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(401, f"Invalid token: {str(e)}")

async def get_current_user(request: Request) -> CurrentUser:
    token = _extract_token(request)
    payload = _decode_jwt(token)
    auth_user_id = payload.get("sub")
    if not auth_user_id:
        raise HTTPException(401, "Invalid token: no sub")
    user = await db.fetchone(
        "SELECT id, auth_user_id, org_id, role::text, name, email FROM users WHERE auth_user_id = $1",
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
