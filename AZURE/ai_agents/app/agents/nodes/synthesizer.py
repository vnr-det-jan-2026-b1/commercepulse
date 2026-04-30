"""
Synthesizer Agent — CEO Persona (Chief Strategist).
Takes the output from all 4 domain agents, removes redundant suggestions,
and produces the final ranked executive action plan focused on GROWING SALES.
"""
import os
import json
from langchain_groq import ChatGroq
from app.agents.state import SystemState
from app.agents.schemas import ExecutiveActionPlan


def run_synthesizer(state: SystemState) -> dict:
    """
    CEO Persona — Chief Strategist.
    Combines Revenue, Operations, Marketing, and Market insights into
    ONE prioritized sales growth plan with quick wins and ranked actions.
    """
    print("🧠 [Synthesizer] Merging all agent insights into a final Sales Growth Plan...")

    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.1)
    llm = llm.with_config(tags=["synthesizer"])
    structured_llm = llm.with_structured_output(ExecutiveActionPlan)

    # Gather the domain insights
    revenue = state.get("revenue_insights", {})
    ops = state.get("ops_insights", {})
    market = state.get("market_insights", {})
    marketing = state.get("marketing_insights", {})

    # Also grab the raw KPIs for context
    snapshot = state.get("snapshot_data", {})
    dashboard_kpis = json.dumps(snapshot.get("dashboard_kpis", {}), indent=2, default=str)

    # Serialize domain reports
    try:
        rev_text = revenue.model_dump_json(indent=2) if revenue else "No Revenue Insights available"
        ops_text = ops.model_dump_json(indent=2) if ops else "No Ops Insights available"
        market_text = market.model_dump_json(indent=2) if market else "No Brand Insights available"
        cmo_text = marketing.model_dump_json(indent=2) if marketing else "No Marketing Insights available"
    except AttributeError:
        rev_text = str(revenue)
        ops_text = str(ops)
        market_text = str(market)
        cmo_text = str(marketing)

    prompt = f"""You are the CEO and founder of "Brew Boulevard", a D2C specialty coffee startup in India. You're not a corporate executive giving board-room advice — you're a FOUNDER who needs to grow sales THIS WEEK. Every rupee matters. Every decision must be backed by data.

Your multi-agent intelligence system has generated FOUR domain reports from REAL business data:

=== CURRENT BUSINESS SNAPSHOT ===
{dashboard_kpis}

=== [CFO REPORT] Revenue & Pricing Intelligence ===
{rev_text}

=== [COO REPORT] Operations & Logistics Intelligence ===
{ops_text}

=== [BRAND REPORT] Channel & Market Intelligence ===
{market_text}

=== [CMO REPORT] Marketing & Ad Spend Intelligence ===
{cmo_text}

YOUR MISSION — Build a Sales Growth Action Plan:

1. **Primary Problem Statement**: In 1-2 sentences, what is the SINGLE BIGGEST thing holding back Brew Boulevard's sales growth right now? Be specific and data-backed.

2. **Quick Wins (48-hour actions)**: List 2-3 things the team can do RIGHT NOW with zero cost to immediately improve sales or stop losing money. Examples:
   - "Pause the ₹X/month ad campaign on [product] that has ROAS 0.3"
   - "Restock [product] on [marketplace] — currently out of stock, losing ₹X/day"
   - "Increase [product] price from ₹X to ₹Y on [marketplace] — margin jumps from X% to Y%"

3. **Ranked Action Plan**: Merge the best actions from all 4 reports into ONE unified list. For each action you MUST provide ALL of these fields:
   - **action_name**: Short title of the action
   - **reason**: WHY is this needed? (reference specific data)
   - **strategy**: HOW to implement it (step-by-step for a small team)
   - **description**: A 1-sentence summary of the action and its expected outcome. THIS FIELD IS MANDATORY.
   - **estimated_impact_percentage**: Expected revenue/conversion improvement %
   - **financial_impact_monthly**: Impact in ₹/month
   - **is_profit_safe**: true/false
   - **risk_level**: Low/Medium/High
   - **difficulty**: Low/Medium/High
   - **timeframe**: When to do it (Immediate / This Week / This Month)
   
   RULES for ranking:
   - EVERY action MUST have ALL fields listed above. Never omit 'description'.
   - Remove duplicate or conflicting suggestions across agents
   - Rank by: (financial_impact × confidence) ÷ difficulty
   - Quick, high-impact, low-risk actions come first
   - Never recommend an action that hurts net profit margin
   - MAXIMUM 5 ACTIONS. Do not generate more than 5 ranked actions.

4. **Confidence Score**: How confident are you in this plan based on the data quality? (0.0 to 1.0)

Think like a bootstrapped founder, not a consultant. Be direct, specific, and aggressive about growing sales."""

    from app.utils import get_groq_api_key
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.1)

    import time
    max_retries = 3
    for attempt in range(max_retries + 1):
        try:
            key = get_groq_api_key()
            result: ExecutiveActionPlan = llm.with_config({"api_key": key}).with_structured_output(ExecutiveActionPlan).invoke(prompt)
            if result is None:
                print("⚠️ [Synthesizer] LLM returned None. Falling back to empty plan.")
                return {"final_executive_plan": None}
            return {"final_executive_plan": result}
        except Exception as e:
            error_str = str(e)
            if attempt < max_retries:
                if "rate_limit_exceeded" in error_str or "429" in error_str:
                    print(f"  ⚠️ [Synthesizer] Rate limit hit. Sleeping for 5s... (Attempt {attempt+1})")
                    time.sleep(5)
                    continue
                if "tool_use_failed" in error_str or "missing properties" in error_str:
                    print(f"  ⚠️ [Synthesizer] Retry {attempt + 1}/{max_retries} due to schema validation error...")
                    time.sleep(2)
                    continue
            print(f"  ❌ [Synthesizer] Failed after {attempt + 1} attempts: {e}")
            return {"final_executive_plan": None}
