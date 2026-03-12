import { useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell,
} from 'recharts';
import { useStorefront, useRecommendations, useStock } from '../hooks/useAnalytics';
import type { Recommendation, StockItem } from '../types';

type Tab = 'overview' | 'analytics' | 'recommendations' | 'products';
type FilterMode = '1d-hourly' | '7d' | '30d';

const TABS: { id: Tab; label: string }[] = [
  { id: 'overview',        label: 'Overview' },
  { id: 'analytics',      label: 'Analytics' },
  { id: 'recommendations', label: 'Recommendations' },
  { id: 'products',       label: 'Products' },
];

const FILTERS: { label: string; mode: FilterMode }[] = [
  { label: 'Today', mode: '1d-hourly' },
  { label: '7 days', mode: '7d' },
  { label: '30 days', mode: '30d' },
];

function modeToParams(mode: FilterMode): { days: number; granularity: 'day' | 'hour' } {
  if (mode === '1d-hourly') return { days: 1, granularity: 'hour' };
  if (mode === '7d')        return { days: 7, granularity: 'day' };
  return                           { days: 30, granularity: 'day' };
}

const FUNNEL_COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b'];

function KpiCard({ label, value, sub, color, icon }: {
  label: string; value: string | number; sub?: string; color: string; icon: string;
}) {
  return (
    <div className={`bg-white rounded-2xl p-5 shadow-sm border-l-4 ${color}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{label}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
          {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
        </div>
        <span className="text-2xl">{icon}</span>
      </div>
    </div>
  );
}

const REC_CONFIG: Record<string, { emoji: string; border: string; badge: string; badgeText: string }> = {
  RESTOCK_URGENT: { emoji: '🔴', border: 'border-red-400',    badge: 'bg-red-100 text-red-700',    badgeText: 'URGENT' },
  RESTOCK_SOON:   { emoji: '🟠', border: 'border-orange-400', badge: 'bg-orange-100 text-orange-700', badgeText: 'RESTOCK SOON' },
  INCREASE_PRICE: { emoji: '🟢', border: 'border-emerald-400', badge: 'bg-emerald-100 text-emerald-700', badgeText: 'RAISE PRICE' },
  DISCOUNT:       { emoji: '🔵', border: 'border-blue-400',   badge: 'bg-blue-100 text-blue-700',   badgeText: 'DISCOUNT' },
  DONT_RESTOCK:   { emoji: '⚪', border: 'border-gray-300',   badge: 'bg-gray-100 text-gray-500',   badgeText: 'SKIP' },
  MAINTAIN:       { emoji: '✅', border: 'border-teal-400',   badge: 'bg-teal-100 text-teal-700',   badgeText: 'MAINTAIN' },
};

const REC_ORDER = ['RESTOCK_URGENT', 'RESTOCK_SOON', 'INCREASE_PRICE', 'DISCOUNT', 'DONT_RESTOCK', 'MAINTAIN'];

const REC_MESSAGES: Record<string, string> = {
  RESTOCK_URGENT: 'Restock immediately — selling fast',
  RESTOCK_SOON:   'Restock within 3–5 days to avoid stockout',
  INCREASE_PRICE: 'High demand — consider raising price 10–15%',
  DISCOUNT:       'Low conversion — try a 10% discount to drive sales',
  DONT_RESTOCK:   'Low interest — skip restocking this cycle',
  MAINTAIN:       'Performing well — maintain current strategy',
};

function StockBar({ current, initial }: { current: number; initial: number }) {
  const pct = initial > 0 ? Math.max(0, Math.min(100, (current / initial) * 100)) : 0;
  const color = current === 0 ? 'bg-red-400' : current <= 3 ? 'bg-amber-400' : 'bg-emerald-400';
  return (
    <div className="w-20 bg-gray-100 rounded-full h-1.5">
      <div className={`${color} h-1.5 rounded-full`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function StockPill({ stock }: { stock: number }) {
  if (stock === 0) return <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-700">Out</span>;
  if (stock <= 3)  return <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-700">{stock} left</span>;
  return <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-700">{stock} in stock</span>;
}

export default function Dashboard() {
  const [tab, setTab]   = useState<Tab>('overview');
  const [mode, setMode] = useState<FilterMode>('7d');
  const [recDays, setRecDays] = useState(7);

  const { days, granularity } = modeToParams(mode);
  const { data, isLoading, error } = useStorefront(days, granularity);
  const { data: stockData }        = useStock();
  const { data: recData }          = useRecommendations(recDays);

  const overview = data?.overview;
  const funnel   = data?.funnel;
  const stock    = stockData?.products ?? [];
  const recs     = recData?.recommendations ?? [];

  const trafficData = (data?.traffic ?? []).map(p => ({
    label: p.hour_label ?? p.visit_date ?? '',
    visits: p.visits,
    unique: p.unique_sessions,
  }));

  const funnelData = funnel
    ? [
        { name: 'Page Views',    value: funnel.page_views },
        { name: 'Product Views', value: funnel.product_views },
        { name: 'Cart Adds',     value: funnel.cart_adds },
        { name: 'Purchases',     value: funnel.purchases },
      ]
    : [];

  const lowStockCount   = stock.filter(p => p.current_stock > 0 && p.current_stock <= 3).length;
  const outOfStockCount = stock.filter(p => p.current_stock === 0).length;

  const sortedRecs = [...recs].sort((a, b) =>
    REC_ORDER.indexOf(a.recommendation) - REC_ORDER.indexOf(b.recommendation)
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-indigo-600 to-violet-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">N</div>
            <span className="text-xl font-bold text-gray-900">Nova<span className="text-indigo-600">Admin</span></span>
            <span className="bg-indigo-100 text-indigo-600 text-xs font-semibold px-2 py-1 rounded-full">SELLER_001</span>
          </div>
          <span className="text-xs text-gray-400">Auto-refreshes every 30s</span>
        </div>

        {/* Tab bar */}
        <div className="max-w-7xl mx-auto px-6 flex gap-1 pb-0">
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-5 py-3 text-sm font-semibold border-b-2 transition-colors ${
                tab === t.id
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t.label}
              {t.id === 'recommendations' && recs.filter(r => r.recommendation === 'RESTOCK_URGENT').length > 0 && (
                <span className="ml-1.5 bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5">
                  {recs.filter(r => r.recommendation === 'RESTOCK_URGENT').length}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {isLoading && tab !== 'recommendations' && tab !== 'products' && (
          <div className="text-center py-20 text-gray-400">Loading analytics...</div>
        )}
        {error && (
          <div className="bg-red-50 text-red-600 rounded-xl p-4 text-sm">
            Failed to load data. Make sure the backend is running.
          </div>
        )}

        {/* ── OVERVIEW TAB ── */}
        {tab === 'overview' && data && (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard label="Total Visits"     value={(overview?.total_visits ?? 0).toLocaleString()}                      sub={`${overview?.unique_sessions ?? 0} unique sessions`} color="border-indigo-500" icon="👁️" />
              <KpiCard label="Revenue"          value={`Rs.${(overview?.total_revenue ?? 0).toLocaleString('en-IN')}`}      sub={`${overview?.orders ?? 0} orders`}                   color="border-emerald-500" icon="💰" />
              <KpiCard label="Cart Adds"        value={(overview?.cart_adds ?? 0).toLocaleString()}                         sub="items added to cart"                                  color="border-violet-500" icon="🛒" />
              <KpiCard label="Conversion Rate"  value={`${(overview?.conversion_rate_pct ?? 0).toFixed(1)}%`}               sub="sessions → purchase"                                  color="border-amber-500" icon="📈" />
            </div>

            {/* Stock health */}
            {stock.length > 0 && (
              <div className="bg-white rounded-2xl p-6 shadow-sm">
                <h2 className="text-base font-bold text-gray-800 mb-4">Inventory Health</h2>
                <div className="flex flex-wrap gap-4">
                  <div className="flex-1 min-w-40 bg-emerald-50 rounded-xl p-4 text-center">
                    <p className="text-3xl font-bold text-emerald-600">{stock.filter(p => p.current_stock > 3).length}</p>
                    <p className="text-xs text-emerald-700 font-semibold mt-1">Healthy Stock</p>
                  </div>
                  <div className="flex-1 min-w-40 bg-amber-50 rounded-xl p-4 text-center">
                    <p className="text-3xl font-bold text-amber-600">{lowStockCount}</p>
                    <p className="text-xs text-amber-700 font-semibold mt-1">Low Stock (≤3 units)</p>
                  </div>
                  <div className="flex-1 min-w-40 bg-red-50 rounded-xl p-4 text-center">
                    <p className="text-3xl font-bold text-red-600">{outOfStockCount}</p>
                    <p className="text-xs text-red-700 font-semibold mt-1">Out of Stock</p>
                  </div>
                  <div className="flex-1 min-w-40 bg-indigo-50 rounded-xl p-4 text-center">
                    <p className="text-3xl font-bold text-indigo-600">{stock.reduce((s, p) => s + p.units_sold, 0)}</p>
                    <p className="text-xs text-indigo-700 font-semibold mt-1">Total Units Sold</p>
                  </div>
                </div>
              </div>
            )}

            {/* Mini top products */}
            <div className="bg-white rounded-2xl p-6 shadow-sm">
              <h2 className="text-base font-bold text-gray-800 mb-4">Top Products by Revenue</h2>
              {data.products.length === 0 ? (
                <p className="text-gray-400 text-sm text-center py-8">No product data yet.</p>
              ) : (
                <div className="space-y-3">
                  {data.products.slice(0, 5).map((p) => (
                    <div key={p.product_id} className="flex items-center gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-gray-900 truncate">{p.product_name}</p>
                        <p className="text-xs text-gray-400">{p.views} views · {p.purchases} purchases</p>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <p className="text-sm font-bold text-gray-900">Rs.{p.revenue.toLocaleString('en-IN')}</p>
                        <p className="text-xs text-emerald-600">{p.conversion_pct ?? 0}% conv.</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {/* ── ANALYTICS TAB ── */}
        {tab === 'analytics' && (
          <>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900">Traffic & Funnel</h2>
              <div className="flex gap-2">
                {FILTERS.map(f => (
                  <button
                    key={f.mode}
                    onClick={() => setMode(f.mode)}
                    className={`px-4 py-1.5 rounded-full text-sm font-semibold transition-colors ${
                      mode === f.mode ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </div>

            {data && (
              <>
                <div className="bg-white rounded-2xl p-6 shadow-sm">
                  <h3 className="text-sm font-bold text-gray-700 mb-4">
                    {granularity === 'hour' ? 'Hourly Traffic (Today)' : `Daily Traffic (${days} days)`}
                  </h3>
                  {trafficData.length === 0 ? (
                    <p className="text-gray-400 text-sm text-center py-8">No traffic data yet.</p>
                  ) : (
                    <ResponsiveContainer width="100%" height={240}>
                      <LineChart data={trafficData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                        <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                        <Tooltip />
                        <Line type="monotone" dataKey="visits" stroke="#6366f1" strokeWidth={2} dot={granularity === 'hour'} name="Visits" />
                        <Line type="monotone" dataKey="unique" stroke="#8b5cf6" strokeWidth={2} dot={granularity === 'hour'} name="Sessions" />
                      </LineChart>
                    </ResponsiveContainer>
                  )}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="bg-white rounded-2xl p-6 shadow-sm">
                    <h3 className="text-sm font-bold text-gray-700 mb-4">Conversion Funnel</h3>
                    {funnelData.every(f => f.value === 0) ? (
                      <p className="text-gray-400 text-sm text-center py-8">No funnel data yet.</p>
                    ) : (
                      <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={funnelData} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                          <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
                          <YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 11 }} />
                          <Tooltip />
                          <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                            {funnelData.map((_, i) => <Cell key={i} fill={FUNNEL_COLORS[i]} />)}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    )}
                  </div>

                  <div className="bg-white rounded-2xl p-6 shadow-sm">
                    <h3 className="text-sm font-bold text-gray-700 mb-4">Key Metrics</h3>
                    <div className="space-y-4">
                      {[
                        { label: 'Total Visits',    value: (overview?.total_visits ?? 0).toLocaleString(),                     bar: null },
                        { label: 'Unique Sessions', value: (overview?.unique_sessions ?? 0).toLocaleString(),                   bar: null },
                        { label: 'Product Views',   value: (overview?.product_views ?? 0).toLocaleString(),                    bar: null },
                        { label: 'Cart Adds',       value: (overview?.cart_adds ?? 0).toLocaleString(),                        bar: null },
                        { label: 'Orders',          value: (overview?.orders ?? 0).toLocaleString(),                           bar: null },
                        { label: 'Revenue',         value: `Rs.${(overview?.total_revenue ?? 0).toLocaleString('en-IN')}`,     bar: null },
                      ].map(m => (
                        <div key={m.label} className="flex items-center justify-between text-sm">
                          <span className="text-gray-500">{m.label}</span>
                          <span className="font-semibold text-gray-900">{m.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </>
            )}
          </>
        )}

        {/* ── RECOMMENDATIONS TAB ── */}
        {tab === 'recommendations' && (
          <>
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-gray-900">AI Recommendations</h2>
                <p className="text-sm text-gray-500 mt-0.5">Demand-based insights for each product</p>
              </div>
              <div className="flex gap-2">
                {[7, 14, 30].map(d => (
                  <button
                    key={d}
                    onClick={() => setRecDays(d)}
                    className={`px-4 py-1.5 rounded-full text-sm font-semibold transition-colors ${
                      recDays === d ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {d}d
                  </button>
                ))}
              </div>
            </div>

            {sortedRecs.length === 0 ? (
              <div className="text-center py-20 text-gray-400">No recommendation data yet. Drive some traffic to the storefront first.</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {sortedRecs.map((rec: Recommendation) => {
                  const cfg = REC_CONFIG[rec.recommendation] ?? REC_CONFIG['MAINTAIN'];
                  return (
                    <div key={rec.product_id} className={`bg-white rounded-2xl p-5 shadow-sm border-l-4 ${cfg.border}`}>
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${cfg.badge}`}>
                              {cfg.emoji} {cfg.badgeText}
                            </span>
                          </div>
                          <p className="text-sm font-bold text-gray-900 truncate">{rec.product_name}</p>
                          <p className="text-xs text-gray-500 mt-1">{REC_MESSAGES[rec.recommendation]}</p>
                        </div>
                        <div className="text-right flex-shrink-0">
                          <p className="text-lg font-extrabold text-gray-900">{(rec.demand_score ?? 0).toFixed(1)}</p>
                          <p className="text-xs text-gray-400">demand</p>
                        </div>
                      </div>

                      <div className="mt-4 grid grid-cols-4 gap-2 text-center">
                        <div className="bg-gray-50 rounded-xl p-2">
                          <p className="text-sm font-bold text-gray-800">{rec.views}</p>
                          <p className="text-xs text-gray-400">views</p>
                        </div>
                        <div className="bg-gray-50 rounded-xl p-2">
                          <p className="text-sm font-bold text-gray-800">{rec.cart_adds}</p>
                          <p className="text-xs text-gray-400">cart</p>
                        </div>
                        <div className="bg-gray-50 rounded-xl p-2">
                          <p className="text-sm font-bold text-gray-800">{rec.purchases}</p>
                          <p className="text-xs text-gray-400">sold</p>
                        </div>
                        <div className="bg-gray-50 rounded-xl p-2">
                          <p className="text-sm font-bold text-gray-800">{rec.current_stock}</p>
                          <p className="text-xs text-gray-400">stock</p>
                        </div>
                      </div>

                      <div className="mt-3 flex items-center gap-2">
                        <StockBar current={rec.current_stock} initial={10} />
                        <span className="text-xs text-gray-400">{rec.current_stock}/10 units</span>
                        <span className="ml-auto text-xs text-gray-400">{(rec.conversion_pct ?? 0).toFixed(1)}% conv.</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}

        {/* ── PRODUCTS TAB ── */}
        {tab === 'products' && (
          <>
            <h2 className="text-lg font-bold text-gray-900">Product Inventory</h2>

            {stock.length === 0 ? (
              <div className="text-center py-20 text-gray-400">No stock data yet.</div>
            ) : (
              <div className="bg-white rounded-2xl shadow-sm overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-400 text-xs uppercase tracking-wider border-b">
                      <th className="px-6 py-4 font-semibold">Product</th>
                      <th className="px-6 py-4 font-semibold">Category</th>
                      <th className="px-6 py-4 font-semibold text-right">Price</th>
                      <th className="px-6 py-4 font-semibold text-right">Sold</th>
                      <th className="px-6 py-4 font-semibold text-center">Stock Level</th>
                      <th className="px-6 py-4 font-semibold text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {stock
                      .slice()
                      .sort((a: StockItem, b: StockItem) => a.current_stock - b.current_stock)
                      .map((p: StockItem) => (
                        <tr key={p.product_id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 font-semibold text-gray-900">{p.product_name}</td>
                          <td className="px-6 py-4 text-gray-500 text-xs">{p.category}</td>
                          <td className="px-6 py-4 text-right text-gray-700">Rs.{p.price.toLocaleString('en-IN')}</td>
                          <td className="px-6 py-4 text-right text-gray-700">{p.units_sold}</td>
                          <td className="px-6 py-4">
                            <div className="flex flex-col items-center gap-1">
                              <StockBar current={p.current_stock} initial={p.initial_stock} />
                              <span className="text-xs text-gray-400">{p.current_stock}/{p.initial_stock}</span>
                            </div>
                          </td>
                          <td className="px-6 py-4 text-center">
                            <StockPill stock={p.current_stock} />
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Also show product performance table if storefront data available */}
            {data && data.products.length > 0 && (
              <>
                <h2 className="text-lg font-bold text-gray-900 pt-4">Performance Metrics</h2>
                <div className="bg-white rounded-2xl shadow-sm overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-gray-400 text-xs uppercase tracking-wider border-b">
                        <th className="px-6 py-4 font-semibold">Product</th>
                        <th className="px-6 py-4 font-semibold text-right">Views</th>
                        <th className="px-6 py-4 font-semibold text-right">Cart Adds</th>
                        <th className="px-6 py-4 font-semibold text-right">Purchases</th>
                        <th className="px-6 py-4 font-semibold text-right">Revenue</th>
                        <th className="px-6 py-4 font-semibold text-right">Conv. %</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {data.products.map((p) => (
                        <tr key={p.product_id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 font-medium text-gray-900">{p.product_name}</td>
                          <td className="px-6 py-4 text-right text-gray-600">{p.views}</td>
                          <td className="px-6 py-4 text-right text-gray-600">{p.cart_adds}</td>
                          <td className="px-6 py-4 text-right text-gray-600">{p.purchases}</td>
                          <td className="px-6 py-4 text-right font-semibold text-gray-900">Rs.{p.revenue.toLocaleString('en-IN')}</td>
                          <td className="px-6 py-4 text-right">
                            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                              (p.conversion_pct ?? 0) >= 5  ? 'bg-emerald-100 text-emerald-700' :
                              (p.conversion_pct ?? 0) >= 1  ? 'bg-amber-100 text-amber-700' :
                                                              'bg-gray-100 text-gray-500'
                            }`}>
                              {p.conversion_pct ?? 0}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
