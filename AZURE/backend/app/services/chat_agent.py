import os
import time
import logging
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

logger = logging.getLogger(__name__)

# ── Tools ─────────────────────────────────────────────────────

@tool
def fetch_live_product_roas(product_id: str) -> str:
    """
    Fetches the live, mathematically exact ROAS (Return on Ad Spend) for a specific product.
    Use this tool to verify ROAS numbers.
    """
    import httpx
    backend_url = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8010").rstrip("/")
    url = f"{backend_url}/analytics/product/{product_id}/roas"
    try:
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        data = response.json()
        return f"Live ROAS for {product_id} is {data.get('roas', 'unknown')}. Total Spend: {data.get('total_spend', 'unknown')}."
    except Exception as e:
        return f"Could not verify live ROAS due to API error: {str(e)}."

@tool
def fetch_live_product_inventory(product_id: str) -> str:
    """
    Fetches the live inventory count for a specific product.
    Use this tool to verify if a product is actually out of stock.
    """
    import httpx
    backend_url = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8010").rstrip("/")
    url = f"{backend_url}/analytics/inventory/{product_id}"
    try:
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        data = response.json()
        return f"Live inventory for {product_id} is {data.get('available_stock', 'unknown')} units."
    except Exception as e:
        return f"Could not verify live inventory due to API error: {str(e)}."

@tool
def fetch_product_metrics(product_id: str, seller_id: str) -> str:
    """
    Fetches comprehensive deep live metrics (like Revenue, AOV, ROAS, Returns, Units Sold, Delivery Days) for a specific product.
    Requires product_id and seller_id.
    """
    import httpx
    backend_url = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8010").rstrip("/")
    url = f"{backend_url}/analytics/product/{product_id}/metrics?seller_id={seller_id}"
    try:
        response = httpx.get(url, timeout=5.0)
        if response.status_code == 404:
            return "Product not found."
        response.raise_for_status()
        data = response.json()
        import json
        return f"Live comprehensive product metrics: {json.dumps(data)}"
    except Exception as e:
        return f"Could not fetch product metrics due to API error: {str(e)}."

@tool
def fetch_all_products_metrics(seller_id: str) -> str:
    """
    Fetches the metrics for all products owned by the seller, including product ID, name, SKU, total revenue, total orders, ROAS, and inventory stock level.
    Use this tool when the user asks about top-selling products, best performers, general product performance, or lists of products.
    """
    import httpx
    backend_url = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8010").rstrip("/")
    url = f"{backend_url}/analytics/products/list?seller_id={seller_id}"
    try:
        response = httpx.get(url, timeout=5.0)
        if response.status_code == 404:
            return "Seller or products not found."
        response.raise_for_status()
        data = response.json()
        import json
        return f"All products metrics: {json.dumps(data.get('data', []))}"
    except Exception as e:
        return f"Could not fetch all products metrics due to API error: {str(e)}."


# ── Multi-Key Resilient Fallback System ───────────────────────

def _collect_api_keys():
    """Collect all available Groq API keys from environment variables."""
    keys = []
    # Primary key
    primary = os.getenv("GROQ_API_KEY")
    if primary:
        keys.append(primary)
    # Additional keys (numbered)
    for suffix in ["GROQ_API_KEY_2", "GROQ_API_KEY_3"]:
        k = os.getenv(suffix)
        if k and k not in keys:
            keys.append(k)
    # Dedicated fallback key
    fallback = os.getenv("FALLBACK_GROQ_API_KEY")
    if fallback and fallback not in keys:
        keys.append(fallback)
    return keys


def _is_rate_limit_error(e: Exception) -> bool:
    """Check if an exception is a 429 rate limit error."""
    err_str = str(e).lower()
    return "429" in err_str or "rate limit" in err_str or "rate_limit" in err_str


def _parse_retry_after(e: Exception) -> float:
    """Try to parse the retry-after time from a rate limit error message."""
    import re
    err_str = str(e)
    match = re.search(r"try again in (\d+\.?\d*)", err_str, re.IGNORECASE)
    if match:
        return min(float(match.group(1)), 30.0)  # Cap at 30 seconds
    return 5.0  # Default wait


def make_resilient_runnable(model_configs):
    """
    Creates a runnable that tries multiple model+key combinations.
    model_configs: list of (ChatGroq_instance, description_str) tuples.
    If ALL fail, returns a graceful error message instead of crashing.
    """

    def invoke_fn(input, config=None, **kwargs):
        last_error = None
        for model, desc in model_configs:
            try:
                return model.invoke(input, config, **kwargs)
            except Exception as e:
                last_error = e
                if _is_rate_limit_error(e):
                    wait = _parse_retry_after(e)
                    logger.warning(f"[Chat] {desc} hit rate limit. Waiting {wait:.1f}s before trying next key...")
                    time.sleep(min(wait, 3.0))  # Brief pause before trying next key
                else:
                    logger.error(f"[Chat] {desc} failed with non-rate-limit error: {e}")
        # All models exhausted
        logger.error(f"[Chat] ALL model/key combinations exhausted. Last error: {last_error}")
        raise last_error

    async def ainvoke_fn(input, config=None, **kwargs):
        import asyncio
        last_error = None
        for model, desc in model_configs:
            try:
                return await model.ainvoke(input, config, **kwargs)
            except Exception as e:
                last_error = e
                if _is_rate_limit_error(e):
                    wait = _parse_retry_after(e)
                    logger.warning(f"[Chat] {desc} hit rate limit. Waiting {wait:.1f}s before trying next key...")
                    await asyncio.sleep(min(wait, 3.0))
                else:
                    logger.error(f"[Chat] {desc} failed with non-rate-limit error: {e}")
        logger.error(f"[Chat] ALL model/key combinations exhausted. Last error: {last_error}")
        raise last_error

    return RunnableLambda(invoke_fn, afunc=ainvoke_fn)


class ResilientChatGroq:
    """
    A ChatGroq wrapper that rotates through multiple API keys and models.
    Tries each key with the primary model first, then each key with the fallback model.
    """

    def __init__(self, model_configs):
        """model_configs: list of (ChatGroq, description) tuples"""
        self.model_configs = model_configs

    def bind_tools(self, tools, **kwargs):
        bound_configs = []
        for model, desc in self.model_configs:
            bound_configs.append((model.bind_tools(tools, **kwargs), desc))
        return make_resilient_runnable(bound_configs)

    def with_structured_output(self, schema, **kwargs):
        struct_configs = []
        for model, desc in self.model_configs:
            struct_configs.append((model.with_structured_output(schema, **kwargs), desc))
        return make_resilient_runnable(struct_configs)

    def invoke(self, messages, **kwargs):
        return make_resilient_runnable(self.model_configs).invoke(messages, **kwargs)

    def ainvoke(self, messages, **kwargs):
        return make_resilient_runnable(self.model_configs).ainvoke(messages, **kwargs)


# ── Agent Factory ─────────────────────────────────────────────

def get_chat_agent():
    api_keys = _collect_api_keys()
    if not api_keys:
        raise ValueError("No Groq API keys found. Set GROQ_API_KEY or FALLBACK_GROQ_API_KEY.")

    # Build model configs: try each key with primary model, then each key with fallback model
    PRIMARY_MODEL = "llama-3.3-70b-versatile"
    FALLBACK_MODEL = "llama-3.1-8b-instant"

    model_configs = []

    # Phase 1: Try all keys with the powerful primary model
    for i, key in enumerate(api_keys):
        model = ChatGroq(
            api_key=key,
            model=PRIMARY_MODEL,
            temperature=0.2,
            max_tokens=800,
        )
        model_configs.append((model, f"Key#{i+1}/{PRIMARY_MODEL}"))

    # Phase 2: Try all keys with the lighter fallback model
    for i, key in enumerate(api_keys):
        model = ChatGroq(
            api_key=key,
            model=FALLBACK_MODEL,
            temperature=0.2,
            max_tokens=800,
        )
        model_configs.append((model, f"Key#{i+1}/{FALLBACK_MODEL}"))

    logger.info(f"[Chat] Initialized with {len(api_keys)} API keys × 2 models = {len(model_configs)} fallback combinations.")

    llm = ResilientChatGroq(model_configs)

    tools = [fetch_live_product_roas, fetch_live_product_inventory, fetch_product_metrics, fetch_all_products_metrics]

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an elite, highly aggressive Senior Business Analyst & Strategist for a D2C brand named "Brew Boulevard". 
Your job is to answer the user's questions strictly based on their real data.
Be concise, highly professional, use bullet points if needed, and reference actual Rs amounts, percentages, and units.

Here is the LIVE DATA context for Brew Boulevard:
{context_str}

If the user asks about a specific product, and you have its product_id, USE YOUR TOOLS to fetch live metrics, inventory, or ROAS for it before answering.

Rules:
1. Do not hallucinate metrics. Assume the LIVE DATA provided is the most current and relevant data for the user's query.
2. Be aggressive about growth and protecting margins. Focus on profitability, ROAS optimization, and high-impact actions.
3. Keep responses under 200 words unless explaining a complex multi-step strategy.
4. Always reference actual financial numbers (Rs amounts) to back up your claims.
5. Provide extremely actionable, data-driven advice for D2C scaling.
6. If the user asks about a specific product, USE your `fetch_product_metrics` tool to get the full picture, do NOT just guess.
7. If the user asks about overall product metrics, top selling products, or general catalog queries, USE the `fetch_all_products_metrics` tool to get the full product catalog metrics before answering. Use the Seller ID from the context.
"""),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    return agent_executor
