import asyncpg
from app.config import settings

pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=2,
            max_size=10,
        )
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
