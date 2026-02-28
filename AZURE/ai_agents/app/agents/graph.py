from langgraph.graph import StateGraph, END
from app.agents.state import SystemState
from app.agents.nodes.orchestrator import run_orchestrator
from app.agents.nodes.revenue import run_revenue_agent
from app.agents.nodes.operations import run_ops_agent
from app.agents.nodes.customer import run_customer_agent
from app.agents.nodes.synthesizer import run_synthesizer

def build_commerce_pulse_engine():
    """
    Constructs the 5-agent LangGraph workflow.
    """
    workflow = StateGraph(SystemState)
    
    # 1. Add all nodes
    workflow.add_node("orchestrator", run_orchestrator)
    workflow.add_node("revenue_agent", run_revenue_agent)
    workflow.add_node("operations_agent", run_ops_agent)
    workflow.add_node("customer_agent", run_customer_agent)
    workflow.add_node("synthesizer", run_synthesizer)
    
    # 2. Define the exact flow
    workflow.set_entry_point("orchestrator")
    
    # Orchestrator triggers the 3 domain agents IN PARALLEL
    workflow.add_edge("orchestrator", "revenue_agent")
    workflow.add_edge("orchestrator", "operations_agent")
    workflow.add_edge("orchestrator", "customer_agent")
    
    # All 3 domain agents must complete before the Synthesizer triggers
    # In LangGraph, if multiple edges point to the same node, it automatically waits 
    # for all of them to finish in the graph traversal.
    workflow.add_edge("revenue_agent", "synthesizer")
    workflow.add_edge("operations_agent", "synthesizer")
    workflow.add_edge("customer_agent", "synthesizer")
    
    # End execution
    workflow.add_edge("synthesizer", END)
    
    # Compile the decision engine
    commerce_pulse_engine = workflow.compile()
    
    return commerce_pulse_engine

# Export the compiled engine singleton for the Celery worker to import
engine = build_commerce_pulse_engine()
