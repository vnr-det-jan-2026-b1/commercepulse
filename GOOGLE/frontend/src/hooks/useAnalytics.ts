import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchStorefront, fetchStock, fetchRecommendations, restockProduct } from '../api/client';
import type { StorefrontData, StockItem, Recommendation } from '../types';

export const useStorefront = (days: number, granularity: 'day' | 'hour') =>
  useQuery<StorefrontData>({
    queryKey: ['storefront', days, granularity],
    queryFn: () => fetchStorefront(days, granularity),
    refetchInterval: 30_000,
  });

export const useStock = () =>
  useQuery<{ products: StockItem[] }>({
    queryKey: ['stock'],
    queryFn: fetchStock,
    refetchInterval: 30_000,
  });

export const useRecommendations = (days: number) =>
  useQuery<{ recommendations: Recommendation[] }>({
    queryKey: ['recommendations', days],
    queryFn: () => fetchRecommendations(days),
    refetchInterval: 60_000,
  });

export const useRestock = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ productId, quantity }: { productId: string; quantity: number }) =>
      restockProduct(productId, quantity),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stock'] });
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
    },
  });
};
