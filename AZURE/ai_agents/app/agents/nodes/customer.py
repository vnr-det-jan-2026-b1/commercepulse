import os
from langchain_groq import ChatGroq
from app.agents.state import SystemState
from app.agents.schemas import MarketInsights

def run_customer_agent(state: SystemState) -> dict:
    """
    Brand Strategist Persona.
    Uses vector similarity (from Supabase/pgvector) to detect sentiment drift and competitor shocks.
    """
    from app.db.supabase_client import fetch_recent_context
    print("🎯 [Customer Agent] Fetching recent context from Supabase/pgvector...")
    
    seller_id = state.get("seller_id")
    recent_context = fetch_recent_context(seller_id, limit=5)
    
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.0)
    structured_llm = llm.with_structured_output(MarketInsights)
    
    snapshot = state.get("snapshot_data", {})
    
    prompt = f"""
    You are the Chief Brand Strategist and Customer Success Director for a major eCommerce company.
    Your sole focus is managing public perception, identifying precise macro-economic or competitive shocks, and 
    diagnosing the root causes of sentiment drift before they cause irreversible brand damage.

    Here is the recent product context from our PostgreSQL vector database for Seller {seller_id}:
    {recent_context}

    Analyze the following recent triggered event/snapshot for Seller {seller_id}:
    {snapshot}
    
    DIRECTIONS:
    1. Scan the textual and metric data for 'Sentiment Drift' (e.g., correlations between delivery delays and negative reviews).
    2. Identify any external competitive shocks (e.g., aggressive price matching from rivals).
    3. Output highly specific, mathematically grounded findings. Do NOT give generic advice like 'improve customer service'. Instead, pinpoint exactly which metric is failing and what specifically is driving the sentiment down.
    """
    
    try:
        result: MarketInsights = structured_llm.invoke(prompt)
        return {"market_insights": result}
    except Exception as e:
        print(f"Error in Customer Agent: {e}")
        return {"market_insights": None}
