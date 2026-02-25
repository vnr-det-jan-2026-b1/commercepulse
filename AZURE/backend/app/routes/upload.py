"""Upload routes — POST /upload/{domain}"""
from datetime import date
from typing import Optional
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import rate_limiter, enforce_seller_scope
from app.services import ingestion

router = APIRouter(
    dependencies=[Depends(rate_limiter(max_requests=60, window_seconds=60))],
)
logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/octet-stream",
}

def _validate_excel(file: UploadFile):
    if file.content_type not in ALLOWED_CONTENT_TYPES and not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx / .xls files are accepted.")


def _trigger_embed(seller_id: str, snap_date: date):
    """
    Fire-and-forget: enqueue the Celery embedding task.
    Gracefully degrades if Redis is unavailable (logs warning, doesn't crash the upload).
    """
    try:
        from app.services.tasks import auto_embed
        res = auto_embed.delay(seller_id, str(snap_date))
        logger.info(
            "[Upload] Enqueued auto_embed task_id=%s seller_id=%s date=%s",
            res.id,
            seller_id,
            snap_date,
        )
    except Exception as e:
        logger.warning("[Upload] Could not enqueue embed task (Redis unavailable?): %s", e)


# ── Orders ─────────────────────────────────────────────────────
@router.post("/orders", summary="Upload Orders Excel sheet")
async def upload_orders(
    seller_id:     str           = Form(..., description="Seller UUID"),
    snapshot_date: Optional[str] = Form(None, description="Snapshot date YYYY-MM-DD (default: today)"),
    file:          UploadFile    = File(...),
    db:            AsyncSession  = Depends(get_db),
    _scope:        str           = Depends(enforce_seller_scope),
):
    _validate_excel(file)
    snap_date = date.fromisoformat(snapshot_date) if snapshot_date else date.today()
    content = await file.read()
    result  = await ingestion.ingest_orders(db, content, seller_id, snap_date)
    _trigger_embed(seller_id, snap_date)   # ← async background embedding
    return {"status": "ok", **result, "snapshot_date": str(snap_date), "embedding": "queued"}


# ── Inventory ──────────────────────────────────────────────────
@router.post("/inventory", summary="Upload Inventory Excel sheet")
async def upload_inventory(
    seller_id:     str           = Form(...),
    snapshot_date: Optional[str] = Form(None),
    file:          UploadFile    = File(...),
    db:            AsyncSession  = Depends(get_db),
    _scope:        str           = Depends(enforce_seller_scope),
):
    _validate_excel(file)
    snap_date = date.fromisoformat(snapshot_date) if snapshot_date else date.today()
    content = await file.read()
    result  = await ingestion.ingest_inventory(db, content, seller_id, snap_date)
    _trigger_embed(seller_id, snap_date)   # ← async background embedding
    return {"status": "ok", **result, "snapshot_date": str(snap_date), "embedding": "queued"}


# ── Pricing ────────────────────────────────────────────────────
@router.post("/pricing", summary="Upload Pricing Excel sheet")
async def upload_pricing(
    seller_id:     str           = Form(...),
    snapshot_date: Optional[str] = Form(None),
    file:          UploadFile    = File(...),
    db:            AsyncSession  = Depends(get_db),
    _scope:        str           = Depends(enforce_seller_scope),
):
    _validate_excel(file)
    snap_date = date.fromisoformat(snapshot_date) if snapshot_date else date.today()
    content = await file.read()
    result  = await ingestion.ingest_pricing(db, content, seller_id, snap_date)
    _trigger_embed(seller_id, snap_date)   # ← async background embedding
    return {"status": "ok", **result, "snapshot_date": str(snap_date), "embedding": "queued"}


# ── Traffic & Ads ──────────────────────────────────────────────
@router.post("/traffic", summary="Upload Traffic & Ads Excel sheet")
async def upload_traffic(
    seller_id:     str           = Form(...),
    snapshot_date: Optional[str] = Form(None),
    file:          UploadFile    = File(...),
    db:            AsyncSession  = Depends(get_db),
    _scope:        str           = Depends(enforce_seller_scope),
):
    _validate_excel(file)
    snap_date = date.fromisoformat(snapshot_date) if snapshot_date else date.today()
    content = await file.read()
    result  = await ingestion.ingest_traffic(db, content, seller_id, snap_date)
    _trigger_embed(seller_id, snap_date)   # ← async background embedding
    return {"status": "ok", **result, "snapshot_date": str(snap_date), "embedding": "queued"}


# ── Logistics ──────────────────────────────────────────────────
@router.post("/logistics", summary="Upload Logistics Excel sheet")
async def upload_logistics(
    seller_id:     str           = Form(...),
    snapshot_date: Optional[str] = Form(None),
    file:          UploadFile    = File(...),
    db:            AsyncSession  = Depends(get_db),
    _scope:        str           = Depends(enforce_seller_scope),
):
    _validate_excel(file)
    snap_date = date.fromisoformat(snapshot_date) if snapshot_date else date.today()
    content = await file.read()
    result  = await ingestion.ingest_logistics(db, content, seller_id, snap_date)
    _trigger_embed(seller_id, snap_date)   # ← async background embedding
    return {"status": "ok", **result, "snapshot_date": str(snap_date), "embedding": "queued"}


# ── Full multi-sheet upload ────────────────────────────────────
@router.post("/full", summary="Upload a single Excel file with multiple sheets (one per domain)")
async def upload_full(
    seller_id:     str           = Form(...),
    snapshot_date: Optional[str] = Form(None),
    file:          UploadFile    = File(...),
    db:            AsyncSession  = Depends(get_db),
    _scope:        str           = Depends(enforce_seller_scope),
):
    """
    Expects an Excel workbook with up to 5 sheets named:
    Orders, Inventory, Pricing, Traffic, Logistics (case-insensitive).
    Embedding is triggered once after all sheets are processed.
    """
    import io
    import pandas as pd

    _validate_excel(file)
    snap_date = date.fromisoformat(snapshot_date) if snapshot_date else date.today()
    content = await file.read()

    xl = pd.ExcelFile(io.BytesIO(content), engine="openpyxl")
    sheet_names_lower = {s.strip().lower(): s for s in xl.sheet_names}

    results = {}
    DOMAIN_MAP = {
        "orders":    ingestion.ingest_orders,
        "inventory": ingestion.ingest_inventory,
        "pricing":   ingestion.ingest_pricing,
        "traffic":   ingestion.ingest_traffic,
        "logistics": ingestion.ingest_logistics,
    }

    for domain, fn in DOMAIN_MAP.items():
        if domain in sheet_names_lower:
            sheet_df = xl.parse(sheet_names_lower[domain])
            buf = io.BytesIO()
            sheet_df.to_excel(buf, index=False, engine="openpyxl")
            results[domain] = await fn(db, buf.getvalue(), seller_id, snap_date)

    if not results:
        raise HTTPException(400, "No recognizable sheets found. Expected: Orders, Inventory, Pricing, Traffic, Logistics")

    # Trigger one embed job for all domains processed
    _trigger_embed(seller_id, snap_date)

    return {"status": "ok", "results": results, "snapshot_date": str(snap_date), "embedding": "queued"}
