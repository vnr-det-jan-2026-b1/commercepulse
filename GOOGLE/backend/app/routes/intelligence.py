"""Intelligence routes — GET /intelligence/* (ML prediction outputs)"""
from fastapi import APIRouter, Depends, Query

from app.core.security import enforce_seller_scope
from app.clients import bigquery_client as bq
from app.core.config import settings

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

ML  = settings.BQ_DATASET_ML
G   = settings.BQ_DATASET_GOLD


@router.get("/demand-forecast")
async def demand_forecast(
    seller_id:  str = Query(...),
    sku:        str | None = Query(None),
    days_ahead: int = Query(14, ge=1, le=30),
    _scope:     str = Depends(enforce_seller_scope),
):
    sku_filter = "AND sku = @sku" if sku else ""
    sql = f"""
        SELECT
          sku, marketplace, forecast_date,
          ROUND(predicted_units, 1)        AS predicted_units,
          ROUND(prediction_interval_lower, 1) AS lower_bound,
          ROUND(prediction_interval_upper, 1) AS upper_bound,
          model_version
        FROM `{ML}.demand_forecasts`
        WHERE seller_id = @seller_id
          AND forecast_date BETWEEN CURRENT_DATE()
              AND DATE_ADD(CURRENT_DATE(), INTERVAL @days_ahead DAY)
          {sku_filter}
        ORDER BY sku, forecast_date
    """
    params = {"seller_id": seller_id, "days_ahead": days_ahead}
    if sku:
        params["sku"] = sku

    rows = await bq.query(sql, params)
    return {"seller_id": seller_id, "days_ahead": days_ahead, "forecasts": rows}


@router.get("/inventory-risk")
async def inventory_risk(
    seller_id: str = Query(...),
    _scope:    str = Depends(enforce_seller_scope),
):
    sql = f"""
        SELECT
          sku, marketplace, available_stock, reserved_stock,
          avg_daily_units, ROUND(days_until_stockout, 1) AS days_until_stockout,
          recommended_reorder_qty, risk_level, score_date
        FROM `{G}.inventory_risk_scores`
        WHERE seller_id = @seller_id
        ORDER BY
          CASE risk_level WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1
                          WHEN 'MEDIUM' THEN 2 ELSE 3 END,
          days_until_stockout ASC
    """
    rows = await bq.query(sql, {"seller_id": seller_id})
    summary = {
        "critical": sum(1 for r in rows if r["risk_level"] == "CRITICAL"),
        "high":     sum(1 for r in rows if r["risk_level"] == "HIGH"),
        "medium":   sum(1 for r in rows if r["risk_level"] == "MEDIUM"),
        "ok":       sum(1 for r in rows if r["risk_level"] == "OK"),
    }
    return {"seller_id": seller_id, "summary": summary, "risks": rows}


@router.get("/marketing-attribution")
async def marketing_attribution(
    seller_id: str = Query(...),
    days:      int = Query(30, ge=1, le=90),
    model:     str = Query("last_click", pattern="^(last_click|linear|shapley)$"),
    _scope:    str = Depends(enforce_seller_scope),
):
    sql = f"""
        SELECT
          utm_source, utm_medium, utm_campaign, attribution_date,
          attributed_sessions, attributed_conversions,
          ROUND(CAST(attributed_revenue AS FLOAT64), 2)  AS attributed_revenue,
          ROUND(CAST(ad_spend AS FLOAT64), 2)            AS ad_spend,
          ROUND(roas, 2)                                 AS roas,
          ROUND(shapley_weight, 4)                       AS shapley_weight,
          attribution_model
        FROM `{G}.marketing_attribution`
        WHERE seller_id = @seller_id
          AND attribution_model = @model
          AND attribution_date >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
        ORDER BY attributed_revenue DESC
    """
    rows = await bq.query(sql, {"seller_id": seller_id, "model": model, "days": days})
    return {
        "seller_id":        seller_id,
        "period_days":      days,
        "attribution_model": model,
        "data":             rows,
    }


@router.get("/anomalies")
async def anomalies(
    seller_id: str = Query(...),
    days:      int = Query(7, ge=1, le=30),
    _scope:    str = Depends(enforce_seller_scope),
):
    sql = f"""
        SELECT
          alert_type, sku, marketplace, metric_name,
          metric_value, baseline_value, deviation_pct,
          severity, alert_ts, is_resolved
        FROM `{G}.performance_alerts`
        WHERE seller_id = @seller_id
          AND DATE(alert_ts) >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
          AND is_resolved = FALSE
        ORDER BY severity DESC, alert_ts DESC
        LIMIT 50
    """
    rows = await bq.query(sql, {"seller_id": seller_id, "days": days})
    return {"seller_id": seller_id, "count": len(rows), "alerts": rows}
