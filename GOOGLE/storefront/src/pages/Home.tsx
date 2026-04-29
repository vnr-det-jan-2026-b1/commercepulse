import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CATEGORIES } from "../data/products";
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

const HERO_ID = "P006";

export function Home({ products, onAddToCart, cartItems, stockMap }: Props) {
  const [activeCategory, setActiveCategory] = useState<string>("All");
  const hero = products.find(p => p.id === HERO_ID) ?? products[0];

  useEffect(() => { tracker.pageView(); }, []);

  const filtered = activeCategory === "All"
    ? products
    : products.filter(p => p.category === activeCategory);

  if (!hero) {
    return (
      <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>Loading products…</p>
      </div>
    );
  }

  return (
    <div>
      {/* ── HERO — always dark, Nike-style ── */}
      <div style={{ background: "#0c0c0c", overflow: "hidden" }}>
        <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "60px 32px 36px", display: "grid", gridTemplateColumns: "1fr 1.1fr 0.65fr", alignItems: "center", gap: "24px" }}>

          {/* Left: huge italic headline */}
          <div>
            <p style={{ color: "rgba(255,255,255,0.3)", fontSize: "10px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.14em", margin: "0 0 22px" }}>
              ● Free delivery above Rs.999
            </p>
            <h1 style={{ color: "white", fontSize: "clamp(2.8rem, 5vw, 4.8rem)", fontWeight: 900, lineHeight: 0.95, letterSpacing: "-0.045em", margin: "0 0 32px", fontStyle: "italic" }}>
              THE<br />FUTURE<br />OF TECH.
            </h1>
            <a
              href="#products"
              style={{ display: "inline-flex", alignItems: "center", gap: "8px", color: "white", fontSize: "13px", fontWeight: 600, textDecoration: "none", border: "1px solid rgba(255,255,255,0.18)", borderRadius: "6px", padding: "9px 18px", transition: "border-color 200ms ease, background 200ms ease" }}
              onMouseEnter={e => { const el = e.currentTarget as HTMLElement; el.style.borderColor = "rgba(255,255,255,0.45)"; el.style.background = "rgba(255,255,255,0.06)"; }}
              onMouseLeave={e => { const el = e.currentTarget as HTMLElement; el.style.borderColor = "rgba(255,255,255,0.18)"; el.style.background = "transparent"; }}
            >
              Shop Now <span>→</span>
            </a>
          </div>

          {/* Center: floating hero product */}
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center" }}>
            <Link to={`/product/${hero.id}`} style={{ display: "block" }}>
              <img
                src={hero.image}
                alt={hero.name}
                style={{ width: "100%", maxWidth: "380px", objectFit: "contain", filter: "drop-shadow(0 40px 80px rgba(0,0,0,0.95))", transition: "transform 400ms ease" }}
                onMouseEnter={e => { (e.currentTarget as HTMLImageElement).style.transform = "scale(1.05) translateY(-8px)"; }}
                onMouseLeave={e => { (e.currentTarget as HTMLImageElement).style.transform = "scale(1) translateY(0)"; }}
              />
            </Link>
          </div>

          {/* Right: product info */}
          <div style={{ textAlign: "right" }}>
            <p style={{ color: "rgba(255,255,255,0.3)", fontSize: "10px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.12em", margin: "0 0 8px" }}>Featured</p>
            <p style={{ color: "white", fontSize: "15px", fontWeight: 700, margin: "0 0 8px", lineHeight: 1.3 }}>{hero.name}</p>
            <p style={{ color: "rgba(255,255,255,0.55)", fontSize: "22px", fontWeight: 800, margin: "0 0 16px", letterSpacing: "-0.025em" }}>
              Rs.{hero.price.toLocaleString("en-IN")}
            </p>
            <Link to={`/product/${hero.id}`} style={{ color: "#22c55e", fontSize: "13px", fontWeight: 600, textDecoration: "none" }}>
              View Details →
            </Link>
          </div>
        </div>

        {/* Bottom row: 3 mini product cards */}
        <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "0 32px 32px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: "10px" }}>
            {products.slice(0, 3).map(p => {
              const stock = stockMap[p.id] ?? 10;
              const soldOut = stock === 0;
              return (
                <div
                  key={p.id}
                  style={{ display: "flex", alignItems: "center", gap: "12px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "12px", padding: "12px 14px", transition: "background 200ms ease, border-color 200ms ease" }}
                  onMouseEnter={e => { const el = e.currentTarget; el.style.background = "rgba(255,255,255,0.09)"; el.style.borderColor = "rgba(255,255,255,0.15)"; }}
                  onMouseLeave={e => { const el = e.currentTarget; el.style.background = "rgba(255,255,255,0.05)"; el.style.borderColor = "rgba(255,255,255,0.07)"; }}
                >
                  <Link to={`/product/${p.id}`} style={{ flexShrink: 0 }}>
                    <img src={p.image} alt={p.name} style={{ width: "50px", height: "50px", objectFit: "cover", borderRadius: "8px", opacity: soldOut ? 0.4 : 1, display: "block" }} />
                  </Link>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Link to={`/product/${p.id}`} style={{ textDecoration: "none" }}>
                      <p style={{ color: "white", fontSize: "12px", fontWeight: 600, margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.name}</p>
                    </Link>
                    <p style={{ color: "rgba(255,255,255,0.3)", fontSize: "11px", margin: "3px 0 0" }}>{"★".repeat(Math.floor(p.rating))} {p.rating}</p>
                  </div>
                  <div style={{ textAlign: "right", flexShrink: 0, display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "5px" }}>
                    <p style={{ color: "white", fontSize: "13px", fontWeight: 700, margin: 0 }}>Rs.{p.price.toLocaleString("en-IN")}</p>
                    <button
                      onClick={() => !soldOut && onAddToCart(p)}
                      disabled={soldOut}
                      style={{ width: "26px", height: "26px", borderRadius: "50%", background: soldOut ? "rgba(255,255,255,0.1)" : "#22c55e", border: "none", color: "white", fontSize: "18px", cursor: soldOut ? "not-allowed" : "pointer", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 300, lineHeight: 1, padding: 0 }}
                    >+</button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── PRODUCTS GRID ── */}
      <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "48px 32px" }} id="products">

        {/* Category filter */}
        <div style={{ display: "flex", gap: "8px", overflowX: "auto", paddingBottom: "4px", marginBottom: "28px" }}>
          {CATEGORIES.map(cat => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              style={{ whiteSpace: "nowrap", padding: "7px 18px", borderRadius: "8px", fontSize: "13px", fontWeight: 600, border: "1px solid", cursor: "pointer", fontFamily: "inherit", background: activeCategory === cat ? "var(--accent)" : "var(--surface)", borderColor: activeCategory === cat ? "var(--accent)" : "var(--border)", color: activeCategory === cat ? "white" : "var(--text-secondary)" }}
            >
              {cat}
            </button>
          ))}
        </div>

        <div style={{ display: "flex", alignItems: "baseline", gap: "10px", marginBottom: "20px" }}>
          <h2 style={{ fontSize: "20px", fontWeight: 700, color: "var(--text-primary)", margin: 0, letterSpacing: "-0.02em" }}>
            {activeCategory === "All" ? "All Products" : activeCategory}
          </h2>
          <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>{filtered.length} items</span>
        </div>

        {/* Grid */}
        <div className="stagger" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(290px, 1fr))", gap: "14px" }}>
          {filtered.map(p => {
            const stock = stockMap[p.id] ?? 10;
            const inCart = cartItems.some(i => i.product.id === p.id);
            const soldOut = stock === 0;
            const lowStock = !soldOut && stock <= 3;

            return (
              <div
                key={p.id}
                style={{ background: "var(--surface)", borderRadius: "12px", overflow: "hidden", display: "flex", flexDirection: "column", border: "1px solid transparent", transition: "border-color 200ms ease, transform 200ms ease" }}
                onMouseEnter={e => { const el = e.currentTarget; el.style.borderColor = "var(--border)"; el.style.transform = "scale(1.02)"; }}
                onMouseLeave={e => { const el = e.currentTarget; el.style.borderColor = "transparent"; el.style.transform = "scale(1)"; }}
              >
                <Link to={`/product/${p.id}`} style={{ position: "relative", display: "block", textDecoration: "none" }} onClick={() => tracker.productView(p)}>
                  <img
                    src={p.image} alt={p.name}
                    style={{ width: "100%", height: "200px", objectFit: "cover", display: "block", opacity: soldOut ? 0.4 : 1, filter: soldOut ? "grayscale(1)" : "none" }}
                  />
                  {p.badge && (
                    <span style={{ position: "absolute", top: "10px", left: "10px", fontSize: "10px", fontWeight: 700, color: "var(--text-secondary)", background: "var(--surface)", padding: "3px 8px", borderRadius: "4px", border: "1px solid var(--border)", display: "flex", alignItems: "center", gap: "4px" }}>
                      <span style={{ color: "var(--accent)" }}>●</span> {p.badge}
                    </span>
                  )}
                </Link>
                <div style={{ padding: "16px", display: "flex", flexDirection: "column", flex: 1 }}>
                  <span style={{ fontSize: "10px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--text-secondary)" }}>{p.category}</span>
                  <Link to={`/product/${p.id}`} style={{ textDecoration: "none" }} onClick={() => tracker.productView(p)}>
                    <h3 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-primary)", margin: "5px 0 6px", lineHeight: 1.35 }}>{p.name}</h3>
                  </Link>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "14px" }}>
                    <span style={{ color: "#f59e0b" }}>{"★".repeat(Math.floor(p.rating))}</span> {p.rating} ({p.reviews.toLocaleString()})
                  </div>
                  <div style={{ marginTop: "auto", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "10px" }}>
                    <div>
                      <p style={{ fontSize: "17px", fontWeight: 800, color: "var(--text-primary)", margin: 0, letterSpacing: "-0.02em" }}>
                        Rs.{p.price.toLocaleString("en-IN")}
                      </p>
                      <p style={{ fontSize: "11px", fontWeight: 600, margin: "4px 0 0", color: soldOut ? "var(--danger)" : lowStock ? "#f59e0b" : "var(--accent)", display: "flex", alignItems: "center", gap: "4px" }}>
                        <span>●</span>
                        {soldOut ? "Sold Out" : lowStock ? `Only ${stock} left` : "In Stock"}
                      </p>
                    </div>
                    <button
                      onClick={() => !soldOut && onAddToCart(p)}
                      disabled={soldOut}
                      style={{ flexShrink: 0, padding: "8px 16px", borderRadius: "8px", fontSize: "12px", fontWeight: 700, border: "none", cursor: soldOut ? "not-allowed" : "pointer", fontFamily: "inherit", background: soldOut ? "var(--raised)" : inCart ? "var(--accent-muted)" : "var(--accent)", color: soldOut ? "var(--text-secondary)" : inCart ? "var(--accent)" : "white" }}
                    >
                      {soldOut ? "Sold Out" : inCart ? "✓ In Cart" : "Add"}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
