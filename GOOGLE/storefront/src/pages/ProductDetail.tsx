import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { products } from "../data/products";
import { tracker } from "../utils/tracker";
import type { CartItem } from "../store/cart";
import type { StockMap } from "../App";

interface Props {
  onAddToCart: (product: (typeof products)[0]) => void;
  cartItems: CartItem[];
  stockMap: StockMap;
}

function StockPill({ stock }: { stock: number }) {
  if (stock === 0) return <span className="inline-flex items-center gap-1 text-sm font-semibold text-red-600 bg-red-50 px-3 py-1 rounded-full">Sold Out</span>;
  if (stock <= 3)  return <span className="inline-flex items-center gap-1 text-sm font-semibold text-amber-600 bg-amber-50 px-3 py-1 rounded-full">Only {stock} units left</span>;
  return <span className="inline-flex items-center gap-1 text-sm font-semibold text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full">In Stock ({stock} units)</span>;
}

export function ProductDetail({ onAddToCart, cartItems, stockMap }: Props) {
  const { id } = useParams<{ id: string }>();
  const product = products.find((p) => p.id === id);
  const [qty, setQty] = useState(1);

  useEffect(() => {
    if (product) tracker.productView(product);
  }, [product]);

  if (!product) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <p className="text-gray-500">Product not found.</p>
        <Link to="/" className="mt-4 inline-block text-indigo-600 font-medium">Back to store</Link>
      </div>
    );
  }

  const stock = stockMap[product.id] ?? 10;
  const soldOut = stock === 0;
  const inCart = cartItems.some((i) => i.product.id === product.id);

  function handleAdd() {
    if (soldOut) return;
    for (let i = 0; i < qty; i++) onAddToCart(product!);
    tracker.addToCart(product!, qty);
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <Link to="/" className="inline-flex items-center gap-1 text-indigo-600 text-sm font-medium hover:underline mb-6">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
        All Products
      </Link>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
        {/* Image */}
        <div className="rounded-3xl overflow-hidden bg-gray-100 shadow-sm">
          <img
            src={product.image}
            alt={product.name}
            className={`w-full h-96 object-cover ${soldOut ? "opacity-40 grayscale" : ""}`}
          />
        </div>

        {/* Info */}
        <div className="flex flex-col gap-4">
          <div>
            <span className="text-xs font-bold text-indigo-500 uppercase tracking-widest">{product.category}</span>
            {product.badge && (
              <span className="ml-2 bg-indigo-100 text-indigo-700 text-xs font-bold px-2 py-0.5 rounded-full">{product.badge}</span>
            )}
          </div>

          <h1 className="text-3xl font-extrabold text-gray-900 leading-tight">{product.name}</h1>

          <div className="flex items-center gap-2">
            <span className="text-yellow-400 text-lg">{"★".repeat(Math.floor(product.rating))}</span>
            <span className="text-gray-500 text-sm font-medium">{product.rating} · {product.reviews.toLocaleString()} reviews</span>
          </div>

          <p className="text-gray-500 text-sm leading-relaxed">{product.description}</p>

          <div className="flex items-baseline gap-3 mt-1">
            <span className="text-4xl font-extrabold text-gray-900">Rs.{product.price.toLocaleString("en-IN")}</span>
          </div>

          <StockPill stock={stock} />

          {!soldOut && (
            <div className="flex items-center gap-3">
              <label className="text-sm text-gray-600 font-medium">Qty</label>
              <select
                value={qty}
                onChange={(e) => setQty(Number(e.target.value))}
                className="border border-gray-200 rounded-xl px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-300"
              >
                {Array.from({ length: Math.min(stock, 5) }, (_, i) => i + 1).map(n => (
                  <option key={n}>{n}</option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={handleAdd}
            disabled={soldOut}
            className={`py-4 px-8 rounded-2xl font-bold text-base transition-all ${
              soldOut
                ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                : inCart
                ? "bg-emerald-100 text-emerald-700"
                : "bg-indigo-600 text-white hover:bg-indigo-700 shadow-md hover:shadow-lg"
            }`}
          >
            {soldOut ? "Out of Stock" : inCart ? "Added to Cart" : "Add to Cart"}
          </button>

          {/* Trust Badges */}
          <div className="flex gap-3 flex-wrap pt-2">
            {[
              { icon: "🚚", label: "Free Delivery" },
              { icon: "↩️", label: "10-day Returns" },
              { icon: "🛡️", label: "1 Year Warranty" },
            ].map(b => (
              <div key={b.label} className="flex items-center gap-1.5 bg-gray-50 rounded-xl px-3 py-2 text-xs font-medium text-gray-600 border border-gray-100">
                <span>{b.icon}</span> {b.label}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
