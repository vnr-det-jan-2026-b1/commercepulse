"""
Gemini AI service — builds seller context from BigQuery data
and calls Gemini for recommendations and chat.

Uses google.genai SDK.  Authentication priority:
  1. GEMINI_API_KEY env var  → Gemini Developer API (AI Studio key)
  2. Fallback                → Vertex AI with application default credentials
"""
import asyncio
import json
import logging
from typing import AsyncIterator

from google import genai
from google.genai import types as genai_types

from app.core.config import settings
from app.clients import bigquery_client as bq

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if settings.GEMINI_API_KEY:
            _client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            _client = genai.Client(
                vertexai=True,
                project=settings.GCP_PROJECT,
                location=settings.VERTEX_LOCATION,
            )
    return _client


# ── Context builder ────────────────────────────────────────────

async def build_seller_context(seller_id: str) -> dict:
    # Compute KPIs directly from source tables (not the pre-computed gold table
    # which may be stale or manually zeroed) using a 90-day window so older
    # order data is still included.
    kpis_sql = f"""
        SELECT
          ROUND(SUM(CAST(net_revenue AS FLOAT64)), 2)                         AS total_net_revenue,
          COUNT(*)                                                             AS total_orders,
          ROUND(COUNTIF(order_status = 'cancelled') / COUNT(*) * 100, 1)     AS cancellation_rate_pct,
          ROUND(COUNTIF(return_flag) / COUNT(*) * 100, 1)                    AS rto_rate_pct,
          COUNTIF(order_status = 'cancelled')                                 AS cancelled_orders,
          COUNTIF(return_flag)                                                 AS returned_orders
        FROM `{settings.BQ_DATASET_BRONZE}.orders`
        WHERE seller_id = @seller_id
          AND order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    """
    funnel_sql = f"""
        SELECT sku, marketplace,
               SUM(impressions) AS impressions,
               SUM(product_views) AS product_views,
               SUM(add_to_cart) AS add_to_cart,
               SUM(purchases) AS purchases,
               ROUND(AVG(overall_conversion_rate)*100, 2) AS conv_pct,
               ROUND(AVG(roas), 2) AS roas
        FROM `{settings.BQ_DATASET_GOLD}.funnel_metrics`
        WHERE seller_id = @seller_id
          AND metric_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        GROUP BY sku, marketplace
        ORDER BY conv_pct DESC
        LIMIT 5
    """
    risk_sql = f"""
        SELECT sku, marketplace, available_stock, days_until_stockout,
               risk_level, recommended_reorder_qty
        FROM `{settings.BQ_DATASET_GOLD}.inventory_risk_scores`
        WHERE seller_id = @seller_id
          AND risk_level IN ('CRITICAL', 'HIGH')
        ORDER BY days_until_stockout ASC
        LIMIT 5
    """
    stock_sql = f"""
        SELECT
          COUNTIF(GREATEST(c.initial_stock - COALESCE(sold.qty,0), 0) = 0)      AS stockout_count,
          COUNTIF(GREATEST(c.initial_stock - COALESCE(sold.qty,0), 0) BETWEEN 1 AND 3) AS low_stock_count
        FROM `{settings.BQ_DATASET_RAW}.product_catalog` c
        LEFT JOIN (
          SELECT product_id, SUM(quantity) AS qty
          FROM `{settings.BQ_DATASET_RAW}.storefront_events`
          WHERE event_type = 'purchase' AND seller_id = @seller_id
          GROUP BY product_id
        ) sold ON sold.product_id = c.product_id
        WHERE c.seller_id = @seller_id
    """
    params = {"seller_id": seller_id}
    kpis, funnel_top, risks, stock_summary = await asyncio.gather(
        bq.query_single(kpis_sql, params),
        bq.query(funnel_sql, params),
        bq.query(risk_sql, params),
        bq.query_single(stock_sql, params),
    )
    kpis = kpis or {}
    stock_summary = stock_summary or {}
    kpis["low_stock_count"] = stock_summary.get("low_stock_count", 0)
    kpis["stockout_count"] = stock_summary.get("stockout_count", 0)
    return {
        "seller_id": seller_id,
        "kpis": kpis,
        "top_converting_products": funnel_top,
        "inventory_risks": risks,
    }


# ── Recommendation brief ───────────────────────────────────────

RECOMMENDATION_PROMPT = """
You are a senior e-commerce analytics consultant advising Indian marketplace sellers.

Seller: {seller_id}
Analysis Period: Last 90 days

KPI Summary:
- Total Net Revenue: ₹{total_net_revenue:,.0f}
- Total Orders: {total_orders:,}
- Cancellation Rate: {cancellation_rate_pct:.1f}%
- RTO Rate: {rto_rate_pct:.1f}%
- Average ROAS: {avg_roas:.2f}x
- Low Stock Products: {low_stock_count}
- Stockout Products: {stockout_count}

Top Converting Products (last 7 days):
{funnel_data}

Inventory Risks:
{risk_data}

Generate a concise executive intelligence brief:
1. **Primary diagnosis** — What is the #1 problem hurting this seller's revenue? (cite specific numbers)
2. **Top 3 ranked actions** — Each with: action title, expected revenue impact in ₹/month, risk level (Low/Medium/High), difficulty (Low/Medium/High)
3. **One inventory alert** — If CRITICAL risk products exist, name them and estimated revenue at risk
4. **One marketing insight** — Which channel/product needs budget reallocation based on ROAS data

Be direct, specific, and cite the numbers provided. Avoid generic advice.
Output as structured JSON matching this schema:
{{
  "primary_problem_statement": "...",
  "total_revenue_recovery_potential_pct": 0.0,
  "total_financial_recovery_monthly": 0.0,
  "ranked_actions": [
    {{"action_name": "...", "description": "...", "estimated_impact_percentage": 0.0,
      "financial_impact_monthly": 0.0, "is_profit_safe": true,
      "risk_level": "Low|Medium|High", "difficulty": "Low|Medium|High"}}
  ],
  "confidence_score": 0.0
}}
"""


async def generate_recommendations(seller_id: str) -> dict:
    ctx = await build_seller_context(seller_id)
    kpis = ctx.get("kpis") or {}

    funnel_lines = "\n".join(
        f"  - {r.get('sku')} ({r.get('marketplace')}): conv={r.get('conv_pct')}%, ROAS={r.get('roas')}x"
        for r in ctx.get("top_converting_products", [])
    ) or "  No data available"

    risk_lines = "\n".join(
        f"  - {r.get('sku')} ({r.get('marketplace')}): {r.get('available_stock')} units, "
        f"{r.get('days_until_stockout') or 0:.0f} days left [{r.get('risk_level')}]"
        for r in ctx.get("inventory_risks", [])
    ) or "  No critical risks"

    prompt = RECOMMENDATION_PROMPT.format(
        seller_id=seller_id,
        total_net_revenue=float(kpis.get("total_net_revenue") or 0),
        total_orders=int(kpis.get("total_orders") or 0),
        cancellation_rate_pct=float(kpis.get("cancellation_rate_pct") or 0),
        rto_rate_pct=float(kpis.get("rto_rate_pct") or 0),
        avg_roas=float(kpis.get("avg_roas") or 0),
        low_stock_count=int(kpis.get("low_stock_count") or 0),
        stockout_count=int(kpis.get("stockout_count") or 0),
        funnel_data=funnel_lines,
        risk_data=risk_lines,
    )

    client = _get_client()
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            temperature=0.3,
            response_mime_type="application/json",
        ),
    )

    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        return {"raw_response": response.text, "error": "Could not parse as JSON"}


# ── Streaming chat ─────────────────────────────────────────────

CHAT_SYSTEM_PROMPT = (
    "You are CommercePulse AI, an expert e-commerce analytics assistant for Indian "
    "marketplace sellers. Answer questions with specific numbers from their data. "
    "Keep answers concise and actionable. Always think in terms of revenue impact in INR."
)


async def stream_chat(
    seller_id: str,
    message: str,
    history: list[dict] | None = None,
) -> AsyncIterator[str]:
    ctx = await build_seller_context(seller_id)
    kpis = ctx.get("kpis") or {}

    grounding = (
        f"Seller context for {seller_id}:\n"
        f"Revenue: ₹{float(kpis.get('total_net_revenue') or 0):,.0f} (last 30d)\n"
        f"Orders: {int(kpis.get('total_orders') or 0):,}\n"
        f"ROAS: {float(kpis.get('avg_roas') or 0):.2f}x\n"
        f"Critical inventory alerts: {len([r for r in ctx.get('inventory_risks', []) if r.get('risk_level') == 'CRITICAL'])}\n\n"
        f"User question: {message}"
    )

    client = _get_client()

    def _stream():
        for chunk in client.models.generate_content_stream(
            model=settings.GEMINI_MODEL,
            contents=[CHAT_SYSTEM_PROMPT, grounding],
            config=genai_types.GenerateContentConfig(temperature=0.5),
        ):
            if chunk.text:
                yield chunk.text

    for text in await asyncio.to_thread(lambda: list(_stream())):
        yield text


# ── Per-product insights ───────────────────────────────────────

async def generate_product_insights(seller_id: str, recs: list[dict]) -> dict:
    if not recs:
        return {}

    products_summary = "\n".join(
        f"- {r.get('product_id')} | {r.get('product_name')} | price:₹{r.get('price',0)} "
        f"| stock:{r.get('current_stock',0)} | views:{r.get('views',0)} "
        f"| cart:{r.get('cart_adds',0)} | sold:{r.get('purchases',0)} "
        f"| demand_score:{r.get('demand_score',0)} | label:{r.get('recommendation','')}"
        for r in recs
    )

    prompt = f"""You are an e-commerce analytics AI for Indian marketplace sellers.

Seller: {seller_id}
Product data (last 7 days):
{products_summary}

For EVERY product, generate a specific data-driven recommendation. Cite exact numbers and ₹ values.
Return ONLY a valid JSON array with exactly {len(recs)} entries:
[
  {{
    "product_id": "P001",
    "insight": "1-sentence insight citing actual numbers",
    "urgency": "CRITICAL|HIGH|MEDIUM|LOW",
    "monthly_revenue_impact": 0
  }}
]
Include all {len(recs)} products."""

    try:
        client = _get_client()
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )
        insights_list = json.loads(response.text)
        return {item["product_id"]: item for item in insights_list if "product_id" in item}
    except Exception as e:
        logger.warning("Gemini product insights failed: %s", e)
        return {}
