"""
app/tasks/embed.py
Celery tasks for background embedding.

Tasks:
  auto_embed         — triggered after each Excel upload (per seller, per date)
  nightly_embed_all  — Celery Beat scheduled task, runs daily at 2 AM IST
  embed_single_product — embeds a single product summary (used by /ai/embed/product)
"""
import asyncio
import logging
from datetime import date, timedelta

from celery import shared_task

logger = logging.getLogger(__name__)


# ── Core async embedding logic ─────────────────────────────────
async def _run_embed(seller_id: str, snap_date_str: str) -> int:
    """
    Fetch product snapshot for seller + date, batch-encode summaries,
    bulk-upsert into Supabase product_embeddings.
    Returns number of products embedded.
    """
    from sqlalchemy import text
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from app.db.session import AsyncSessionLocal
    from app.models.models import ProductEmbedding
    from app.services.embeddings import embed_batch

    snap_date = date.fromisoformat(snap_date_str)

    async with AsyncSessionLocal() as db:
        sql = text("""
            SELECT
                p.product_id, p.sku, p.product_name, p.category,
                i.marketplace,
                i.available_stock, i.reorder_threshold,
                pr.selling_price, pr.net_margin, pr.margin_pct,
                t.impressions, t.clicks, t.orders AS ad_orders, t.roas
            FROM products p
            LEFT JOIN inventory_snapshots i
                ON i.product_id = p.product_id AND i.seller_id = :sid
               AND i.snapshot_date = :d
            LEFT JOIN pricing_snapshots pr
                ON pr.product_id = p.product_id AND pr.seller_id = :sid
               AND pr.snapshot_date = :d
            LEFT JOIN traffic_metrics t
                ON t.product_id = p.product_id AND t.seller_id = :sid
               AND t.metric_date = :d
            WHERE p.seller_id = :sid
        """)
        result = await db.execute(sql, {"sid": seller_id, "d": snap_date})
        rows = result.mappings().all()

        if not rows:
            logger.warning("[Embed] No products for seller=%s date=%s", seller_id, snap_date)
            return 0

        # Build summary strings
        summaries = [
            (
                f"Product: {r['product_name']} (SKU: {r['sku']}, Category: {r['category']}, "
                f"Marketplace: {r['marketplace'] or 'N/A'}). "
                f"Stock: {r['available_stock'] or 'N/A'} units "
                f"(threshold: {r['reorder_threshold'] or 10}). "
                f"Price: Rs.{r['selling_price'] or 'N/A'}, "
                f"Margin: {r['margin_pct'] or 'N/A'}%. "
                f"Traffic: {r['impressions'] or 0} impressions, "
                f"{r['clicks'] or 0} clicks, {r['ad_orders'] or 0} ad orders, "
                f"ROAS: {r['roas'] or 0}."
            )
            for r in rows
        ]
        metas = [
            {
                "available_stock": r["available_stock"],
                "selling_price":   float(r["selling_price"]) if r["selling_price"] else None,
                "margin_pct":      float(r["margin_pct"]) if r["margin_pct"] else None,
                "roas":            float(r["roas"]) if r["roas"] else None,
            }
            for r in rows
        ]

        # ONE batch model call for all products
        vectors = await embed_batch(summaries)

        # Bulk upsert into Supabase pgvector
        ins = pg_insert(ProductEmbedding).values([
            {
                "seller_id":    seller_id,
                "product_id":   str(rows[i]["product_id"]),
                "embed_date":   snap_date,
                "embed_type":   "daily_snapshot",
                "summary_text": summaries[i],
                "embedding":    vectors[i],
                "meta":         metas[i],
            }
            for i in range(len(rows))
        ])
        stmt = ins.on_conflict_do_update(
            index_elements=["seller_id", "product_id", "embed_date", "embed_type"],
            set_={
                "summary_text": ins.excluded.summary_text,
                "embedding":    ins.excluded.embedding,
                "metadata":     ins.excluded.metadata,  # DB column name (not ORM attr 'meta')
            },
        )
        await db.execute(stmt)
        await db.commit()

        logger.info("[Embed] seller=%s date=%s embedded=%d", seller_id, snap_date, len(rows))
        return len(rows)


# ── Task 1: Per-upload trigger ─────────────────────────────────
@shared_task(
    name="app.services.tasks.auto_embed",
    bind=True,
    max_retries=3,
    default_retry_delay=30,   # Retry after 30s on failure
    queue="embed",
)
def auto_embed(self, seller_id: str, snap_date: str):
    """
    Triggered automatically after every Excel upload.
    Embeds all products for the given seller and date.

    Usage from FastAPI:
        from app.tasks.embed import auto_embed
        auto_embed.delay(seller_id, snap_date)
    """
    try:
        logger.info("[Celery] auto_embed started seller=%s date=%s", seller_id, snap_date)
        count = asyncio.run(_run_embed(seller_id, snap_date))
        logger.info("[Celery] auto_embed done embedded=%d", count)
        return {"status": "ok", "embedded": count, "seller_id": seller_id, "date": snap_date}
    except Exception as exc:
        logger.error("[Celery] auto_embed error: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


# ── Task 2: Single product embed (for /ai/embed/product) ───────
@shared_task(
    name="app.services.tasks.embed_single_product",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="embed",
)
def embed_single_product(self, seller_id: str, product_id: str, summary: str, embed_date: str | None = None, embed_type: str = "daily_snapshot"):
    """
    Embed a single product summary.

    Used by /ai/embed/product to offload embedding work to Celery.
    """
    try:
        from datetime import date as _date

        from app.db.session import AsyncSessionLocal
        from app.services.embeddings import embedding_service

        async def _run():
            d = _date.fromisoformat(embed_date) if embed_date else _date.today()
            async with AsyncSessionLocal() as db:
                await embedding_service.upsert_product_embedding(
                    db,
                    seller_id=seller_id,
                    product_id=product_id,
                    summary_text=summary,
                    embed_date=d,
                    embed_type=embed_type,
                )
            return {"status": "ok", "embedded": True, "product_id": product_id, "date": str(d)}

        result = asyncio.run(_run())
        logger.info("[Celery] embed_single_product seller=%s product=%s date=%s", seller_id, product_id, result["date"])
        return result
    except Exception as exc:
        logger.error("[Celery] embed_single_product error: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


# ── Task 3: Nightly batch for ALL sellers ─────────────────────
@shared_task(
    name="app.services.tasks.nightly_embed_all",
    queue="embed",
)
def nightly_embed_all():
    """
    Scheduled by Celery Beat at 2:00 AM IST daily.
    Re-embeds yesterday's snapshot for every seller in the database.
    This ensures the AI memory layer is always up-to-date.
    """
    async def _run():
        from sqlalchemy import text
        from app.db.session import AsyncSessionLocal

        yesterday = str(date.today() - timedelta(days=1))

        async with AsyncSessionLocal() as db:
            result = await db.execute(text("SELECT seller_id FROM sellers"))
            seller_ids = [str(row.seller_id) for row in result.fetchall()]

        logger.info("[Celery] nightly_embed_all: %d sellers for date=%s", len(seller_ids), yesterday)
        results = []
        for sid in seller_ids:
            try:
                count = await _run_embed(sid, yesterday)
                results.append({"seller_id": sid, "embedded": count})
            except Exception as e:
                logger.error("[Celery] nightly embed failed seller=%s: %s", sid, e)
                results.append({"seller_id": sid, "error": str(e)})
        return results

    return asyncio.run(_run())
