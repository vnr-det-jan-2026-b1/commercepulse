import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchStorefront, fetchStock, fetchRecommendations, restockProduct, fetchPricingMargins, fetchRevenue, fetchInventoryAlerts, fetchAIBrief } from '../api/client';
import type { StorefrontData, StockItem, Recommendation, PricingMargin, RevenueRow, InventoryAlert, RestockHistoryEntry } from '../types';

// ── Restock history (display only — BigQuery is source of truth for stock) ─────
const HISTORY_KEY = 'nova-restock-history';

export function getRestockHistory(): RestockHistoryEntry[] {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); }
  catch { return []; }
}

export function clearRestockHistory() {
  localStorage.removeItem(HISTORY_KEY);
}

function saveHistory(productId: string, productName: string, qty: number) {
  try {
    const history: RestockHistoryEntry[] = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
    history.unshift({ product_id: productId, product_name: productName, quantity: qty, timestamp: new Date().toISOString() });
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  } catch { /* ignore */ }
}

// Mirrors the server-side CASE logic in RECOMMENDATIONS_SQL
function recomputeLabel(r: Recommendation): string {
  const s  = r.current_stock;
  const ds = r.demand_score ?? 0;
  const views = r.views ?? 0;
  const conv  = r.conversion_pct ?? 0;
  const purchases = r.purchases ?? 0;
  if (s <= 2 && ds >= 1)         return 'RESTOCK_URGENT';
  if (s <= 4 && ds >= 0.5)       return 'RESTOCK_SOON';
  if (views >= 5 && conv >= 20)  return 'INCREASE_PRICE';
  if (views >= 4 && conv < 5)    return 'DISCOUNT';
  if (views < 2 && purchases === 0) return 'DONT_RESTOCK';
  return 'MAINTAIN';
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
    queryFn: fetchStock,           // BigQuery is source of truth — no localStorage inflation
    refetchInterval: 10_000,       // refresh every 10 s to catch purchase events quickly
    staleTime: 0,
  });

export const useRecommendations = (days: number) =>
  useQuery<{ recommendations: Recommendation[]; ai_powered?: boolean }>({
    queryKey: ['recommendations', days],
    queryFn: () => fetchRecommendations(days),  // BigQuery is source of truth
    refetchInterval: 15_000,
    staleTime: 0,
  });

export const usePricingMargins = () =>
  useQuery<{ data: PricingMargin[] }>({
    queryKey: ['margins'],
    queryFn: fetchPricingMargins,
    refetchInterval: 60_000,
  });

export const useRevenue = (days: number) =>
  useQuery<{ data: RevenueRow[] }>({
    queryKey: ['revenue', days],
    queryFn: () => fetchRevenue(days),
    refetchInterval: 60_000,
  });

export const useInventoryAlerts = () =>
  useQuery<{ alerts: InventoryAlert[] }>({
    queryKey: ['inventoryAlerts'],
    queryFn: fetchInventoryAlerts,
    refetchInterval: 60_000,
  });

export const useAIBrief = (enabled: boolean) =>
  useQuery<{ recommendations: Record<string, unknown> }>({
    queryKey: ['ai-brief'],
    queryFn: fetchAIBrief,
    enabled,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

// ── Restock mutation ──────────────────────────────────────────────────────────

export const useRestock = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ productId, productName, quantity }: { productId: string; productName: string; quantity: number }) => {
      // 1. Save to restock history log (for display)
      saveHistory(productId, productName, quantity);

      // 2. Optimistically update stock cache immediately
      queryClient.setQueryData(['stock'], (old: { products: StockItem[] } | undefined) => {
        if (!old) return old;
        return {
          ...old,
          products: old.products.map((p: StockItem) =>
            p.product_id === productId
              ? { ...p, current_stock: p.current_stock + quantity }
              : p
          ),
        };
      });

      // 3. Update recommendations cache with recomputed label
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

      // 4. Call backend (writes to BigQuery + in-memory store)
      return restockProduct(productId, quantity);
    },
    onSuccess: () => {
      // Re-fetch after a short delay to get BigQuery-confirmed values
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['stock'] });
        queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      }, 3000);
    },
  });
};
