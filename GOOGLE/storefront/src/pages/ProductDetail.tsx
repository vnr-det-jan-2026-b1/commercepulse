import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import type { Product } from "../data/products";
import { tracker } from "../utils/tracker";
import type { CartItem } from "../store/cart";
import type { StockMap } from "../App";

interface Props {
  products: Product[];
  onAddToCart: (product: Product) => void;
  cartItems: CartItem[];
  stockMap: StockMap;
}

export function ProductDetail({ products, onAddToCart, cartItems, stockMap }: Props) {
  const { id } = useParams<{ id: string }>();
  const product = products.find((p) => p.id === id);
  const [qty, setQty] = useState(1);

  useEffect(() => {
    if (product) tracker.productView(product);
  }, [product]);

  if (!product) {
    return (
      <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "80px 32px", textAlign: "center" }}>
        <p style={{ color: "var(--text-secondary)" }}>Product not found.</p>
        <Link to="/" style={{ color: "var(--accent)", fontWeight: 600, textDecoration: "none" }}>← Back to store</Link>
      </div>
    );
  }

  const stockRaw = stockMap[product.id];
  const stockLoaded = stockRaw !== undefined;
  const stock = stockRaw ?? 0;
  const soldOut = stockLoaded && stock === 0;
  const lowStock = stockLoaded && !soldOut && stock <= 3;
  const inCart = cartItems.some((i) => i.product.id === product.id);

  function handleAdd() {
    if (soldOut) return;
    for (let i = 0; i < qty; i++) onAddToCart(product!);
    tracker.addToCart(product!, qty);
  }

  return (
    <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "40px 32px" }}>
      <Link to="/" style={{ display: "inline-flex", alignItems: "center", gap: "6px", color: "var(--text-secondary)", fontSize: "13px", fontWeight: 500, textDecoration: "none", marginBottom: "32px" }}>
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        All Products
      </Link>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "48px", alignItems: "start" }}>
        {/* Image */}
        <div style={{ background: "var(--surface)", borderRadius: "16px", overflow: "hidden", border: "1px solid var(--border)" }}>
          <img
            src={product.image} alt={product.name}
            style={{ width: "100%", height: "420px", objectFit: "cover", display: "block", opacity: soldOut ? 0.4 : 1, filter: soldOut ? "grayscale(1)" : "none" }}
          />
        </div>

        {/* Info */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "10px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-secondary)" }}>{product.category}</span>
            {product.badge && (
              <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--accent)", display: "flex", alignItems: "center", gap: "4px" }}>● {product.badge}</span>
            )}
          </div>

          <h1 style={{ fontSize: "2.1rem", fontWeight: 800, color: "var(--text-primary)", lineHeight: 1.1, letterSpacing: "-0.035em", margin: 0 }}>{product.name}</h1>

          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "var(--text-secondary)" }}>
            <span style={{ color: "#f59e0b" }}>{"★".repeat(Math.floor(product.rating))}</span>
            {product.rating} · {product.reviews.toLocaleString()} reviews
          </div>

          <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.75, margin: 0 }}>{product.description}</p>

          <p style={{ fontSize: "2.6rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.045em", lineHeight: 1, margin: 0 }}>
            Rs.{product.price.toLocaleString("en-IN")}
          </p>

          {/* Stock status */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", fontWeight: 600, color: soldOut ? "var(--danger)" : lowStock ? "#f59e0b" : "var(--accent)" }}>
            ● {soldOut ? "Out of Stock" : lowStock ? `Only ${stock} units left` : stockLoaded ? `In Stock — ${stock} units` : "In Stock"}
          </div>

          {!soldOut && (
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <label style={{ fontSize: "13px", color: "var(--text-secondary)", fontWeight: 500 }}>Qty</label>
              <select
                value={qty}
                onChange={e => setQty(Number(e.target.value))}
                style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px", padding: "8px 14px", fontSize: "14px", color: "var(--text-primary)", cursor: "pointer", fontFamily: "inherit" }}
              >
                {Array.from({ length: Math.min(stockLoaded ? stock : 5, 5) }, (_, i) => i + 1).map(n => (
                  <option key={n}>{n}</option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={handleAdd} disabled={soldOut}
            style={{ padding: "15px 24px", borderRadius: "8px", fontSize: "15px", fontWeight: 700, border: "none", cursor: soldOut ? "not-allowed" : "pointer", fontFamily: "inherit", background: soldOut ? "var(--raised)" : inCart ? "var(--accent-muted)" : "var(--accent)", color: soldOut ? "var(--text-secondary)" : inCart ? "var(--accent)" : "white" }}
          >
            {soldOut ? "Out of Stock" : inCart ? "✓ Added to Cart" : "Add to Cart"}
          </button>

          {/* Trust badges */}
          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            {[
              { icon: "🚚", label: "Free Delivery" },
              { icon: "↩️", label: "10-day Returns" },
              { icon: "🛡️", label: "1 Year Warranty" },
            ].map(b => (
              <div key={b.label} style={{ display: "flex", alignItems: "center", gap: "6px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px", padding: "8px 12px", fontSize: "12px", fontWeight: 500, color: "var(--text-secondary)" }}>
                <span>{b.icon}</span> {b.label}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
