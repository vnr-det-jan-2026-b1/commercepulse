export interface StockItem {
  product_id: string;
  product_name: string;
  category: string;
  price: number;
  initial_stock: number;
  units_sold: number;
  current_stock: number;
}

export interface Recommendation {
  product_id: string;
  product_name: string;
  price: number;
  current_stock: number;
  demand_score: number;
  views: number;
  cart_adds: number;
  purchases: number;
  conversion_pct: number;
  recommendation: string;
}

export interface StorefrontOverview {
  total_visits: number;
  unique_sessions: number;
  product_views: number;
  cart_adds: number;
  orders: number;
  total_revenue: number;
  conversion_rate_pct: number;
}

export interface TrafficPoint {
  visit_date?: string;   // daily
  hour_label?: string;   // hourly
  visits: number;
  unique_sessions: number;
}

export interface ProductPerformance {
  product_id: string;
  product_name: string;
  views: number;
  cart_adds: number;
  purchases: number;
  revenue: number;
  conversion_pct: number;
}

export interface Funnel {
  page_views: number;
  product_views: number;
  cart_adds: number;
  purchases: number;
}

export interface PricingMargin {
  sku: string;
  marketplace: string;
  selling_price: number;
  cost_price: number;
  mrp: number;
  commission_pct: number;
  commission_amount: number;
  discount_percentage: number;
  net_margin: number;
  margin_pct: number;
  snapshot_date: string;
}

export interface RevenueRow {
  marketplace: string;
  gross_revenue: number;
  net_revenue: number;
  total_discount: number;
  total_orders: number;
  delivered_orders: number;
  cancelled_orders: number;
  returned_orders: number;
  avg_order_value: number;
}

export interface InventoryAlert {
  sku: string;
  marketplace: string;
  available_stock: number;
  reserved_stock: number;
  reorder_threshold: number;
  days_until_stockout: number;
  recommended_reorder_qty: number;
  risk_level: string;
  score_date: string;
}

export interface RestockHistoryEntry {
  product_id: string;
  product_name: string;
  quantity: number;
  timestamp: string;
}

export interface FunnelDataPoint {
  metric_date?: string;
  impressions: number;
  clicks: number;
  add_to_cart: number;
  purchases: number;
}

export interface RevenueDataPoint {
  order_date?: string;
  daily_revenue?: number;
}

export interface StorefrontData {
  seller_id: string;
  period_days: number;
  granularity: 'day' | 'hour';
  overview: StorefrontOverview;
  traffic: TrafficPoint[];
  products: ProductPerformance[];
  funnel: Funnel;
}
