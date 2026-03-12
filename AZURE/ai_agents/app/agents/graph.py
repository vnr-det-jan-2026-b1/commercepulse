from langgraph.graph import StateGraph, END
from app.agents.state import SystemState
from app.agents.nodes.orchestrator import run_orchestrator
from app.agents.nodes.revenue import run_revenue_agent
from app.agents.nodes.operations import run_ops_agent
from app.agents.nodes.customer import run_customer_agent
from app.agents.nodes.synthesizer import run_synthesizer
from app.agents.nodes.marketing import run_marketing_agent

def build_commerce_pulse_engine():
    """
    Constructs the 6-agent LangGraph workflow.
    """
    workflow = StateGraph(SystemState)
    
    # 1. Add all nodes
    workflow.add_node("orchestrator", run_orchestrator)
    workflow.add_node("revenue_agent", run_revenue_agent)
    workflow.add_node("operations_agent", run_ops_agent)
    workflow.add_node("customer_agent", run_customer_agent)
    workflow.add_node("marketing_agent", run_marketing_agent)
    workflow.add_node("synthesizer", run_synthesizer)
    
    # 2. Define the exact flow
    workflow.set_entry_point("orchestrator")
    
    # langgraph 0.0.31 does not support parallel fan-out from a single node.
    # Chain agents sequentially: each agent's output accumulates in the shared state,
    # and the synthesizer receives all insights at the end.
    workflow.add_edge("orchestrator", "revenue_agent")
    workflow.add_edge("revenue_agent", "operations_agent")
    workflow.add_edge("operations_agent", "customer_agent")
    workflow.add_edge("customer_agent", "marketing_agent")
    workflow.add_edge("marketing_agent", "synthesizer")
    
    # End execution
    workflow.add_edge("synthesizer", END)
    
    # Compile the decision engine
    commerce_pulse_engine = workflow.compile()
    
    return commerce_pulse_engine

# Export the compiled engine singleton for the Celery worker to import
engine = build_commerce_pulse_engine()
