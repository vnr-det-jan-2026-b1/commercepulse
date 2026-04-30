from langgraph.graph import StateGraph, END
from app.agents.state import SystemState

# Import domain agents (reused)
from app.agents.nodes.revenue import run_revenue_agent
from app.agents.nodes.operations import run_ops_agent
from app.agents.nodes.customer import run_customer_agent
from app.agents.nodes.marketing import run_marketing_agent

# Import per-product orchestrator and synthesizer
from app.agents.nodes.product_orchestrator import run_product_orchestrator
from app.agents.nodes.product_synthesizer import run_product_synthesizer

def build_product_analysis_engine():
    """
    Builds the multi-agent graph specifically for Per-Product Analysis.
    Sequential flow:
    Orchestrator -> Revenue -> Ops -> Customer -> Marketing -> Synthesizer -> END
    """
    workflow = StateGraph(SystemState)
    
    # Add Nodes
    workflow.add_node("product_orchestrator", run_product_orchestrator)
    workflow.add_node("revenue_agent", run_revenue_agent)
    workflow.add_node("operations_agent", run_ops_agent)
    workflow.add_node("customer_agent", run_customer_agent)
    workflow.add_node("marketing_agent", run_marketing_agent)
    workflow.add_node("product_synthesizer", run_product_synthesizer)
    
    # Define Edges (Sequential for reasoning chain)
    workflow.set_entry_point("product_orchestrator")
    workflow.add_edge("product_orchestrator", "revenue_agent")
    workflow.add_edge("revenue_agent", "operations_agent")
    workflow.add_edge("operations_agent", "customer_agent")
    workflow.add_edge("customer_agent", "marketing_agent")
    workflow.add_edge("marketing_agent", "product_synthesizer")
    workflow.add_edge("product_synthesizer", END)
    
    return workflow.compile()
