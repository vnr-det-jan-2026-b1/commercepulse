from typing import Any, Dict
from app.agents.state import SystemState

def run_orchestrator(state: SystemState) -> SystemState:
    """
    Control Tower Node.
    This does NOT use an LLM. It simply structures the incoming data (e.g. from Celery/DB)
    to ensure the domain agents have a clean, consistent snapshot.
    """
    print(f"🚀 [Orchestrator] Starting analysis for Seller {state.get('seller_id')}")
    
    # In a real scenario, this node might fetch fresh aggregations from Supabase here
    # Since we assume the data is passed in the state during invocation, we just log and pass it on.
    
    return state
