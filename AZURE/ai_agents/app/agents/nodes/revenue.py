import os
from langchain_groq import ChatGroq
from app.agents.state import SystemState
from app.agents.schemas import RevenueInsights

def run_revenue_agent(state: SystemState) -> dict:
    """
    CFO Persona.
    Examines the snapshot data for revenue drops and simulates discount safety.
    """
    from app.db.supabase_client import fetch_recent_context
    print("📈 [Revenue Agent] Fetching recent context from Supabase/pgvector...")
    
    seller_id = state.get("seller_id")
    recent_context = fetch_recent_context(seller_id, limit=5)
    
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.0)
    
    # We force the LLM to output exactly our Pydantic schema
    structured_llm = llm.with_structured_output(RevenueInsights)
    
    snapshot = state.get("snapshot_data", {})
    
    prompt = f"""
    You are the Chief Financial Officer (CFO) and Head of Pricing Strategy for a massive eCommerce portfolio.
    You deal strictly in numbers, margin thresholds, price elasticity, and direct revenue impact. You care about protecting net profit at all costs.
    
    Here is the recent product context from our PostgreSQL vector database for Seller {seller_id}:
    {recent_context}

    Analyze the following recent triggered event/snapshot for Seller {seller_id}:
    {snapshot}
    
    DIRECTIONS:
    1. Calculate and identify precisely where revenue is leaking (e.g., conversion drops caused directly by competitor pricing, stockout velocity).
    2. Assess the absolute gross margin hit of the current scenario.
    3. Before authorizing any price discounts, rigorously evaluate if `is_profit_safe` is true. Never suggest a discount that falls below the baseline COGS/margin requirement unless it's a strategic loss-leader.
    4. Provide immediate, exact financial counter-measures (e.g., 'Deploy a 4% targeted coupon instead of a flat 8% price drop to preserve margins').
    """
    
    try:
        # Generate the structured insight
        result: RevenueInsights = structured_llm.invoke(prompt)
        return {"revenue_insights": result}
    except Exception as e:
        print(f"Error in Revenue Agent: {e}")
        # Return empty state if failure
        return {"revenue_insights": None}
