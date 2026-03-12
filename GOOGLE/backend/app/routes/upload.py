"""
Upload routes — POST /upload/*
Accepts Excel/CSV file uploads, validates, writes to GCS,
and triggers batch ingestion via Cloud Tasks.
"""
import uuid
import logging
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from google.cloud import storage, tasks_v2
from google.protobuf import duration_pb2
import json

from app.core.security import enforce_seller_scope
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_MIME = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    "application/vnd.ms-excel",   # xls
    "text/csv",
    "application/csv",
}

DOMAINS = Literal["orders", "inventory", "pricing", "traffic", "logistics"]
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _upload_to_gcs(file_bytes: bytes, seller_id: str, domain: str, snapshot_date: str) -> str:
    client  = storage.Client(project=settings.GCP_PROJECT)
    bucket  = client.bucket(settings.GCS_UPLOAD_BUCKET)
    job_id  = str(uuid.uuid4())
    ext     = "xlsx"
    blob_path = f"{seller_id}/{domain}/{snapshot_date}/{job_id}.{ext}"
    blob    = bucket.blob(blob_path)
    blob.upload_from_string(file_bytes, content_type="application/octet-stream")
    return f"gs://{settings.GCS_UPLOAD_BUCKET}/{blob_path}", job_id


def _enqueue_ingestion_task(gcs_uri: str, seller_id: str, domain: str,
                             snapshot_date: str, job_id: str) -> None:
    """Enqueue a Cloud Tasks HTTP task to trigger the Dataflow batch job."""
    client  = tasks_v2.CloudTasksClient()
    project = settings.GCP_PROJECT
    region  = settings.GCP_REGION
    queue   = "commercepulse-batch-ingestion"
    parent  = client.queue_path(project, region, queue)

    payload = {
        "gcs_uri":       gcs_uri,
        "seller_id":     seller_id,
        "domain":        domain,
        "snapshot_date": snapshot_date,
        "job_id":        job_id,
    }

    # The task worker URL is a Cloud Run service that launches the Dataflow job
    task_url = f"https://batch-worker-{project}.{region}.run.app/trigger"

    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.POST,
            url=task_url,
            headers={"Content-Type": "application/json"},
            body=json.dumps(payload).encode(),
            oidc_token=tasks_v2.OidcToken(
                service_account_email=f"sa-cloudrun-api@{project}.iam.gserviceaccount.com"
            ),
        ),
        dispatch_deadline=duration_pb2.Duration(seconds=900),
    )
    client.create_task(parent=parent, task=task)


async def _handle_upload(
    file:          UploadFile,
    seller_id:     str,
    domain:        str,
    snapshot_date: str | None,
) -> dict:
    # Validate MIME type
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {file.content_type}. Use xlsx or csv.",
        )

    file_bytes = await file.read()

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds 50 MB limit.",
        )

    snap_date = snapshot_date or str(date.today())

    gcs_uri, job_id = _upload_to_gcs(file_bytes, seller_id, domain, snap_date)
    _enqueue_ingestion_task(gcs_uri, seller_id, domain, snap_date, job_id)

    logger.info("Uploaded %s for seller %s → %s (job: %s)", domain, seller_id, gcs_uri, job_id)

    return {
        "job_id":        job_id,
        "status":        "queued",
        "domain":        domain,
        "seller_id":     seller_id,
        "gcs_path":      gcs_uri,
        "snapshot_date": snap_date,
        "file_size_kb":  round(len(file_bytes) / 1024, 1),
    }


@router.post("/orders")
async def upload_orders(
    file:          UploadFile  = File(...),
    seller_id:     str         = Form(...),
    snapshot_date: str | None  = Form(None),
    _scope:        str         = Depends(enforce_seller_scope),
):
    return await _handle_upload(file, seller_id, "orders", snapshot_date)


@router.post("/inventory")
async def upload_inventory(
    file:          UploadFile  = File(...),
    seller_id:     str         = Form(...),
    snapshot_date: str | None  = Form(None),
    _scope:        str         = Depends(enforce_seller_scope),
):
    return await _handle_upload(file, seller_id, "inventory", snapshot_date)


@router.post("/pricing")
async def upload_pricing(
    file:          UploadFile  = File(...),
    seller_id:     str         = Form(...),
    snapshot_date: str | None  = Form(None),
    _scope:        str         = Depends(enforce_seller_scope),
):
    return await _handle_upload(file, seller_id, "pricing", snapshot_date)


@router.post("/traffic")
async def upload_traffic(
    file:          UploadFile  = File(...),
    seller_id:     str         = Form(...),
    snapshot_date: str | None  = Form(None),
    _scope:        str         = Depends(enforce_seller_scope),
):
    return await _handle_upload(file, seller_id, "traffic", snapshot_date)


@router.post("/logistics")
async def upload_logistics(
    file:          UploadFile  = File(...),
    seller_id:     str         = Form(...),
    snapshot_date: str | None  = Form(None),
    _scope:        str         = Depends(enforce_seller_scope),
):
    return await _handle_upload(file, seller_id, "logistics", snapshot_date)
