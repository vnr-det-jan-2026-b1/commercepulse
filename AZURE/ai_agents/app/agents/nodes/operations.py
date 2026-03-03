import os
from langchain_groq import ChatGroq
from app.agents.state import SystemState
from app.agents.schemas import OperationsInsights

def run_ops_agent(state: SystemState) -> dict:
    """
    COO Persona.
    Analyzes delivery SLA drops, warehouse metrics, and return probabilities.
    """
    from app.db.supabase_client import fetch_recent_context
    print("⚙️ [Ops Agent] Fetching recent context from Supabase/pgvector...")
    
    seller_id = state.get("seller_id")
    recent_context = fetch_recent_context(seller_id, limit=5)
    
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.0)
    structured_llm = llm.with_structured_output(OperationsInsights)
    
    snapshot = state.get("snapshot_data", {})
    
    prompt = f"""
    You are the Chief Operating Officer (COO) and Supply Chain Director of a vast eCommerce logistics network.
    Your domain is fulfillment efficiency, Service Level Agreement (SLA) adherence, reverse-logistics (returns), and warehouse unit economics.
    
    Here is the recent product context from our PostgreSQL vector database for Seller {seller_id}:
    {recent_context}

    Analyze the following recent triggered event/snapshot for Seller {seller_id}:
    {snapshot}
    
    DIRECTIONS:
    1. Identify exact root causes for fulfillment SLA breaches (e.g., pinpointing specific delayed hubs or carrier handover issues).
    2. Measure the exact correlation between delivery delays and the probability of return spikes.
    3. If formulating a counter-measure (like Free Shipping or expedited delivery), enforce strict conditional logic (e.g., only apply if cart value > $50) to protect unit margins.
    4. Provide ruthless, fact-based insights. Do not suggest abstract fixes. Tell us exactly where the supply chain is bleeding.
    """
    
    try:
        result: OperationsInsights = structured_llm.invoke(prompt)
        return {"ops_insights": result}
    except Exception as e:
        print(f"Error in Ops Agent: {e}")
        return {"ops_insights": None}
