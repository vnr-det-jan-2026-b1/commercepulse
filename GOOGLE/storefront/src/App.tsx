import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { Home } from "./pages/Home";
import { ProductDetail } from "./pages/ProductDetail";
import { OrderConfirmed } from "./pages/OrderConfirmed";
import { CartDrawer } from "./components/CartDrawer";
import { useCart } from "./store/cart";
import { tracker } from "./utils/tracker";
import type { Product } from "./data/products";
import "./index.css";

const API_URL = import.meta.env.VITE_API_URL as string;
const SELLER_ID = (import.meta.env.VITE_SELLER_ID as string) || "SELLER_001";

export type StockMap = Record<string, number>;

function App() {
  const { items, add, remove, clear, total, count } = useCart();
  const [cartOpen, setCartOpen] = useState(false);
  const [stockMap, setStockMap] = useState<StockMap>({});

  function refreshStock() {
    fetch(`${API_URL}/v1/analytics/stock?seller_id=${SELLER_ID}`)
      .then(r => r.json())
      .then(data => {
        const map: StockMap = {};
        for (const p of (data.products ?? [])) map[p.product_id] = p.current_stock;
        setStockMap(map);
      })
      .catch(() => {});
  }

  useEffect(() => { refreshStock(); }, []);

  function handleAddToCart(product: Product) {
    const stock = stockMap[product.id] ?? 10;
    if (stock <= 0) return;
    add(product);
    tracker.addToCart(product, 1);
    setCartOpen(true);
  }

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white border-b border-gray-100 sticky top-0 z-30 shadow-sm">
          <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
            <Link to="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-indigo-600 to-violet-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">N</div>
              <span className="text-xl font-bold text-gray-900">Nova<span className="text-indigo-600">Cart</span></span>
            </Link>
            <button
              onClick={() => setCartOpen(true)}
              className="relative flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-xl text-sm font-semibold hover:bg-indigo-700 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13l-1.5 7h10.8" />
              </svg>
              Cart
              {count > 0 && (
                <span className="bg-white text-indigo-600 text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
                  {count}
                </span>
              )}
            </button>
          </div>
        </nav>

        <Routes>
          <Route path="/" element={<Home onAddToCart={handleAddToCart} cartItems={items} stockMap={stockMap} />} />
          <Route path="/product/:id" element={<ProductDetail onAddToCart={handleAddToCart} cartItems={items} stockMap={stockMap} />} />
          <Route path="/confirmed" element={<OrderConfirmed />} />
        </Routes>

        <CartDrawer
          open={cartOpen}
          onClose={() => setCartOpen(false)}
          items={items}
          total={total}
          onRemove={remove}
          onClear={clear}
          onPurchase={() => setTimeout(refreshStock, 2000)}
        />
      </div>
    </BrowserRouter>
  );
}

export default App;
