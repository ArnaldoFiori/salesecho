import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from app.config import settings
from app.middleware import setup_middleware
from app import database as db
from app.routers.webhook_telegram import router as telegram_router

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","module":"%(module)s","message":"%(message)s"}',
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.get_pool()
    yield
    await db.close_pool()


app = FastAPI(
    title="SalesEcho API",
    version="0.1.0",
    lifespan=lifespan,
)

setup_middleware(app)
app.include_router(telegram_router)


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/health/deep")
async def health_deep():
    checks = {}

    try:
        result = await db.fetchval("SELECT 1")
        checks["database"] = "ok" if result == 1 else "error"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:100]}"

    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
