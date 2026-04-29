"""
Gemini AI service — builds seller context from BigQuery data
and calls Vertex AI Gemini API for recommendations and chat.

Replaces LangGraph + Groq (Azure) with Vertex AI Gemini (Google).
Agent schema outputs reused from AZURE/ai_agents/app/agents/schemas.py.
"""
import json
import logging
from typing import AsyncIterator

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig, Part

from app.core.config import settings
from app.clients import bigquery_client as bq

logger = logging.getLogger(__name__)

# Lazy init — called once on first use
_model: GenerativeModel | None = None

def _get_model() -> GenerativeModel:
    global _model
    if _model is None:
        vertexai.init(project=settings.GCP_PROJECT, location=settings.VERTEX_LOCATION)
        _model = GenerativeModel(settings.GEMINI_MODEL)
    return _model


# ── Context builder ────────────────────────────────────────────

async def build_seller_context(seller_id: str) -> dict:
    """
    Pull key metrics from BigQuery gold tables and format into
    a structured dict for Gemini prompt grounding.
    """
    kpis_sql = f"""
        SELECT total_net_revenue, total_orders, cancellation_rate_pct,
               rto_rate_pct, avg_roas, low_stock_count, stockout_count
        FROM `{settings.BQ_DATASET_GOLD}.seller_dashboard_kpis`
        WHERE seller_id = @seller_id LIMIT 1
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
          AND metric_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
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

    params = {"seller_id": seller_id}

    kpis, funnel_top, risks = await asyncio.gather(
        bq.query_single(kpis_sql, params),
        bq.query(funnel_sql, params),
        bq.query(risk_sql, params),
    )

    return {
        "seller_id": seller_id,
        "kpis": kpis or {},
        "top_converting_products": funnel_top,
        "inventory_risks": risks,
    }


# ── Recommendation brief ───────────────────────────────────────

RECOMMENDATION_PROMPT = """
You are a senior e-commerce analytics consultant advising Indian marketplace sellers (Flipkart, Amazon India, Meesho, Myntra).

Seller: {seller_id}
Analysis Period: Last 30 days

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
    """
    Build seller context from BigQuery and generate Gemini recommendation brief.
    Returns parsed JSON matching ExecutiveActionPlan schema.
    """
    import asyncio
    ctx = await build_seller_context(seller_id)
    kpis = ctx.get("kpis") or {}

    funnel_lines = "\n".join(
        f"  - {r.get('sku')} ({r.get('marketplace')}): conv={r.get('conv_pct')}%, ROAS={r.get('roas')}x"
        for r in ctx.get("top_converting_products", [])
    ) or "  No data available"

    risk_lines = "\n".join(
        f"  - {r.get('sku')} ({r.get('marketplace')}): {r.get('available_stock')} units, "
        f"{r.get('days_until_stockout'):.0f} days left [{r.get('risk_level')}]"
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

    model = _get_model()
    response = model.generate_content(
        prompt,
        generation_config=GenerationConfig(
            temperature=0.3,
            response_mime_type="application/json",
        ),
    )

    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        return {"raw_response": response.text, "error": "Could not parse as JSON"}


# ── Streaming chat ─────────────────────────────────────────────

CHAT_SYSTEM_PROMPT = """
You are CommercePulse AI, an expert e-commerce analytics assistant for Indian marketplace sellers.
You have access to the seller's real-time data. Answer questions with specific numbers from their data.
When you don't have specific data, say so clearly and give general best practices.
Keep answers concise and actionable. Always think in terms of revenue impact in INR.
"""


async def stream_chat(
    seller_id: str,
    message: str,
    history: list[dict] | None = None,
) -> AsyncIterator[str]:
    """
    Stream a Gemini chat response grounded in seller data.
    Yields text chunks as they arrive for SSE streaming.
    """
    ctx = await build_seller_context(seller_id)

    grounding = f"""
Seller context for {seller_id}:
Revenue: ₹{float(ctx.get('kpis', {}).get('total_net_revenue') or 0):,.0f} (last 30d)
Orders: {int(ctx.get('kpis', {}).get('total_orders') or 0):,}
ROAS: {float(ctx.get('kpis', {}).get('avg_roas') or 0):.2f}x
Critical inventory alerts: {len([r for r in ctx.get('inventory_risks', []) if r.get('risk_level') == 'CRITICAL'])}

User question: {message}
"""

    model = _get_model()
    stream = model.generate_content(
        [CHAT_SYSTEM_PROMPT, grounding],
        generation_config=GenerationConfig(temperature=0.5),
        stream=True,
    )

    for chunk in stream:
        if chunk.text:
            yield chunk.text


async def generate_product_insights(seller_id: str, recs: list[dict]) -> dict:
    """
    Batch Gemini call: generates per-product natural language insights.
    Returns dict keyed by product_id. Fails silently if Gemini unavailable.
    """
    if not recs:
        return {}

    products_summary = "\n".join(
        f"- {r.get('product_id')} | {r.get('product_name')} | price:₹{r.get('price',0)} "
        f"| stock:{r.get('current_stock',0)} | views:{r.get('views',0)} "
        f"| cart:{r.get('cart_adds',0)} | sold:{r.get('purchases',0)} "
        f"| demand_score:{r.get('demand_score',0)} | label:{r.get('recommendation','')}"
        for r in recs
    )

    prompt = f"""You are an e-commerce analytics AI for Indian marketplace sellers (Flipkart, Amazon India, Meesho).

Seller: {seller_id}
Product data (last 7 days of real storefront activity):
{products_summary}

For EVERY product above, generate a specific data-driven recommendation. Cite exact numbers and ₹ values.

Return ONLY a valid JSON array with exactly {len(recs)} entries, no other text:
[
  {{
    "product_id": "P001",
    "insight": "Restock 8 units now — selling 3 units/day at ₹2,999 and stock hits zero in 2 days, costing ₹72K in lost revenue this month.",
    "urgency": "CRITICAL",
    "monthly_revenue_impact": 72000
  }}
]

Rules:
- urgency: CRITICAL (stock=0 or demand high + low stock) | HIGH (restock soon) | MEDIUM (pricing action) | LOW (maintain or skip)
- insight: 1 sentence, under 25 words, cite actual numbers from the data
- monthly_revenue_impact: realistic INR estimate of monthly impact if action taken
- Include all {len(recs)} products
"""

    try:
        model = _get_model()
        response = model.generate_content(
            prompt,
            generation_config=GenerationConfig(
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )
        insights_list = json.loads(response.text)
        return {item["product_id"]: item for item in insights_list if "product_id" in item}
    except Exception as e:
        logger.warning("Gemini product insights failed: %s", e)
        return {}


import asyncio  # noqa: E402 — needed for gather in build_seller_context
