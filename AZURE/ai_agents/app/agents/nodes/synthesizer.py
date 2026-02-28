import os
from langchain_openai import ChatOpenAI
from app.agents.state import SystemState
from app.agents.schemas import ExecutiveActionPlan

def run_synthesizer(state: SystemState) -> dict:
    """
    CEO Persona (Chief Strategist).
    Takes the output from Revenue, Ops, and Customer nodes, removes redundant suggestions,
    and produces the final ranked executive action plan.
    """
    print("🧠 [Synthesizer] Merging insights into a final Executive Action Plan...")
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
    structured_llm = llm.with_structured_output(ExecutiveActionPlan)
    
    # Gather the parallel insights
    revenue = state.get("revenue_insights", {})
    ops = state.get("ops_insights", {})
    market = state.get("market_insights", {})
    
    # Serialize to text for the LLM prompt
    try:
        rev_text = revenue.model_dump_json() if revenue else "No Revenue Insights"
        ops_text = ops.model_dump_json() if ops else "No Ops Insights"
        market_text = market.model_dump_json() if market else "No Market Insights"
    except AttributeError:
        # Fallback if dictionary instead of BaseModel
        rev_text = str(revenue)
        ops_text = str(ops)
        market_text = str(market)
    
    prompt = f"""
    You are the CEO and Chief Strategist of CommercePulse.
    Your system has generated three distinct domain reports for Seller {state.get("seller_id")}:
    
    [REVENUE CFO REPORT]
    {rev_text}
    
    [OPERATIONS COO REPORT]
    {ops_text}
    
    [MARKET BRAND REPORT]
    {market_text}
    
    Your goal is to combined these into ONE final `ExecutiveActionPlan`.
    - Build causal chains (e.g., Delivery -> Sentiment -> Conversion -> Revenue).
    - Remove redundant suggestions (e.g., if Ops and Market both suggest fixing 'BLR SLA', merge them).
    - Validate that every suggested action is profitable.
    - Rank actions by ROI and feasibility.
    """
    
    try:
        result: ExecutiveActionPlan = structured_llm.invoke(prompt)
        return {"final_executive_plan": result}
    except Exception as e:
        print(f"Error in Synthesizer Agent: {e}")
        return {"final_executive_plan": None}
