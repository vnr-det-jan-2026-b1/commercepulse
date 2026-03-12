"""
Public event-tracking endpoint.
Receives storefront events (page_view, product_view, add_to_cart, purchase)
and streams them into BigQuery cp_raw.storefront_events.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.clients import bigquery_client
from app.core.config import settings

router = APIRouter(prefix="/v1/events", tags=["events"])

TABLE_ID = f"{settings.GCP_PROJECT}.{settings.BQ_DATASET_RAW}.storefront_events"


class EventPayload(BaseModel):
    seller_id: str
    session_id: str
    event_type: str          # page_view | product_view | add_to_cart | purchase
    product_id: str = ""
    product_name: str = ""
    price: float = 0.0
    quantity: int = 0
    page_url: str = ""


@router.post("", status_code=202)
async def track_event(payload: EventPayload):
    row = {
        "event_id":     str(uuid.uuid4()),
        "session_id":   payload.session_id,
        "seller_id":    payload.seller_id,
        "event_type":   payload.event_type,
        "product_id":   payload.product_id,
        "product_name": payload.product_name,
        "price":        payload.price,
        "quantity":     payload.quantity,
        "page_url":     payload.page_url,
        "ts":           datetime.now(timezone.utc).isoformat(),
    }
    await bigquery_client.insert_rows(TABLE_ID, [row])
    return {"ok": True}
