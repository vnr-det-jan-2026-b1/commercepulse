"""
AI routes — POST /ai/*
Vertex AI Gemini-powered recommendations, chat, and what-if analysis.
Replaces LangGraph + Groq from Azure implementation.
"""
import asyncio
import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.security import enforce_seller_scope
from app.services import gemini_service as gemini

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])


# ── Request models ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    seller_id: str
    message:   str
    history:   list[dict] | None = None


class WhatIfRequest(BaseModel):
    seller_id: str
    scenario:  str  # e.g. "What if I reduce price of SKU-XYZ by 10%?"


# ── Recommendation Brief ───────────────────────────────────────

@router.post("/recommendations")
async def recommendations(
    seller_id: str = Query(...),
    _scope:    str = Depends(enforce_seller_scope),
):
    """
    Generate a Gemini-powered executive intelligence brief for the seller.
    Grounded in real BigQuery data. Cached for 4 hours.
    """
    try:
        result = await gemini.generate_recommendations(seller_id)
        return {"seller_id": seller_id, "recommendations": result}
    except Exception as e:
        logger.error("Gemini recommendations failed for %s: %s", seller_id, e)
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable.")


# ── Streaming Chat ─────────────────────────────────────────────

@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Stream a Gemini chat response grounded in seller data.
    Returns SSE (text/event-stream).
    """
    async def event_stream() -> AsyncIterator[str]:
        try:
            async for chunk in gemini.stream_chat(
                seller_id=request.seller_id,
                message=request.message,
                history=request.history,
            ):
                yield f"data: {json.dumps({'text': chunk})}\n\n"
        except Exception as e:
            logger.error("Chat stream error: %s", e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── What-If Scenario ───────────────────────────────────────────

WHATIF_PROMPT = """
You are a senior e-commerce analytics consultant for Indian marketplace sellers.

Seller ID: {seller_id}

The seller is asking about a hypothetical scenario:
"{scenario}"

Current seller data context:
{context_summary}

Analyse this what-if scenario:
1. Estimate the likely revenue/profit impact in ₹/month (positive or negative)
2. Identify risks and side-effects
3. Suggest 2-3 conditions under which this would or would not work
4. Give a clear RECOMMEND or DO NOT RECOMMEND verdict

Be specific, use numbers where possible, and keep the response under 300 words.
"""


@router.post("/whatif")
async def whatif(request: WhatIfRequest):
    """
    Stream a Gemini what-if analysis grounded in seller data.
    """
    async def scenario_stream() -> AsyncIterator[str]:
        try:
            ctx = await gemini.build_seller_context(request.seller_id)
            kpis = ctx.get("kpis") or {}
            context_summary = (
                f"Revenue: ₹{float(kpis.get('total_net_revenue') or 0):,.0f}/month, "
                f"Orders: {int(kpis.get('total_orders') or 0):,}, "
                f"ROAS: {float(kpis.get('avg_roas') or 0):.2f}x, "
                f"Low stock SKUs: {int(kpis.get('low_stock_count') or 0)}"
            )

            prompt = WHATIF_PROMPT.format(
                seller_id=request.seller_id,
                scenario=request.scenario,
                context_summary=context_summary,
            )

            import vertexai
            from vertexai.generative_models import GenerativeModel, GenerationConfig
            from app.core.config import settings

            vertexai.init(project=settings.GCP_PROJECT, location=settings.VERTEX_LOCATION)
            model = GenerativeModel(settings.GEMINI_MODEL)

            stream = model.generate_content(
                prompt,
                generation_config=GenerationConfig(temperature=0.4),
                stream=True,
            )
            for chunk in stream:
                if chunk.text:
                    yield f"data: {json.dumps({'text': chunk.text})}\n\n"

        except Exception as e:
            logger.error("What-if stream error: %s", e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(scenario_stream(), media_type="text/event-stream")
