import os
from langchain_openai import ChatOpenAI
from app.agents.state import SystemState
from app.agents.schemas import RevenueInsights

def run_revenue_agent(state: SystemState) -> dict:
    """
    CFO Persona.
    Examines the snapshot data for revenue drops and simulates discount safety.
    """
    print("📈 [Revenue Agent] Analyzing price gaps and discount simulations...")
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.0)
    
    # We force the LLM to output exactly our Pydantic schema
    structured_llm = llm.with_structured_output(RevenueInsights)
    
    snapshot = state.get("snapshot_data", {})
    
    prompt = f"""
    You are the CFO of an eCommerce brand.
    Analyze the following data snapshot for Seller {state.get("seller_id")}:
    {snapshot}
    
    Identify revenue leakage causes (conversion drops, price gaps, stockouts).
    Before recommending a discount, ensure `is_profit_safe` is accurately evaluated.
    """
    
    try:
        # Generate the structured insight
        result: RevenueInsights = structured_llm.invoke(prompt)
        return {"revenue_insights": result}
    except Exception as e:
        print(f"Error in Revenue Agent: {e}")
        # Return empty state if failure
        return {"revenue_insights": None}
