"""
CommercePulse++ Event Collector
Lightweight Cloud Run service that receives browser/app events
and publishes them to Pub/Sub for Dataflow streaming processing.

POST /collect/{seller_id}  — accepts a single event payload
POST /collect/batch        — accepts an array of events (up to 100)
"""
import hashlib
import hmac
import json
import logging
import os
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException, Path, Request, status
from google.cloud import pubsub_v1

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CommercePulse Event Collector", docs_url=None, redoc_url=None)

GCP_PROJECT   = os.getenv("GCP_PROJECT", "commercepulse-prod")
PUBSUB_TOPIC  = os.getenv("PUBSUB_TOPIC", "commercepulse-events")
SIGNING_SECRET = os.getenv("CP_SIGNING_SECRET", "dev-secret")  # per-seller HMAC secret

publisher    = pubsub_v1.PublisherClient()
topic_path   = publisher.topic_path(GCP_PROJECT, PUBSUB_TOPIC)


def _verify_signature(seller_id: str, body: bytes, signature: str | None) -> bool:
    """HMAC-SHA256 verification using per-seller signing key."""
    if not signature:
        return os.getenv("CP_DEV_MODE", "false") == "true"
    expected = hmac.new(
        f"{SIGNING_SECRET}:{seller_id}".encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _publish(events: list[dict], seller_id: str) -> int:
    futures = []
    for event in events:
        event.setdefault("event_id", str(uuid.uuid4()))
        event["seller_id"] = seller_id
        event.setdefault("ingest_ts", datetime.utcnow().isoformat())

        data = json.dumps(event).encode("utf-8")
        future = publisher.publish(
            topic_path,
            data,
            seller_id=seller_id,
            event_type=event.get("event_type", "unknown"),
        )
        futures.append(future)

    for f in futures:
        f.result(timeout=5)

    return len(futures)


@app.post("/collect/{seller_id}", status_code=status.HTTP_202_ACCEPTED)
async def collect_single(
    request:   Request,
    seller_id: str = Path(..., min_length=3, max_length=64),
):
    body = await request.body()
    sig  = request.headers.get("X-CP-Signature")

    if not _verify_signature(seller_id, body, sig):
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="Expected a JSON object")

    published = _publish([event], seller_id)
    return {"accepted": published, "seller_id": seller_id}


@app.post("/collect/batch", status_code=status.HTTP_202_ACCEPTED)
async def collect_batch(
    request: Request,
):
    body = await request.body()

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if not isinstance(payload, dict) or "seller_id" not in payload or "events" not in payload:
        raise HTTPException(status_code=400, detail="Expected {seller_id, events: [...]}")

    seller_id = payload["seller_id"]
    events    = payload["events"]

    if not isinstance(events, list) or len(events) > 100:
        raise HTTPException(status_code=400, detail="events must be an array of up to 100 items")

    sig = request.headers.get("X-CP-Signature")
    if not _verify_signature(seller_id, body, sig):
        raise HTTPException(status_code=403, detail="Invalid signature")

    published = _publish(events, seller_id)
    return {"accepted": published, "seller_id": seller_id}


@app.get("/health")
async def health():
    return {"status": "ok", "topic": topic_path}
