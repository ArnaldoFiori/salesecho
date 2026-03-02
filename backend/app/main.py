import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from app.config import settings
from app.middleware import setup_middleware
from app import database as db
from app.routers.webhook_telegram import router as telegram_router
from app.routers.stats import router as stats_router
from app.routers.recordings import router as recordings_router
from app.routers.sellers import router as sellers_router
from app.routers.account import router as account_router
from app.routers.admin import router as admin_router
from app.routers.billing import router as billing_router

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","module":"%(module)s","message":"%(message)s"}',
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up")
    yield
    await db.close_pool()

app = FastAPI(
    title="SalesEcho API",
    version="0.1.0",
    lifespan=lifespan,
)

setup_middleware(app)

app.include_router(telegram_router)
app.include_router(stats_router)
app.include_router(recordings_router)
app.include_router(sellers_router)
app.include_router(account_router)
app.include_router(admin_router)
app.include_router(billing_router)

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
