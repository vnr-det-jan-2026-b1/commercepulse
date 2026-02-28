import os
from langchain_openai import ChatOpenAI
from app.agents.state import SystemState
from app.agents.schemas import MarketInsights

def run_customer_agent(state: SystemState) -> dict:
    """
    Brand Strategist Persona.
    Uses vector similarity (from Supabase/pgvector) to detect sentiment drift and competitor shocks.
    """
    print("🎯 [Customer Agent] Checking pgvector for sentiment drift and competitor alerts...")
    
    # In a real implementation: Connect to Supabase here and query `pgvector`
    # e.g., using `supabase.table("reviews").select("*").order("embedding", {"ascending": True}).limit(5)`
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.0)
    structured_llm = llm.with_structured_output(MarketInsights)
    
    snapshot = state.get("snapshot_data", {})
    
    prompt = f"""
    You are the Brand Strategist for an eCommerce company.
    Analyze the following data snapshot (including simulated recent reviews and traffic):
    Seller: {state.get("seller_id")}
    Data: {snapshot}
    
    Determine if there is a 'Sentiment Drift' (e.g., spike in delivery complaints) 
    and identify if a competitor shock has occurred. Output your findings.
    """
    
    try:
        result: MarketInsights = structured_llm.invoke(prompt)
        return {"market_insights": result}
    except Exception as e:
        print(f"Error in Customer Agent: {e}")
        return {"market_insights": None}
