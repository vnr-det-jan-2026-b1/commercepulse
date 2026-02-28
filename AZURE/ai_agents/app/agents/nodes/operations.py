import os
from langchain_openai import ChatOpenAI
from app.agents.state import SystemState
from app.agents.schemas import OperationsInsights

def run_ops_agent(state: SystemState) -> dict:
    """
    COO Persona.
    Analyzes delivery SLA drops, warehouse metrics, and return probabilities.
    """
    print("⚙️ [Ops Agent] Analyzing delivery SLAs and return probabilities...")
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.0)
    structured_llm = llm.with_structured_output(OperationsInsights)
    
    snapshot = state.get("snapshot_data", {})
    
    prompt = f"""
    You are the COO of an eCommerce logistics network.
    Analyze the following data snapshot for Seller {state.get("seller_id")}:
    {snapshot}
    
    Measure how delivery delays impact return rates and overall revenue.
    If suggesting Free Shipping, ensure it includes conditional logic (e.g., cart value thresholds) if it hurts margins.
    """
    
    try:
        result: OperationsInsights = structured_llm.invoke(prompt)
        return {"ops_insights": result}
    except Exception as e:
        print(f"Error in Ops Agent: {e}")
        return {"ops_insights": None}
