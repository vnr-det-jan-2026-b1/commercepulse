import { useNavigate } from "react-router-dom";
import type { CartItem } from "../store/cart";
import { tracker } from "../utils/tracker";
import type { StockMap } from "../App";

interface Props {
  open: boolean;
  onClose: () => void;
  items: CartItem[];
  total: number;
  onRemove: (id: string) => void;
  onUpdateQuantity: (id: string, qty: number) => void;
  onClear: () => void;
  onPurchase: (items: CartItem[]) => void;
  stockMap: StockMap;
}

export function CartDrawer({ open, onClose, items, total, onRemove, onUpdateQuantity, onClear, onPurchase, stockMap }: Props) {
  const navigate = useNavigate();

  function checkout() {
    tracker.purchase(items);
    onPurchase(items);   // passes purchased items so App can deduct stock
    onClear();
    onClose();
    navigate("/confirmed");
  }

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 40, opacity: open ? 1 : 0, pointerEvents: open ? "auto" : "none", transition: "opacity 300ms ease" }}
      />

      {/* Drawer */}
      <div
        style={{ position: "fixed", top: 0, right: 0, height: "100%", width: "380px", background: "var(--surface)", borderLeft: "1px solid var(--border)", zIndex: 50, display: "flex", flexDirection: "column", transform: open ? "translateX(0)" : "translateX(100%)", transition: "transform 300ms ease-out" }}
      >
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "20px 24px", borderBottom: "1px solid var(--border)" }}>
          <div>
            <h2 style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Your Cart</h2>
            <p style={{ fontSize: "12px", color: "var(--text-secondary)", margin: "3px 0 0" }}>{items.length} item{items.length !== 1 ? "s" : ""}</p>
          </div>
          <button
            onClick={onClose}
            style={{ width: "32px", height: "32px", borderRadius: "8px", border: "1px solid var(--border)", background: "transparent", color: "var(--text-secondary)", cursor: "pointer", fontSize: "20px", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "inherit" }}
          >×</button>
        </div>

        {/* Items */}
        {items.length === 0 ? (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "12px", color: "var(--text-secondary)" }}>
            <div style={{ fontSize: "44px", opacity: 0.3 }}>🛒</div>
            <p style={{ fontSize: "14px", fontWeight: 500, margin: 0 }}>Your cart is empty</p>
            <button onClick={onClose} style={{ color: "var(--accent)", fontSize: "13px", fontWeight: 600, background: "none", border: "none", cursor: "pointer", fontFamily: "inherit" }}>
              Continue Shopping
            </button>
          </div>
        ) : (
          <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px", display: "flex", flexDirection: "column", gap: "8px" }}>
            {items.map(({ product, quantity }) => {
              const availableStock = stockMap[product.id] ?? Infinity;
              const atStockLimit = quantity >= availableStock;

              return (
                <div key={product.id} style={{ display: "flex", gap: "12px", alignItems: "center", padding: "12px", borderRadius: "10px", background: "var(--raised)" }}>
                  <img src={product.image} alt={product.name} style={{ width: "52px", height: "52px", objectFit: "cover", borderRadius: "8px", flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)", margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{product.name}</p>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", margin: "6px 0" }}>
                      <button
                        onClick={() => onUpdateQuantity(product.id, quantity - 1)}
                        style={{ width: "24px", height: "24px", borderRadius: "6px", border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text-primary)", cursor: "pointer", fontSize: "14px", fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "inherit", flexShrink: 0 }}
                      >−</button>
                      <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)", minWidth: "16px", textAlign: "center" }}>{quantity}</span>
                      <button
                        onClick={() => { if (!atStockLimit) onUpdateQuantity(product.id, quantity + 1); }}
                        disabled={atStockLimit}
                        title={atStockLimit ? `Only ${availableStock} in stock` : undefined}
                        style={{ width: "24px", height: "24px", borderRadius: "6px", border: "1px solid var(--border)", background: atStockLimit ? "var(--raised)" : "var(--surface)", color: atStockLimit ? "var(--text-secondary)" : "var(--text-primary)", cursor: atStockLimit ? "not-allowed" : "pointer", fontSize: "14px", fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "inherit", flexShrink: 0, opacity: atStockLimit ? 0.4 : 1 }}
                      >+</button>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <p style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent)", margin: 0 }}>Rs.{(product.price * quantity).toLocaleString("en-IN")}</p>
                      {atStockLimit && (
                        <span style={{ fontSize: "10px", fontWeight: 700, color: "var(--danger)", background: "rgba(239,68,68,0.1)", borderRadius: "4px", padding: "1px 5px" }}>MAX</span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => onRemove(product.id)}
                    style={{ background: "none", border: "none", color: "var(--text-secondary)", cursor: "pointer", padding: "4px", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center" }}
                    onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = "var(--danger)"; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = "var(--text-secondary)"; }}
                  >
                    <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* Footer */}
        {items.length > 0 && (
          <div style={{ padding: "16px 20px", borderTop: "1px solid var(--border)" }}>
            <div style={{ background: "var(--raised)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px", marginBottom: "12px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", color: "var(--text-secondary)", marginBottom: "8px" }}>
                <span>Subtotal</span><span>Rs.{total.toLocaleString("en-IN")}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", color: "var(--text-secondary)", marginBottom: "12px" }}>
                <span>Delivery</span>
                <span style={{ color: "var(--accent)", fontWeight: 600 }}>{total >= 999 ? "Free" : "Rs.49"}</span>
              </div>
              <div style={{ height: "1px", background: "var(--border)", marginBottom: "12px" }} />
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "15px", fontWeight: 700, color: "var(--text-primary)" }}>
                <span>Total</span>
                <span>Rs.{(total + (total >= 999 ? 0 : 49)).toLocaleString("en-IN")}</span>
              </div>
            </div>
            <p style={{ fontSize: "11px", textAlign: "center", color: "var(--text-secondary)", margin: "0 0 12px" }}>Estimated delivery: 2–4 business days</p>
            <button
              onClick={checkout}
              style={{ width: "100%", background: "var(--accent)", color: "white", border: "none", borderRadius: "8px", padding: "14px", fontSize: "15px", fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}
            >
              Place Order
            </button>
          </div>
        )}
      </div>
    </>
  );
}
