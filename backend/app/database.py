import asyncio
import logging
import asyncpg
from app.config import settings

logger = logging.getLogger(__name__)
pool: asyncpg.Pool | None = None

async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        for attempt in range(3):
            try:
                pool = await asyncpg.create_pool(
                    settings.DATABASE_URL,
                    min_size=1,
                    max_size=10,
                    statement_cache_size=0,
                    command_timeout=30,
                    timeout=30,
                )
                logger.info("Database pool created")
                return pool
            except Exception as e:
                logger.warning(f"DB connection attempt {attempt+1}/3 failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(3)
                else:
                    raise
    return pool

async def close_pool():
    global pool
    if pool:
        await pool.close()
        pool = None

async def fetchone(query: str, params: list | None = None) -> dict | None:
    p = await get_pool()
    row = await p.fetchrow(query, *(params or []))
    return dict(row) if row else None

async def fetchall(query: str, params: list | None = None) -> list[dict]:
    p = await get_pool()
    rows = await p.fetch(query, *(params or []))
    return [dict(r) for r in rows]

async def fetchval(query: str, params: list | None = None):
    p = await get_pool()
    return await p.fetchval(query, *(params or []))

async def execute(query: str, params: list | None = None):
    p = await get_pool()
    return await p.execute(query, *(params or []))
