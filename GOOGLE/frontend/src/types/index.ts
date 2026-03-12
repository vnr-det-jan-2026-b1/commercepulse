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

export interface StorefrontData {
  seller_id: string;
  period_days: number;
  granularity: 'day' | 'hour';
  overview: StorefrontOverview;
  traffic: TrafficPoint[];
  products: ProductPerformance[];
  funnel: Funnel;
}
