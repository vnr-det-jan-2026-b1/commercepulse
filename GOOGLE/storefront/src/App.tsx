import { useState, useEffect, useCallback } from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { Home } from "./pages/Home";
import { ProductDetail } from "./pages/ProductDetail";
import { OrderConfirmed } from "./pages/OrderConfirmed";
import { CartDrawer } from "./components/CartDrawer";
import { useCart } from "./store/cart";
import { tracker } from "./utils/tracker";
import type { CartItem } from "./store/cart";
import type { Product } from "./data/products";
import "./index.css";

const API_URL = import.meta.env.VITE_API_URL as string;
const SELLER_ID = (import.meta.env.VITE_SELLER_ID as string) || "SELLER_001";

export type StockMap = Record<string, number>;

function ThemeToggle() {
  const [theme, setTheme] = useState<string>(() => localStorage.getItem("nova-theme") ?? "dark");
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("nova-theme", theme);
  }, [theme]);
  return (
    <button
      onClick={() => setTheme(t => t === "dark" ? "light" : "dark")}
      style={{ background: "none", border: "1px solid var(--border)", borderRadius: "8px", width: "34px", height: "34px", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", color: "var(--text-secondary)", fontSize: "15px", flexShrink: 0 }}
    >
      {theme === "dark" ? "☀" : "☾"}
    </button>
  );
}

function App() {
  const { items, add, remove, updateQuantity, clear, total, count } = useCart();
  const [cartOpen, setCartOpen] = useState(false);
  const [stockMap, setStockMap] = useState<StockMap>({});
  const [products, setProducts] = useState<Product[]>([]);

  useEffect(() => {
    const t = localStorage.getItem("nova-theme") ?? "dark";
    document.documentElement.dataset.theme = t;
  }, []);

  useEffect(() => {
    fetch(`${API_URL}/v1/analytics/products?seller_id=${SELLER_ID}`)
      .then(r => r.json())
      .then(data => {
        const rows: Product[] = (data.products ?? []).map((p: Record<string, unknown>) => ({
          id:          p.product_id as string,
          name:        p.name as string,
          category:    p.category as string,
          price:       p.price as number,
          description: p.description as string,
          image:       p.image as string,
          rating:      p.rating as number,
          reviews:     p.reviews as number,
          badge:       p.badge as string || undefined,
        }));
        setProducts(rows);
      })
      .catch(() => {});
  }, []);

  const refreshStock = useCallback(() => {
    fetch(`${API_URL}/v1/analytics/stock?seller_id=${SELLER_ID}`)
      .then(r => r.json())
      .then(data => {
        const map: StockMap = {};
        for (const p of (data.products ?? [])) map[p.product_id] = p.current_stock;
        setStockMap(map);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    refreshStock();
    const interval = setInterval(refreshStock, 30_000);
    return () => clearInterval(interval);
  }, [refreshStock]);

  function handleAddToCart(product: Product) {
    const MAX_STOCK = 10;
    const stock = stockMap[product.id] ?? MAX_STOCK;
    if (stock <= 0) return;

    // Don't exceed available stock when items are already in cart
    const inCart = items.find(i => i.product.id === product.id)?.quantity ?? 0;
    if (inCart >= stock) return;

    add(product);
    tracker.addToCart(product, 1);
    setCartOpen(true);
  }

  async function handlePurchase(purchasedItems: CartItem[]) {
    // 1. Record purchase in backend (updates _purchase_store and triggers BQ DML INSERT).
    //    Only deduct from local stockMap if this succeeds — if it fails, BQ has no record
    //    and we must not show a phantom deduction.
    try {
      const res = await fetch(`${API_URL}/v1/analytics/stock/purchase`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          seller_id: SELLER_ID,
          items: purchasedItems.map(({ product, quantity }) => ({
            product_id: product.id,
            quantity,
          })),
        }),
      });
      if (!res.ok) throw new Error(`purchase POST ${res.status}`);
    } catch (err) {
      console.error("Purchase record failed — stock not deducted locally:", err);
      setTimeout(refreshStock, 1000);
      return;
    }

    // 2. Immediately deduct from local stockMap so UI reflects purchase at once.
    setStockMap(prev => {
      const next = { ...prev };
      for (const { product, quantity } of purchasedItems) {
        next[product.id] = Math.max(0, (next[product.id] ?? 0) - quantity);
      }
      return next;
    });

    // 3. Re-fetch from backend after a short delay to get server-confirmed stock.
    setTimeout(refreshStock, 3000);
  }

  return (
    <BrowserRouter>
      <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
        {/* ── Nav ── */}
        <nav style={{ position: "sticky", top: 0, zIndex: 30, background: "var(--nav-bg)", borderBottom: "1px solid var(--border)" }}>
          <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "0 24px", height: "60px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <Link to="/" style={{ display: "flex", alignItems: "center", gap: "10px", textDecoration: "none" }}>
              <div style={{ width: "32px", height: "32px", background: "var(--accent)", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 800, fontSize: "14px" }}>N</div>
              <span style={{ fontSize: "18px", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
                Nova<span style={{ color: "var(--accent)" }}>Cart</span>
              </span>
            </Link>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <ThemeToggle />
              <button
                onClick={() => setCartOpen(true)}
                style={{ display: "flex", alignItems: "center", gap: "8px", background: "var(--accent)", color: "white", border: "none", borderRadius: "8px", padding: "8px 16px", fontSize: "13px", fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}
              >
                <svg width="15" height="15" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13l-1.5 7h10.8" />
                </svg>
                Cart
                {count > 0 && (
                  <span style={{ background: "white", color: "var(--accent)", fontSize: "10px", fontWeight: 800, borderRadius: "50%", width: "18px", height: "18px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    {count}
                  </span>
                )}
              </button>
            </div>
          </div>
        </nav>

        <Routes>
          <Route path="/" element={<Home products={products} onAddToCart={handleAddToCart} cartItems={items} stockMap={stockMap} />} />
          <Route path="/product/:id" element={<ProductDetail products={products} onAddToCart={handleAddToCart} cartItems={items} stockMap={stockMap} />} />
          <Route path="/confirmed" element={<OrderConfirmed />} />
        </Routes>

        <CartDrawer
          open={cartOpen}
          onClose={() => setCartOpen(false)}
          items={items}
          total={total}
          onRemove={remove}
          onUpdateQuantity={updateQuantity}
          onClear={clear}
          onPurchase={handlePurchase}
          stockMap={stockMap}
        />
      </div>
    </BrowserRouter>
  );
}

export default App;
