import os
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

# Tools
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


def get_chat_agent():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing")
    
    llm = ChatGroq(
        api_key=api_key,
        model="llama-3.3-70b-versatile",
        temperature=0.2,
        max_tokens=800
    )
    
    tools = [fetch_live_product_roas, fetch_live_product_inventory, fetch_product_metrics]
    
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
"""),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    return agent_executor
