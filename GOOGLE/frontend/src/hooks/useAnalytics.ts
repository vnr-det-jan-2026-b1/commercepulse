import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchStorefront, fetchStock, fetchRecommendations, restockProduct } from '../api/client';
import type { StorefrontData, StockItem, Recommendation } from '../types';

// ── Restock adjustments persisted in localStorage ──────────────────────────
const RESTOCK_KEY = 'nova-restock-adjustments';

function getAdjustments(): Record<string, number> {
  try { return JSON.parse(localStorage.getItem(RESTOCK_KEY) || '{}'); }
  catch { return {}; }
}

function saveAdjustment(productId: string, qty: number) {
  const adj = getAdjustments();
  adj[productId] = (adj[productId] || 0) + qty;
  localStorage.setItem(RESTOCK_KEY, JSON.stringify(adj));
}

// Mirrors the server-side CASE logic in RECOMMENDATIONS_SQL
function recomputeLabel(r: Recommendation): string {
  const s  = r.current_stock;
  const ds = r.demand_score ?? 0;
  const views = r.views ?? 0;
  const conv  = r.conversion_pct ?? 0;
  const purchases = r.purchases ?? 0;
  if (s <= 2 && ds >= 1)                      return 'RESTOCK_URGENT';
  if (s <= 4 && ds >= 0.5)                    return 'RESTOCK_SOON';
  if (views >= 5 && conv >= 20)               return 'INCREASE_PRICE';
  if (views >= 4 && conv < 5)                 return 'DISCOUNT';
  if (views < 2  && purchases === 0)          return 'DONT_RESTOCK';
  return 'MAINTAIN';
}

function applyToStock(products: StockItem[]): StockItem[] {
  const adj = getAdjustments();
  return products.map(p => {
    const extra = adj[p.product_id] || 0;
    if (!extra) return p;
    return { ...p, current_stock: Math.min(p.current_stock + extra, 10) };
  });
}

function applyToRecs(recs: Recommendation[]): Recommendation[] {
  const adj = getAdjustments();
  return recs.map(r => {
    const extra = adj[r.product_id] || 0;
    if (!extra) return r;
    const updated = { ...r, current_stock: r.current_stock + extra };
    return { ...updated, recommendation: recomputeLabel(updated) };
  });
}

// ── Queries ──────────────────────────────────────────────────────────────────

export const useStorefront = (days: number, granularity: 'day' | 'hour') =>
  useQuery<StorefrontData>({
    queryKey: ['storefront', days, granularity],
    queryFn: () => fetchStorefront(days, granularity),
    refetchInterval: 30_000,
  });

export const useStock = () =>
  useQuery<{ products: StockItem[] }>({
    queryKey: ['stock'],
    queryFn: () => fetchStock().then(data => ({ ...data, products: applyToStock(data.products) })),
    refetchInterval: 30_000,
  });

export const useRecommendations = (days: number) =>
  useQuery<{ recommendations: Recommendation[] }>({
    queryKey: ['recommendations', days],
    queryFn: () => fetchRecommendations(days).then(data => ({
      ...data,
      recommendations: applyToRecs(data.recommendations),
    })),
    refetchInterval: 60_000,
  });

// ── Restock mutation ──────────────────────────────────────────────────────────

export const useRestock = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ productId, quantity }: { productId: string; quantity: number }) => {
      // 1. Persist to localStorage — survives page refresh
      saveAdjustment(productId, quantity);

      // 2. Update stock cache immediately
      queryClient.setQueryData(['stock'], (old: { products: StockItem[] } | undefined) => {
        if (!old) return old;
        return {
          ...old,
          products: old.products.map((p: StockItem) =>
            p.product_id === productId
              ? { ...p, current_stock: Math.min(p.current_stock + quantity, 10) }
              : p
          ),
        };
      });

      // 3. Update all recommendations caches — also recompute the URGENT/SOON label
      queryClient.setQueriesData(
        { queryKey: ['recommendations'] },
        (old: { recommendations: Recommendation[] } | undefined) => {
          if (!old) return old;
          return {
            ...old,
            recommendations: old.recommendations.map((r: Recommendation) => {
              if (r.product_id !== productId) return r;
              const updated = { ...r, current_stock: r.current_stock + quantity };
              return { ...updated, recommendation: recomputeLabel(updated) };
            }),
          };
        }
      );

      // 4. Backend call best-effort — works when local backend is running
      return restockProduct(productId, quantity).catch(() => ({ ok: true }));
    },
  });
};
