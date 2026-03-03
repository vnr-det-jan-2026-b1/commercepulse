import os
from langchain_groq import ChatGroq
from app.agents.state import SystemState
from app.agents.schemas import ExecutiveActionPlan

def run_synthesizer(state: SystemState) -> dict:
    """
    CEO Persona (Chief Strategist).
    Takes the output from Revenue, Ops, and Customer nodes, removes redundant suggestions,
    and produces the final ranked executive action plan.
    """
    print("🧠 [Synthesizer] Merging insights into a final Executive Action Plan...")
    
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.1, streaming=True)
    # Give the node a tag so `astream_events` can easily filter for it
    llm = llm.with_config(tags=["synthesizer"])
    structured_llm = llm.with_structured_output(ExecutiveActionPlan)
    
    # Gather the parallel insights
    revenue = state.get("revenue_insights", {})
    ops = state.get("ops_insights", {})
    market = state.get("market_insights", {})
    marketing = state.get("marketing_insights", {})
    
    # Serialize to text for the LLM prompt
    try:
        rev_text = revenue.model_dump_json() if revenue else "No Revenue Insights"
        ops_text = ops.model_dump_json() if ops else "No Ops Insights"
        market_text = market.model_dump_json() if market else "No Brand Insights"
        cmo_text = marketing.model_dump_json() if marketing else "No Marketing/Ad Insights"
    except AttributeError:
        # Fallback if dictionary instead of BaseModel
        rev_text = str(revenue)
        ops_text = str(ops)
        market_text = str(market)
        cmo_text = str(marketing)
    
    prompt = f"""
    You are the CEO and Chief Strategist of CommercePulse. You are known for being ruthlessly analytical, completely unfiltered, and highly aggressive in finding ways to improve sales and crush the competition. Do NOT sugarcoat your findings. If a strategy is failing, say so bluntly. Provide strong, unconventional, and highly effective sales advice.
    
    Your system has generated FOUR distinct domain reports for Seller {state.get("seller_id")}:
    
    [REVENUE CFO REPORT]
    {rev_text}
    
    [OPERATIONS COO REPORT]
    {ops_text}
    
    [MARKET BRAND REPORT]
    {market_text}
    
    [MARKETING CMO REPORT]
    {cmo_text}
    
    Your goal is to combine these into ONE final `ExecutiveActionPlan`.
    - Build causal chains (e.g., Delivery -> Sentiment -> Conversion -> Revenue).
    - Remove redundant suggestions.
    - Validate that every suggested action is highly profitable and gives a strategic edge.
    - Be brutally honest about where the seller needs to improve.
    - Rank actions by ROI and urgency.
    """
    
    try:
        result: ExecutiveActionPlan = structured_llm.invoke(prompt)
        return {"final_executive_plan": result}
    except Exception as e:
        print(f"Error in Synthesizer Agent: {e}")
        return {"final_executive_plan": None}
