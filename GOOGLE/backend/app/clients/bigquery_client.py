"""
Async BigQuery client wrapper.
Uses asyncio.to_thread to avoid blocking the event loop.
"""
import asyncio
import logging
from typing import Any

from google.cloud import bigquery

from app.core.config import settings

logger = logging.getLogger(__name__)

_bq_client: bigquery.Client | None = None


def _get_client() -> bigquery.Client:
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client(project=settings.GCP_PROJECT)
    return _bq_client


def _run_query_sync(sql: str, params: dict) -> list[dict]:
    client = _get_client()

    # Build query parameters
    bq_params = []
    for k, v in params.items():
        if isinstance(v, int):
            bq_params.append(bigquery.ScalarQueryParameter(k, "INT64", v))
        elif isinstance(v, float):
            bq_params.append(bigquery.ScalarQueryParameter(k, "FLOAT64", v))
        else:
            bq_params.append(bigquery.ScalarQueryParameter(k, "STRING", str(v)))

    job_config = bigquery.QueryJobConfig(query_parameters=bq_params)
    job = client.query(sql, job_config=job_config)
    rows = job.result()
    return [dict(row) for row in rows]


async def query(sql: str, params: dict | None = None) -> list[dict]:
    """Execute a BigQuery SQL query asynchronously."""
    try:
        return await asyncio.to_thread(_run_query_sync, sql, params or {})
    except Exception as e:
        logger.error("BigQuery query failed: %s | SQL: %s", e, sql[:200])
        raise


async def query_single(sql: str, params: dict | None = None) -> dict | None:
    """Execute a query and return the first row, or None."""
    rows = await query(sql, params)
    return rows[0] if rows else None
