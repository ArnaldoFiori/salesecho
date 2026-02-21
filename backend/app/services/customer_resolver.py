from app import database as db


async def resolve_customer(org_id: str, customer_name_raw: str) -> str:
    """Resolve ou cria customer. Retorna customer_id."""
    name_normalized = customer_name_raw.strip().lower()

    row = await db.fetchone(
        "SELECT id FROM customers WHERE org_id = $1 AND name_normalized = $2",
        [org_id, name_normalized],
    )
    if row:
        return str(row["id"])

    row = await db.fetchone(
        """INSERT INTO customers (org_id, name, name_normalized)
        VALUES ($1, $2, $3)
        ON CONFLICT (org_id, name_normalized) DO UPDATE SET name = EXCLUDED.name
        RETURNING id""",
        [org_id, customer_name_raw.strip(), name_normalized],
    )
    return str(row["id"])
