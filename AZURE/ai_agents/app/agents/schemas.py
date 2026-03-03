from pydantic import BaseModel, Field
from typing import List, Optional

# -------------------------------------------------------------------
# Common Structures
# -------------------------------------------------------------------
class ActionItem(BaseModel):
    action_name: str = Field(description="Short title of the recommended action")
    description: str = Field(description="Detailed explanation of the action to take")
    estimated_impact_percentage: float = Field(description="Estimated positive impact on revenue/conversion as a percentage")
    financial_impact_monthly: float = Field(description="Estimated monetary value of this action per month (in original currency, e.g., INR)")
    is_profit_safe: bool = Field(description="Must evaluate to True if this action has been simulated and ensures net profit growth (e.g., after COGS and shipping)")
    risk_level: str = Field(description="Low, Medium, or High risk associated with this action")
    difficulty: str = Field(description="Low, Medium, or High implementation difficulty")


# -------------------------------------------------------------------
# Agent Outputs (Domain Insights)
# -------------------------------------------------------------------

class RevenueInsights(BaseModel):
    """Output schema for the Revenue Intelligence Agent (CFO persona)"""
    conversion_drop_impact_pct: float = Field(description="Percentage impact of conversion drop on overall revenue")
    price_gap_impact_pct: float = Field(description="Percentage impact of competitor pricing gaps")
    stockout_impact_pct: float = Field(description="Percentage impact of out-of-stock items")
    discount_misuse_pct: float = Field(description="Percentage impact of misused or inefficient discounting")
    recommended_actions: List[ActionItem] = Field(description="CFO-approved actions (validated for profit margin)")


class OperationsInsights(BaseModel):
    """Output schema for the Operations & Cost Intelligence Agent (COO persona)"""
    delivery_delay_increase_days: float = Field(description="Average increase in delivery SLA delays")
    return_probability_increase_pct: float = Field(description="Increase in return probability due to operational issues")
    revenue_loss_contribution_pct: float = Field(description="How much of the total revenue loss is driven by operations")
    recommended_actions: List[ActionItem] = Field(description="COO-approved operational fixes (e.g., warehouse SLAs, shipping adjustments)")


class MarketInsights(BaseModel):
    """Output schema for the Customer & Market Intelligence Agent (Brand Strategist persona)"""
    sentiment_drift_topic: str = Field(description="Primary topic of negative sentiment drift (e.g., 'Delivery complaints', 'Quality issues')")
    sentiment_revenue_impact_pct: float = Field(description="Estimated revenue drop contribution from sentiment shifts")
    competitor_shock_detected: bool = Field(description="True if a major competitor moved prices or launched an aggressive campaign")
    churn_risk_probability: float = Field(description="Probability (0.0 to 1.0) of increased customer churn")
    recommended_actions: List[ActionItem] = Field(description="Brand-approved actions to correct sentiment or market positioning")

class MarketingInsights(BaseModel):
    """Output schema for the Marketing & Growth Intelligence Agent (CMO persona)"""
    inefficient_ad_spend_pct: float = Field(description="Percentage of total ad spend currently yielding negative ROAS or sub-optimal conversion")
    wasted_ad_spend_monthly: float = Field(description="Estimated monetary value of wasted or inefficient ad spend per month (in original currency)")
    primary_traffic_bottleneck: str = Field(description="The main reason traffic isn't converting (e.g., 'Low CTR on main image', 'High bounce rate due to pricing')")
    recommended_campaign_kills: List[str] = Field(description="Specific campaigns or keyword strategies to pause instantly to save money")
    recommended_actions: List[ActionItem] = Field(description="CMO-approved actions to optimize ROAS, shift budget, or capture competitor traffic")


# -------------------------------------------------------------------
# Final Output (Synthesizer)
# -------------------------------------------------------------------

class ExecutiveActionPlan(BaseModel):
    """Final output from the Synthesizer Agent (CEO persona) combining all insights."""
    primary_problem_statement: str = Field(description="A concise summary of the core issue driving revenue loss.")
    total_revenue_recovery_potential_pct: float = Field(description="Summed expected recovery percentage from approved actions.")
    total_financial_recovery_monthly: float = Field(description="Estimated absolute financial recovery per month.")
    ranked_actions: List[ActionItem] = Field(description="The finalized, merged list of actions ranked by ROI and Risk. MUST eliminate redundant suggestions.")
    confidence_score: float = Field(description="Confidence score (0.0 to 1.0) in this overall strategy based on data availability.")
