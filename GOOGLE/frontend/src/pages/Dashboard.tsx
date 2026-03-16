import { useState, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell,
} from 'recharts';
import { useStorefront, useRecommendations, useStock, useRestock } from '../hooks/useAnalytics';
import type { Recommendation, StockItem } from '../types';

type Tab = 'overview' | 'analytics' | 'recommendations' | 'inventory' | 'products';
type FilterMode = '1d-hourly' | '7d' | '30d';

function modeToParams(mode: FilterMode): { days: number; granularity: 'day' | 'hour' } {
  if (mode === '1d-hourly') return { days: 1, granularity: 'hour' };
  if (mode === '7d')        return { days: 7, granularity: 'day' };
  return                           { days: 30, granularity: 'day' };
}

const REC_ORDER = ['RESTOCK_URGENT', 'RESTOCK_SOON', 'INCREASE_PRICE', 'DISCOUNT', 'DONT_RESTOCK', 'MAINTAIN'];

const REC_META: Record<string, { dot: string; label: string; msg: string }> = {
  RESTOCK_URGENT: { dot: 'var(--danger)', label: 'URGENT',        msg: 'Restock immediately — selling fast' },
  RESTOCK_SOON:   { dot: 'var(--amber)', label: 'RESTOCK SOON',  msg: 'Restock within 3–5 days to avoid stockout' },
  INCREASE_PRICE: { dot: 'var(--accent)', label: 'RAISE PRICE',  msg: 'High demand — consider raising price 10–15%' },
  DISCOUNT:       { dot: 'var(--text-secondary)', label: 'DISCOUNT', msg: 'Low conversion — try a 10% discount' },
  DONT_RESTOCK:   { dot: 'var(--text-secondary)', label: 'SKIP',  msg: 'Low interest — skip restocking this cycle' },
  MAINTAIN:       { dot: 'var(--accent)', label: 'OK',           msg: 'Performing well — maintain current strategy' },
};

// ── Icons ──────────────────────────────────────────────────────────────
function IconOverview()   { return <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>; }
function IconAnalytics()  { return <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>; }
function IconRecs()       { return <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/></svg>; }
function IconInventory()  { return <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"/></svg>; }
function IconProducts()   { return <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>; }

const NAV_ITEMS: { id: Tab; label: string; Icon: () => JSX.Element }[] = [
  { id: 'overview',        label: 'Overview',        Icon: IconOverview },
  { id: 'analytics',       label: 'Analytics',       Icon: IconAnalytics },
  { id: 'recommendations', label: 'Recommendations', Icon: IconRecs },
  { id: 'inventory',       label: 'Stock Room',      Icon: IconInventory },
  { id: 'products',        label: 'Products',        Icon: IconProducts },
];

// ── ThemeToggle ────────────────────────────────────────────────────────
function ThemeToggle() {
  const [theme, setTheme] = useState<string>(() => localStorage.getItem('nova-theme') ?? 'dark');
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('nova-theme', theme);
  }, [theme]);
  return (
    <button
      onClick={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
      style={{ background: 'none', border: '1px solid var(--border)', borderRadius: '8px', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: 'var(--text-secondary)', fontSize: '15px', flexShrink: 0 }}
      title="Toggle theme"
    >
      {theme === 'dark' ? '☀' : '☾'}
    </button>
  );
}

// ── StockBar ───────────────────────────────────────────────────────────
function StockBar({ current, initial }: { current: number; initial: number }) {
  const pct = initial > 0 ? Math.max(0, Math.min(100, (current / initial) * 100)) : 0;
  const color = current === 0 ? 'var(--danger)' : current <= 3 ? 'var(--amber)' : 'var(--accent)';
  return (
    <div style={{ width: '72px', background: 'var(--raised)', borderRadius: '4px', height: '4px' }}>
      <div style={{ background: color, height: '4px', borderRadius: '4px', width: `${pct}%`, transition: 'width 400ms ease' }} />
    </div>
  );
}

// ── KpiCard (Verbal-style) ─────────────────────────────────────────────
function KpiCard({ label, value, sub, upward }: { label: string; value: string; sub?: string; upward?: boolean | null }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px 22px' }}>
      <p style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-primary)', margin: '0 0 10px' }}>{label}</p>
      <p style={{ fontSize: '2.4rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0, lineHeight: 1, letterSpacing: '-0.04em' }}>{value}</p>
      {sub && upward !== undefined && upward !== null && (
        <p style={{ fontSize: '12px', fontWeight: 600, margin: '8px 0 0', color: upward ? 'var(--accent)' : 'var(--danger)', display: 'flex', alignItems: 'center', gap: '3px' }}>
          {upward ? '▲' : '▼'} {sub}
        </p>
      )}
      {sub && upward === undefined && (
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: '6px 0 0' }}>{sub}</p>
      )}
    </div>
  );
}

// ── Tooltip theme ──────────────────────────────────────────────────────
const tooltipStyle = { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '12px', color: 'var(--text-primary)' };

// ── Main Dashboard ─────────────────────────────────────────────────────
export default function Dashboard() {
  const [tab, setTab]   = useState<Tab>('overview');
  const [mode, setMode] = useState<FilterMode>('7d');
  const [recDays, setRecDays] = useState(7);
  const [restockQty, setRestockQty] = useState<Record<string, number>>({});
  const [restockDone, setRestockDone] = useState<Record<string, number>>({}); // productId → qty added
  const [restockDismissed, setRestockDismissed] = useState<Set<string>>(new Set());
  const restock = useRestock();

  const getQty = (productId: string, fallback = 10) =>
    restockQty[productId] ?? fallback;

  const handleRestock = (productId: string) => {
    const qty = getQty(productId);
    if (qty < 1) return;
    restock.mutate({ productId, quantity: qty }, {
      onSuccess: () => setRestockDone(prev => ({ ...prev, [productId]: qty })),
    });
  };
  const handleDismiss = (productId: string) => {
    setRestockDismissed(prev => new Set([...prev, productId]));
  };

  useEffect(() => {
    const t = localStorage.getItem('nova-theme') ?? 'dark';
    document.documentElement.dataset.theme = t;
  }, []);

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
    Visits: p.visits,
    Sessions: p.unique_sessions,
  }));

  const funnelData = funnel
    ? [
        { name: 'Page Views',    value: funnel.page_views },
        { name: 'Product Views', value: funnel.product_views },
        { name: 'Cart Adds',     value: funnel.cart_adds },
        { name: 'Purchases',     value: funnel.purchases },
      ]
    : [];

  const lowStockCount      = stock.filter(p => p.current_stock > 0 && p.current_stock <= 3).length;
  const outOfStockCount    = stock.filter(p => p.current_stock === 0).length;
  const urgentCount        = recs.filter(r => r.recommendation === 'RESTOCK_URGENT').length;
  const criticalStockItems = stock.filter(p => p.current_stock <= 3);
  const criticalStockCount = criticalStockItems.length;
  const activeRestockAlerts = criticalStockItems.filter(p => !restockDismissed.has(p.product_id));

  const sortedRecs = [...recs].sort((a, b) =>
    REC_ORDER.indexOf(a.recommendation) - REC_ORDER.indexOf(b.recommendation)
  );

  // grid lines color adapts to theme
  const gridColor = 'var(--border)';

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg)', fontFamily: 'inherit' }}>

      {/* ── SIDEBAR ── */}
      <aside style={{ width: '220px', flexShrink: 0, background: 'var(--sidebar-bg)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Logo */}
        <div style={{ padding: '22px 20px 20px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
            <div style={{ width: '30px', height: '30px', background: 'var(--accent)', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 800, fontSize: '13px', flexShrink: 0 }}>N</div>
            <span style={{ fontSize: '16px', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
              Nova<span style={{ color: 'var(--accent)' }}>Admin</span>
            </span>
          </div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', background: 'var(--accent-muted)', borderRadius: '6px', padding: '3px 8px' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent)', display: 'inline-block' }} />
            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent)' }}>SELLER_001</span>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: '12px 10px', display: 'flex', flexDirection: 'column', gap: '2px', overflowY: 'auto' }}>
          {NAV_ITEMS.map(({ id, label, Icon }) => {
            const active = tab === id;
            return (
              <button
                key={id}
                onClick={() => setTab(id)}
                style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '9px 12px', borderRadius: '8px', border: 'none', cursor: 'pointer', fontFamily: 'inherit', fontSize: '13px', fontWeight: active ? 600 : 500, width: '100%', textAlign: 'left', background: active ? 'var(--accent-muted)' : 'transparent', color: active ? 'var(--accent)' : 'var(--text-secondary)', position: 'relative' }}
                onMouseEnter={e => { if (!active) (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)'; }}
                onMouseLeave={e => { if (!active) (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)'; }}
              >
                <Icon />
                {label}
                {id === 'recommendations' && urgentCount > 0 && (
                  <span style={{ marginLeft: 'auto', background: 'var(--danger)', color: 'white', fontSize: '10px', fontWeight: 700, borderRadius: '10px', padding: '1px 6px' }}>{urgentCount}</span>
                )}
                {id === 'inventory' && criticalStockCount > 0 && (
                  <span style={{ marginLeft: 'auto', background: criticalStockCount > 0 ? 'var(--amber)' : 'transparent', color: 'white', fontSize: '10px', fontWeight: 700, borderRadius: '10px', padding: '1px 6px' }}>{criticalStockCount}</span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Bottom */}
        <div style={{ padding: '14px 16px', borderTop: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Auto-refresh 30s</span>
          <ThemeToggle />
        </div>
      </aside>

      {/* ── MAIN ── */}
      <main style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>

        {/* Page header */}
        <div style={{ padding: '28px 32px 0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.03em' }}>
              {NAV_ITEMS.find(n => n.id === tab)?.label}
            </h1>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '4px 0 0' }}>
              {tab === 'overview'        && 'Store performance at a glance'}
              {tab === 'analytics'       && 'Traffic and conversion funnel'}
              {tab === 'recommendations' && 'Demand-based product insights'}
              {tab === 'inventory'       && 'Stock levels and restock management'}
              {tab === 'products'        && 'Inventory and performance metrics'}
            </p>
          </div>
        </div>

        {/* Content */}
        <div style={{ padding: '24px 32px 40px', flex: 1 }}>
          {error && (
            <div style={{ background: 'var(--danger-muted)', border: '1px solid var(--danger)', borderRadius: '10px', padding: '12px 16px', fontSize: '13px', color: 'var(--danger)', marginBottom: '20px' }}>
              Failed to load data. Make sure the backend is running.
            </div>
          )}

          {/* ── OVERVIEW ── */}
          {tab === 'overview' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {isLoading ? (
                <div style={{ textAlign: 'center', paddingTop: '80px', color: 'var(--text-secondary)', fontSize: '14px' }}>Loading analytics…</div>
              ) : data ? (
                <>
                  {/* KPI row */}
                  <div className="stagger" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
                    <KpiCard label="Total Visits"    value={(overview?.total_visits ?? 0).toLocaleString()}                     sub={`${overview?.unique_sessions ?? 0} unique sessions`} />
                    <KpiCard label="Revenue"         value={`₹${((overview?.total_revenue ?? 0) / 1000).toFixed(1)}K`}          sub={`${overview?.orders ?? 0} orders`} />
                    <KpiCard label="Cart Adds"       value={(overview?.cart_adds ?? 0).toLocaleString()}                        sub="items added to cart" />
                    <KpiCard label="Conversion Rate" value={`${(overview?.conversion_rate_pct ?? 0).toFixed(1)}%`}               sub="sessions → purchase" upward={(overview?.conversion_rate_pct ?? 0) > 2} />
                  </div>

                  {/* Chart + Inventory Health row */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    {/* Traffic mini chart */}
                    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px 20px 14px' }}>
                      <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 16px' }}>Traffic Overview</p>
                      {trafficData.length === 0 ? (
                        <p style={{ color: 'var(--text-secondary)', fontSize: '13px', textAlign: 'center', padding: '32px 0' }}>No traffic data yet</p>
                      ) : (
                        <ResponsiveContainer width="100%" height={180}>
                          <LineChart data={trafficData}>
                            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                            <XAxis dataKey="label" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} allowDecimals={false} />
                            <Tooltip contentStyle={tooltipStyle} />
                            <Line type="monotone" dataKey="Visits" stroke="var(--accent)" strokeWidth={2} dot={false} />
                          </LineChart>
                        </ResponsiveContainer>
                      )}
                    </div>

                    {/* Inventory health */}
                    {stock.length > 0 && (
                      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px' }}>
                        <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 16px' }}>Inventory Health</p>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                          {[
                            { n: stock.filter(p => p.current_stock > 3).length, label: 'Healthy Stock', color: 'var(--accent)' },
                            { n: lowStockCount,   label: 'Low Stock',    color: 'var(--amber)' },
                            { n: outOfStockCount, label: 'Out of Stock', color: 'var(--danger)' },
                            { n: stock.reduce((s, p) => s + p.units_sold, 0), label: 'Units Sold', color: 'var(--text-primary)' },
                          ].map(({ n, label, color }) => (
                            <div key={label} style={{ background: 'var(--raised)', border: '1px solid var(--border)', borderRadius: '10px', padding: '14px 16px' }}>
                              <p style={{ fontSize: '1.8rem', fontWeight: 800, color, margin: 0, lineHeight: 1, letterSpacing: '-0.03em' }}>{n}</p>
                              <p style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', margin: '6px 0 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Top products */}
                  <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px' }}>
                    <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 16px' }}>Top Products by Revenue</p>
                    {data.products.length === 0 ? (
                      <p style={{ color: 'var(--text-secondary)', fontSize: '13px', textAlign: 'center', padding: '24px 0' }}>No product data yet</p>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
                        {data.products.slice(0, 5).map((p, i) => (
                          <div key={p.product_id} style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 0', borderBottom: i < 4 ? '1px solid var(--border)' : 'none' }}>
                            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-secondary)', width: '18px', textAlign: 'center', flexShrink: 0 }}>{i + 1}</span>
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.product_name}</p>
                              <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: '2px 0 0' }}>{p.views} views · {p.purchases} purchases</p>
                            </div>
                            <div style={{ textAlign: 'right', flexShrink: 0 }}>
                              <p style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>₹{p.revenue.toLocaleString('en-IN')}</p>
                              <p style={{ fontSize: '11px', fontWeight: 600, color: 'var(--accent)', margin: '2px 0 0' }}>{p.conversion_pct ?? 0}% conv.</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              ) : null}
            </div>
          )}

          {/* ── ANALYTICS ── */}
          {tab === 'analytics' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
                  {granularity === 'hour' ? 'Hourly traffic today' : `Daily traffic — last ${days} days`}
                </p>
                <div style={{ display: 'flex', gap: '6px' }}>
                  {([{ label: 'Today', mode: '1d-hourly' as FilterMode }, { label: '7 days', mode: '7d' as FilterMode }, { label: '30 days', mode: '30d' as FilterMode }]).map(f => (
                    <button
                      key={f.mode}
                      onClick={() => setMode(f.mode)}
                      style={{ padding: '6px 14px', borderRadius: '8px', fontSize: '12px', fontWeight: 600, border: '1px solid', cursor: 'pointer', fontFamily: 'inherit', background: mode === f.mode ? 'var(--accent)' : 'transparent', borderColor: mode === f.mode ? 'var(--accent)' : 'var(--border)', color: mode === f.mode ? 'white' : 'var(--text-secondary)' }}
                    >
                      {f.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Traffic chart */}
              <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px', padding: '22px 22px 14px' }}>
                <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 18px' }}>Visits & Sessions</p>
                {trafficData.length === 0 ? (
                  <p style={{ color: 'var(--text-secondary)', fontSize: '13px', textAlign: 'center', padding: '48px 0' }}>No traffic data yet.</p>
                ) : (
                  <ResponsiveContainer width="100%" height={260}>
                    <LineChart data={trafficData}>
                      <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                      <XAxis dataKey="label" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} allowDecimals={false} />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Line type="monotone" dataKey="Visits"   stroke="var(--accent)" strokeWidth={2.5} dot={granularity === 'hour'} name="Visits" />
                      <Line type="monotone" dataKey="Sessions" stroke="var(--text-secondary)" strokeWidth={1.5} dot={false} name="Sessions" strokeDasharray="4 2" />
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </div>

              {/* Funnel + Key Metrics */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px', padding: '22px' }}>
                  <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 18px' }}>Conversion Funnel</p>
                  {funnelData.every(f => f.value === 0) ? (
                    <p style={{ color: 'var(--text-secondary)', fontSize: '13px', textAlign: 'center', padding: '40px 0' }}>No funnel data yet.</p>
                  ) : (
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={funnelData} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                        <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} allowDecimals={false} />
                        <YAxis dataKey="name" type="category" width={90} tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
                        <Tooltip contentStyle={tooltipStyle} />
                        <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                          {funnelData.map((_, i) => (
                            <Cell key={i} fill={i === 0 ? 'var(--accent)' : i === 1 ? '#4ade80' : i === 2 ? '#86efac' : '#bbf7d0'} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </div>

                <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px', padding: '22px' }}>
                  <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 18px' }}>Key Metrics</p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
                    {[
                      { label: 'Total Visits',    value: (overview?.total_visits ?? 0).toLocaleString() },
                      { label: 'Unique Sessions', value: (overview?.unique_sessions ?? 0).toLocaleString() },
                      { label: 'Product Views',   value: (overview?.product_views ?? 0).toLocaleString() },
                      { label: 'Cart Adds',       value: (overview?.cart_adds ?? 0).toLocaleString() },
                      { label: 'Orders',          value: (overview?.orders ?? 0).toLocaleString() },
                      { label: 'Revenue',         value: `₹${(overview?.total_revenue ?? 0).toLocaleString('en-IN')}` },
                    ].map((m, i, arr) => (
                      <div key={m.label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '11px 0', borderBottom: i < arr.length - 1 ? '1px solid var(--border)' : 'none' }}>
                        <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{m.label}</span>
                        <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)' }}>{m.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── RECOMMENDATIONS ── */}
          {tab === 'recommendations' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

              {/* Low-stock restock alerts */}
              {activeRestockAlerts.length > 0 && (
                <div style={{ background: 'rgba(251,191,36,0.06)', border: '1px solid var(--amber)', borderRadius: '12px', padding: '16px 20px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <span style={{ color: 'var(--amber)', fontSize: '8px' }}>●</span>
                    <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--amber)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Restock Alerts — {activeRestockAlerts.length} product{activeRestockAlerts.length > 1 ? 's' : ''} critically low</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {activeRestockAlerts.map(p => (
                      <div key={p.product_id} style={{ display: 'flex', alignItems: 'center', gap: '12px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '10px', padding: '12px 16px' }}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <p style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.product_name}</p>
                          <p style={{ fontSize: '11px', color: p.current_stock === 0 ? 'var(--danger)' : 'var(--amber)', margin: 0, fontWeight: 600 }}>
                            {p.current_stock === 0 ? '● Out of stock' : `● Only ${p.current_stock} unit${p.current_stock === 1 ? '' : 's'} remaining`}
                          </p>
                        </div>
                        <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: 0, flexShrink: 0 }}>{p.category}</p>
                        {restockDone[p.product_id] ? (
                          <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--accent)', flexShrink: 0 }}>✓ +{restockDone[p.product_id]} units ordered</span>
                        ) : (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
                            <input
                              type="number" min={1} value={getQty(p.product_id)}
                              onChange={e => setRestockQty(prev => ({ ...prev, [p.product_id]: Math.max(1, parseInt(e.target.value) || 1) }))}
                              style={{ width: '56px', padding: '5px 8px', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--raised)', color: 'var(--text-primary)', fontSize: '12px', fontFamily: 'inherit', textAlign: 'center' }}
                            />
                            <button
                              onClick={() => handleRestock(p.product_id)}
                              disabled={restock.isPending}
                              style={{ padding: '6px 12px', borderRadius: '8px', fontSize: '12px', fontWeight: 700, border: 'none', cursor: 'pointer', background: 'var(--accent)', color: 'white', fontFamily: 'inherit', opacity: restock.isPending ? 0.6 : 1 }}
                            >
                              Restock
                            </button>
                            <button
                              onClick={() => handleDismiss(p.product_id)}
                              style={{ padding: '6px 10px', borderRadius: '8px', fontSize: '12px', fontWeight: 600, border: '1px solid var(--border)', cursor: 'pointer', background: 'transparent', color: 'var(--text-secondary)', fontFamily: 'inherit' }}
                            >
                              Dismiss
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>Demand-based insights per product</p>
                <div style={{ display: 'flex', gap: '6px' }}>
                  {[7, 14, 30].map(d => (
                    <button
                      key={d}
                      onClick={() => setRecDays(d)}
                      style={{ padding: '6px 14px', borderRadius: '8px', fontSize: '12px', fontWeight: 600, border: '1px solid', cursor: 'pointer', fontFamily: 'inherit', background: recDays === d ? 'var(--accent)' : 'transparent', borderColor: recDays === d ? 'var(--accent)' : 'var(--border)', color: recDays === d ? 'white' : 'var(--text-secondary)' }}
                    >
                      {d}d
                    </button>
                  ))}
                </div>
              </div>

              {sortedRecs.length === 0 ? (
                <div style={{ textAlign: 'center', paddingTop: '80px', color: 'var(--text-secondary)', fontSize: '14px' }}>
                  No recommendation data yet. Drive some traffic to NovaCart first.
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
                  {sortedRecs.map((rec: Recommendation) => {
                    const meta = REC_META[rec.recommendation] ?? REC_META['MAINTAIN'];
                    return (
                      <div key={rec.product_id} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px', padding: '18px 20px' }}>
                        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px', marginBottom: '12px' }}>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                              <span style={{ color: meta.dot, fontSize: '8px' }}>●</span>
                              <span style={{ fontSize: '10px', fontWeight: 700, color: meta.dot, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{meta.label}</span>
                            </div>
                            <p style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{rec.product_name}</p>
                            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>{meta.msg}</p>
                          </div>
                          <div style={{ textAlign: 'right', flexShrink: 0 }}>
                            <p style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0, lineHeight: 1, letterSpacing: '-0.03em' }}>{(rec.demand_score ?? 0).toFixed(1)}</p>
                            <p style={{ fontSize: '10px', color: 'var(--text-secondary)', margin: '3px 0 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>demand</p>
                          </div>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px', marginBottom: '12px' }}>
                          {[
                            { v: rec.views,     l: 'views' },
                            { v: rec.cart_adds, l: 'cart' },
                            { v: rec.purchases, l: 'sold' },
                            { v: rec.current_stock, l: 'stock' },
                          ].map(({ v, l }) => (
                            <div key={l} style={{ background: 'var(--raised)', borderRadius: '8px', padding: '8px', textAlign: 'center' }}>
                              <p style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>{v}</p>
                              <p style={{ fontSize: '10px', color: 'var(--text-secondary)', margin: '2px 0 0', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{l}</p>
                            </div>
                          ))}
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <StockBar current={rec.current_stock} initial={10} />
                          <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{rec.current_stock}/10 units</span>
                          <span style={{ marginLeft: 'auto', fontSize: '11px', color: 'var(--text-secondary)' }}>{(rec.conversion_pct ?? 0).toFixed(1)}% conv.</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* ── INVENTORY / STOCK ROOM ── */}
          {tab === 'inventory' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

              {/* Summary KPIs */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
                {[
                  { n: stock.length,                                             label: 'Total Products',  color: 'var(--text-primary)' },
                  { n: stock.filter(p => p.current_stock > 3).length,           label: 'Healthy Stock',   color: 'var(--accent)' },
                  { n: lowStockCount,                                            label: 'Low Stock (≤3)',  color: 'var(--amber)' },
                  { n: outOfStockCount,                                          label: 'Out of Stock',    color: 'var(--danger)' },
                ].map(({ n, label, color }) => (
                  <div key={label} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px', padding: '18px 20px' }}>
                    <p style={{ fontSize: '2.2rem', fontWeight: 800, color, margin: 0, lineHeight: 1, letterSpacing: '-0.04em' }}>{n}</p>
                    <p style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', margin: '8px 0 0', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</p>
                  </div>
                ))}
              </div>

              {/* Critical: needs restocking */}
              {criticalStockItems.length > 0 && (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <span style={{ color: 'var(--amber)', fontSize: '8px' }}>●</span>
                    <p style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>Needs Restocking</p>
                    <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>— products at 3 units or below</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
                    {criticalStockItems.map(p => {
                      const isOut = p.current_stock === 0;
                      const ordered = !!restockDone[p.product_id];
                      return (
                        <div key={p.product_id} style={{ background: 'var(--surface)', border: `1px solid ${isOut ? 'var(--danger)' : 'var(--amber)'}`, borderRadius: '12px', padding: '18px 20px' }}>
                          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px', marginBottom: '14px' }}>
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                                <span style={{ fontSize: '7px', color: isOut ? 'var(--danger)' : 'var(--amber)' }}>●</span>
                                <span style={{ fontSize: '10px', fontWeight: 700, color: isOut ? 'var(--danger)' : 'var(--amber)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                                  {isOut ? 'Out of Stock' : 'Low Stock'}
                                </span>
                              </div>
                              <p style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.product_name}</p>
                              <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: 0 }}>{p.category} · ₹{p.price.toLocaleString('en-IN')}</p>
                            </div>
                            <div style={{ textAlign: 'right', flexShrink: 0 }}>
                              <p style={{ fontSize: '2rem', fontWeight: 800, color: isOut ? 'var(--danger)' : 'var(--amber)', margin: 0, lineHeight: 1, letterSpacing: '-0.04em' }}>{p.current_stock}</p>
                              <p style={{ fontSize: '10px', color: 'var(--text-secondary)', margin: '3px 0 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>units left</p>
                            </div>
                          </div>

                          <div style={{ marginBottom: '14px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                              <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Stock level</span>
                              <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{p.current_stock}/{p.initial_stock} units</span>
                            </div>
                            <div style={{ width: '100%', background: 'var(--raised)', borderRadius: '4px', height: '6px' }}>
                              <div style={{
                                background: isOut ? 'var(--danger)' : 'var(--amber)',
                                height: '6px', borderRadius: '4px',
                                width: `${p.initial_stock > 0 ? (p.current_stock / p.initial_stock) * 100 : 0}%`,
                                transition: 'width 400ms ease'
                              }} />
                            </div>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{p.units_sold} sold</span>
                            <span style={{ marginLeft: 'auto' }} />
                            {ordered ? (
                              <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--accent)' }}>✓ +{restockDone[p.product_id]} units ordered</span>
                            ) : (
                              <>
                                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Restock qty:</span>
                                <input
                                  type="number" min={1} value={getQty(p.product_id)}
                                  onChange={e => setRestockQty(prev => ({ ...prev, [p.product_id]: Math.max(1, parseInt(e.target.value) || 1) }))}
                                  style={{ width: '64px', padding: '6px 8px', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--raised)', color: 'var(--text-primary)', fontSize: '13px', fontFamily: 'inherit', textAlign: 'center' }}
                                />
                                <button
                                  onClick={() => handleRestock(p.product_id)}
                                  disabled={restock.isPending}
                                  style={{ padding: '7px 16px', borderRadius: '8px', fontSize: '12px', fontWeight: 700, border: 'none', cursor: 'pointer', background: 'var(--accent)', color: 'white', fontFamily: 'inherit', opacity: restock.isPending ? 0.6 : 1 }}
                                >
                                  Confirm Restock
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {criticalStockItems.length === 0 && (
                <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px', padding: '32px', textAlign: 'center' }}>
                  <p style={{ fontSize: '14px', fontWeight: 600, color: 'var(--accent)', margin: '0 0 4px' }}>✓ All products healthy</p>
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>No products are critically low on stock.</p>
                </div>
              )}

              {/* Full stock table */}
              {stock.length > 0 && (
                <div>
                  <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 12px' }}>All Products — Stock Overview</p>
                  <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px', overflow: 'hidden' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid var(--border)' }}>
                          {['Product', 'Category', 'Price', 'Sold', 'Stock Level', 'Status', 'Action'].map(h => (
                            <th key={h} style={{ padding: '12px 16px', textAlign: h === 'Product' ? 'left' : 'center', fontSize: '10px', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', whiteSpace: 'nowrap' }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {stock.slice().sort((a: StockItem, b: StockItem) => a.current_stock - b.current_stock).map((p: StockItem, i: number) => {
                          const isCritical = p.current_stock <= 3;
                          const isOut = p.current_stock === 0;
                          const ordered = !!restockDone[p.product_id];
                          return (
                            <tr key={p.product_id} style={{ borderBottom: '1px solid var(--border)', background: i % 2 === 1 ? 'var(--raised)' : 'transparent' }}>
                              <td style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-primary)' }}>{p.product_name}</td>
                              <td style={{ padding: '12px 16px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{p.category}</td>
                              <td style={{ padding: '12px 16px', textAlign: 'center', color: 'var(--text-primary)', fontWeight: 500 }}>₹{p.price.toLocaleString('en-IN')}</td>
                              <td style={{ padding: '12px 16px', textAlign: 'center', color: 'var(--text-secondary)' }}>{p.units_sold}</td>
                              <td style={{ padding: '12px 16px' }}>
                                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                                  <StockBar current={p.current_stock} initial={p.initial_stock} />
                                  <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>{p.current_stock}/{p.initial_stock}</span>
                                </div>
                              </td>
                              <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                                <span style={{ fontSize: '12px', fontWeight: 600, color: isOut ? 'var(--danger)' : isCritical ? 'var(--amber)' : 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}>
                                  <span style={{ fontSize: '7px' }}>●</span>
                                  {isOut ? 'Out' : isCritical ? 'Low' : 'OK'}
                                </span>
                              </td>
                              <td style={{ padding: '10px 16px', textAlign: 'center' }}>
                                {isCritical ? (
                                  ordered ? (
                                    <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent)' }}>✓ +{restockDone[p.product_id]}</span>
                                  ) : (
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', justifyContent: 'center' }}>
                                      <input
                                        type="number" min={1} value={getQty(p.product_id)}
                                        onChange={e => setRestockQty(prev => ({ ...prev, [p.product_id]: Math.max(1, parseInt(e.target.value) || 1) }))}
                                        style={{ width: '48px', padding: '4px 6px', borderRadius: '5px', border: '1px solid var(--border)', background: 'var(--raised)', color: 'var(--text-primary)', fontSize: '11px', fontFamily: 'inherit', textAlign: 'center' }}
                                      />
                                      <button
                                        onClick={() => handleRestock(p.product_id)}
                                        disabled={restock.isPending}
                                        style={{ padding: '4px 10px', borderRadius: '6px', fontSize: '11px', fontWeight: 700, border: 'none', cursor: 'pointer', background: 'var(--accent)', color: 'white', fontFamily: 'inherit', opacity: restock.isPending ? 0.6 : 1 }}
                                      >
                                        +Add
                                      </button>
                                    </div>
                                  )
                                ) : (
                                  <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>—</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {stock.length === 0 && criticalStockItems.length === 0 && (
                <div style={{ textAlign: 'center', paddingTop: '60px', color: 'var(--text-secondary)', fontSize: '14px' }}>No stock data yet.</div>
              )}
            </div>
          )}

          {/* ── PRODUCTS ── */}
          {tab === 'products' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {/* Inventory table */}
              <div>
                <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 12px' }}>Inventory Levels</p>
                {stock.length === 0 ? (
                  <div style={{ textAlign: 'center', paddingTop: '60px', color: 'var(--text-secondary)', fontSize: '14px' }}>No stock data yet.</div>
                ) : (
                  <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px', overflow: 'hidden' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid var(--border)' }}>
                          {['Product', 'Category', 'Price', 'Sold', 'Stock Level', 'Status'].map(h => (
                            <th key={h} style={{ padding: '12px 16px', textAlign: h === 'Product' ? 'left' : 'right', fontSize: '10px', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', whiteSpace: 'nowrap' }}>
                              {h === 'Stock Level' || h === 'Status' ? <span style={{ display: 'block', textAlign: 'center' }}>{h}</span> : h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {stock.slice().sort((a: StockItem, b: StockItem) => a.current_stock - b.current_stock).map((p: StockItem, i: number) => (
                          <tr key={p.product_id} style={{ borderBottom: '1px solid var(--border)', background: i % 2 === 1 ? 'var(--raised)' : 'transparent' }}>
                            <td style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-primary)' }}>{p.product_name}</td>
                            <td style={{ padding: '12px 16px', textAlign: 'right', color: 'var(--text-secondary)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{p.category}</td>
                            <td style={{ padding: '12px 16px', textAlign: 'right', color: 'var(--text-primary)', fontWeight: 500 }}>₹{p.price.toLocaleString('en-IN')}</td>
                            <td style={{ padding: '12px 16px', textAlign: 'right', color: 'var(--text-secondary)' }}>{p.units_sold}</td>
                            <td style={{ padding: '12px 16px' }}>
                              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                                <StockBar current={p.current_stock} initial={p.initial_stock} />
                                <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>{p.current_stock}/{p.initial_stock}</span>
                              </div>
                            </td>
                            <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                              <span style={{ fontSize: '12px', fontWeight: 600, color: p.current_stock === 0 ? 'var(--danger)' : p.current_stock <= 3 ? 'var(--amber)' : 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}>
                                <span style={{ fontSize: '7px' }}>●</span>
                                {p.current_stock === 0 ? 'Out' : p.current_stock <= 3 ? 'Low' : 'OK'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Performance table */}
              {data && data.products.length > 0 && (
                <div>
                  <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 12px' }}>Performance Metrics</p>
                  <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px', overflow: 'hidden' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid var(--border)' }}>
                          {['Product', 'Views', 'Cart Adds', 'Purchases', 'Revenue', 'Conv. %'].map(h => (
                            <th key={h} style={{ padding: '12px 16px', textAlign: h === 'Product' ? 'left' : 'right', fontSize: '10px', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {data.products.map((p, i) => (
                          <tr key={p.product_id} style={{ borderBottom: '1px solid var(--border)', background: i % 2 === 1 ? 'var(--raised)' : 'transparent' }}>
                            <td style={{ padding: '12px 16px', fontWeight: 500, color: 'var(--text-primary)' }}>{p.product_name}</td>
                            <td style={{ padding: '12px 16px', textAlign: 'right', color: 'var(--text-secondary)' }}>{p.views}</td>
                            <td style={{ padding: '12px 16px', textAlign: 'right', color: 'var(--text-secondary)' }}>{p.cart_adds}</td>
                            <td style={{ padding: '12px 16px', textAlign: 'right', color: 'var(--text-secondary)' }}>{p.purchases}</td>
                            <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 700, color: 'var(--text-primary)' }}>₹{p.revenue.toLocaleString('en-IN')}</td>
                            <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 600, color: (p.conversion_pct ?? 0) >= 5 ? 'var(--accent)' : (p.conversion_pct ?? 0) >= 1 ? 'var(--amber)' : 'var(--text-secondary)' }}>
                              {p.conversion_pct ?? 0}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
