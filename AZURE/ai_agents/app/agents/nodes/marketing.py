import os
from langchain_groq import ChatGroq
from app.agents.state import SystemState
from app.agents.schemas import MarketingInsights
from app.db.supabase_client import fetch_recent_context

def run_marketing_agent(state: SystemState) -> dict:
    """
    CMO Persona (Chief Marketing Officer)
    Focus: Ad spend, ROAS, traffic quality, conversion funnel drop-offs.
    Action logic: Kill low ROAS campaigns, double down on high intent keywords.
    """
    print("📈 [Marketing Agent] Starting ROAS & Traffic analysis...")
    
    # Extract the payload the backend sent us
    snapshot_data = state.get("snapshot_data", {})
    seller_id = state.get("seller_id", "")
    
    # 1. Fetch live historical data from Supabase
    try:
        context_docs = fetch_recent_context(
            seller_id=seller_id,
            limit=3
        )
        recent_context_str = "\n".join([doc.page_content for doc in context_docs]) if context_docs else "No historical marketing data available in vector store."
    except Exception as e:
        print(f"Warning: Failed to fetch Supabase context in Marketing agent: {e}")
        recent_context_str = "Error fetching historical context."

    # 2. Initialize the fast Groq LLM
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.1)
    
    # Bind our Pydantic schema to force the LLM to output structured JSON
    structured_llm = llm.with_structured_output(MarketingInsights)
    
    # 3. Build the prompt
    prompt = f"""
    You are the Chief Marketing Officer (CMO) of a rapidly scaling e-commerce brand.
    Your focus is *strictly* on driving profitable traffic, maximizing ROAS (Return on Ad Spend), and eliminating wasted advertising budget.
    
    We have received a new business event / snapshot for Seller {seller_id}:
    {snapshot_data}
    
    Here is the recent historical data for their top products from our database (pay attention to traffic, clicks, and ROAS):
    {recent_context_str}
    
    Your Task:
    Validate if the current ad campaigns are effective or if we are wasting money on traffic that bounces or doesn't convert.
    Be extremely critical of any campaign with low ROAS. If a product is out of stock or overpriced compared to the market, recommend pulling the ad spend immediately.
    
    Output your analysis matching the required MarketingInsights schema. Ensure all 'wasted_ad_spend_monthly' estimates are realistic based on the provided inputs.
    """
    
    # 4. Invoke LLM and return update for the State
    try:
        result: MarketingInsights = structured_llm.invoke(prompt)
        return {"marketing_insights": result}
    except Exception as e:
        print(f"Error in Marketing Agent: {e}")
        return {"marketing_insights": None}
