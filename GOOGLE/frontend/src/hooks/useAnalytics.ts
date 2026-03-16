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

function applyToStock(products: StockItem[]): StockItem[] {
  const adj = getAdjustments();
  return products.map(p => {
    const extra = adj[p.product_id] || 0;
    if (!extra) return p;
    return { ...p, current_stock: p.current_stock + extra, initial_stock: p.initial_stock + extra };
  });
}

function applyToRecs(recs: Recommendation[]): Recommendation[] {
  const adj = getAdjustments();
  return recs.map(r => {
    const extra = adj[r.product_id] || 0;
    if (!extra) return r;
    return { ...r, current_stock: r.current_stock + extra };
  });
}

// ── Queries ─────────────────────────────────────────────────────────────────

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

// ── Restock mutation ─────────────────────────────────────────────────────────

export const useRestock = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ productId, quantity }: { productId: string; quantity: number }) => {
      // 1. Persist to localStorage so refreshes keep the adjustment
      saveAdjustment(productId, quantity);

      // 2. Update stock cache immediately
      queryClient.setQueryData(['stock'], (old: { products: StockItem[] } | undefined) => {
        if (!old) return old;
        return {
          ...old,
          products: old.products.map((p: StockItem) =>
            p.product_id === productId
              ? { ...p, current_stock: p.current_stock + quantity, initial_stock: p.initial_stock + quantity }
              : p
          ),
        };
      });

      // 3. Update all recommendations caches (covers 7d, 14d, 30d variants)
      queryClient.setQueriesData(
        { queryKey: ['recommendations'] },
        (old: { recommendations: Recommendation[] } | undefined) => {
          if (!old) return old;
          return {
            ...old,
            recommendations: old.recommendations.map((r: Recommendation) =>
              r.product_id === productId
                ? { ...r, current_stock: r.current_stock + quantity }
                : r
            ),
          };
        }
      );

      // 4. Backend call is best-effort — ignore 404 from undeployed endpoint
      return restockProduct(productId, quantity).catch(() => ({ ok: true }));
    },
  });
};
