import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-Seller-Id': import.meta.env.VITE_SELLER_ID,
  },
});

const sellerId = import.meta.env.VITE_SELLER_ID;

export const fetchStorefront = (days: number, granularity: 'day' | 'hour') =>
  api.get('/v1/analytics/storefront', { params: { seller_id: sellerId, days, granularity } }).then(r => r.data);

export const fetchStock = () =>
  api.get('/v1/analytics/stock', { params: { seller_id: sellerId } }).then(r => r.data);

export const fetchRecommendations = (days: number) =>
  api.get('/v1/analytics/recommendations', { params: { seller_id: sellerId, days } }).then(r => r.data);

export const restockProduct = (productId: string, quantity: number) =>
  api.post('/v1/analytics/stock/restock', { seller_id: sellerId, product_id: productId, quantity }).then(r => r.data);

export const fetchPricingMargins = () =>
  api.get('/v1/analytics/pricing/margins', { params: { seller_id: sellerId } }).then(r => r.data);

export const fetchRevenue = (days: number) =>
  api.get('/v1/analytics/revenue', { params: { seller_id: sellerId, days } }).then(r => r.data);

export const fetchInventoryAlerts = () =>
  api.get('/v1/analytics/inventory/alerts', { params: { seller_id: sellerId } }).then(r => r.data);

export const fetchAIBrief = () =>
  api.post(`/v1/ai/recommendations`, null, { params: { seller_id: sellerId } }).then(r => r.data);
