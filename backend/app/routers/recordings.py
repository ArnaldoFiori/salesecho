import io
import math
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from app.auth import get_current_user, CurrentUser, require_org_admin
from app import database as db

router = APIRouter(prefix="/api", tags=["recordings"])

ALLOWED_SORT = {"created_at", "seller_name", "customer_name", "audio_duration_sec", "status"}


def _build_query(org_id: str, seller_id: str | None, customer_id: str | None,
                 status: str | None, date_from: date | None, date_to: date | None,
                 sort_by: str, sort_order: str):
    base = """
        SELECT r.id, r.created_at, u.name as seller_name,
               COALESCE(c.name, r.customer_name_raw) as customer_name,
               r.product_raw as product, r.audio_duration_sec,
               r.status::text as status
        FROM recordings r
        LEFT JOIN users u ON r.seller_id = u.id
        LEFT JOIN customers c ON r.customer_id = c.id
        WHERE r.org_id = $1
    """
    params = [org_id]
    idx = 2

    if seller_id:
        base += f" AND r.seller_id = ${idx}"
        params.append(seller_id)
        idx += 1

    if customer_id:
        base += f" AND r.customer_id = ${idx}"
        params.append(customer_id)
        idx += 1

    if status:
        base += f" AND r.status::text = ${idx}"
        params.append(status)
        idx += 1

    if date_from:
        base += f" AND r.created_at >= ${idx}"
        params.append(date_from)
        idx += 1

    if date_to:
        base += f" AND r.created_at < ${idx} + INTERVAL '1 day'"
        params.append(date_to)
        idx += 1

    col = sort_by if sort_by in ALLOWED_SORT else "created_at"
    direction = "ASC" if sort_order == "asc" else "DESC"
    base += f" ORDER BY {col} {direction}"

    return base, params, idx


@router.get("/recordings")
async def list_recordings(
    user: CurrentUser = Depends(require_org_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    seller_id: str | None = None,
    customer_id: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    base, params, idx = _build_query(
        user.org_id, seller_id, customer_id, status, date_from, date_to, sort_by, sort_order
    )

    # Count
    count_query = f"SELECT COUNT(*) FROM ({base}) sub"
    total = await db.fetchval(count_query, params)

    # Paginate
    offset = (page - 1) * page_size
    paginated = base + f" LIMIT ${idx} OFFSET ${idx + 1}"
    params.extend([page_size, offset])

    rows = await db.fetchall(paginated, params)

    items = []
    for r in rows:
        items.append({
            "id": str(r["id"]),
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "seller_name": r["seller_name"],
            "customer_name": r["customer_name"],
            "product": r["product"],
            "audio_duration_sec": r["audio_duration_sec"],
            "status": r["status"],
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 0,
    }


@router.get("/recordings/export")
async def export_recordings(
    user: CurrentUser = Depends(require_org_admin),
    seller_id: str | None = None,
    customer_id: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    query = """
        SELECT r.created_at, u.name as seller_name,
               COALESCE(c.name, r.customer_name_raw) as customer_name,
               r.product_raw as product, r.audio_duration_sec,
               r.transcript_text, r.summary_text, r.status::text as status
        FROM recordings r
        LEFT JOIN users u ON r.seller_id = u.id
        LEFT JOIN customers c ON r.customer_id = c.id
        WHERE r.org_id = $1
    """
    params = [user.org_id]
    idx = 2

    if seller_id:
        query += f" AND r.seller_id = ${idx}"
        params.append(seller_id)
        idx += 1
    if customer_id:
        query += f" AND r.customer_id = ${idx}"
        params.append(customer_id)
        idx += 1
    if status:
        query += f" AND r.status::text = ${idx}"
        params.append(status)
        idx += 1
    if date_from:
        query += f" AND r.created_at >= ${idx}"
        params.append(date_from)
        idx += 1
    if date_to:
        query += f" AND r.created_at < ${idx} + INTERVAL '1 day'"
        params.append(date_to)
        idx += 1

    query += " ORDER BY r.created_at DESC"
    rows = await db.fetchall(query, params)

    wb = Workbook()
    ws = wb.active
    ws.title = "Recordings"
    ws.append(["Data", "Vendedor", "Cliente", "Produto", "Duração (min)", "Transcrição", "Resumo IA", "Status"])

    for r in rows:
        duration_min = round(r["audio_duration_sec"] / 60, 1) if r["audio_duration_sec"] else 0
        ws.append([
            r["created_at"].strftime("%Y-%m-%d %H:%M") if r["created_at"] else "",
            r["seller_name"] or "",
            r["customer_name"] or "",
            r["product"] or "",
            duration_min,
            r["transcript_text"] or "",
            r["summary_text"] or "",
            r["status"] or "",
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=recordings.xlsx"},
    )


@router.get("/recordings/{recording_id}")
async def get_recording(recording_id: str, user: CurrentUser = Depends(require_org_admin)):
    row = await db.fetchone(
        """SELECT r.id, r.created_at, u.name as seller_name,
                  COALESCE(c.name, r.customer_name_raw) as customer_name,
                  r.product_raw as product, r.audio_duration_sec,
                  r.status::text as status, r.transcript_text,
                  r.summary_text, r.error_message
           FROM recordings r
           LEFT JOIN users u ON r.seller_id = u.id
           LEFT JOIN customers c ON r.customer_id = c.id
           WHERE r.id = $1 AND r.org_id = $2""",
        [recording_id, user.org_id],
    )
    if not row:
        raise HTTPException(404, "Recording not found")

    return {
        "id": str(row["id"]),
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "seller_name": row["seller_name"],
        "customer_name": row["customer_name"],
        "product": row["product"],
        "audio_duration_sec": row["audio_duration_sec"],
        "status": row["status"],
        "transcript_text": row["transcript_text"],
        "summary_text": row["summary_text"],
        "error_message": row["error_message"],
    }
