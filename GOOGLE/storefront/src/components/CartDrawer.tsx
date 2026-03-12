import { useNavigate } from "react-router-dom";
import type { CartItem } from "../store/cart";
import { tracker } from "../utils/tracker";

interface Props {
  open: boolean;
  onClose: () => void;
  items: CartItem[];
  total: number;
  onRemove: (id: string) => void;
  onClear: () => void;
  onPurchase: () => void;
}

export function CartDrawer({ open, onClose, items, total, onRemove, onClear, onPurchase }: Props) {
  const navigate = useNavigate();

  function checkout() {
    tracker.purchase(items);
    onPurchase();
    onClear();
    onClose();
    navigate("/confirmed");
  }

  return (
    <>
      {open && <div className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm" onClick={onClose} />}
      <div
        className={`fixed top-0 right-0 h-full w-96 bg-white shadow-2xl z-50 flex flex-col transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Your Cart</h2>
            <p className="text-xs text-gray-400">{items.length} item{items.length !== 1 ? "s" : ""}</p>
          </div>
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors text-xl">&times;</button>
        </div>

        {items.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 text-gray-400">
            <div className="text-5xl">🛒</div>
            <p className="text-sm font-medium">Your cart is empty</p>
            <button onClick={onClose} className="text-indigo-600 text-sm font-semibold hover:underline">Continue Shopping</button>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
            {items.map(({ product, quantity }) => (
              <div key={product.id} className="flex gap-3 items-center p-3 rounded-2xl bg-gray-50">
                <img src={product.image} alt={product.name} className="w-14 h-14 object-cover rounded-xl flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-gray-900 leading-tight truncate">{product.name}</p>
                  <p className="text-xs text-gray-400 mt-0.5">Qty {quantity}</p>
                  <p className="text-sm font-bold text-indigo-600 mt-0.5">Rs.{(product.price * quantity).toLocaleString("en-IN")}</p>
                </div>
                <button onClick={() => onRemove(product.id)} className="text-gray-300 hover:text-red-400 transition-colors flex-shrink-0">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}

        {items.length > 0 && (
          <div className="px-6 py-4 border-t border-gray-100 space-y-3">
            <div className="bg-indigo-50 rounded-2xl p-4 space-y-2">
              <div className="flex justify-between text-sm text-gray-600">
                <span>Subtotal</span>
                <span>Rs.{total.toLocaleString("en-IN")}</span>
              </div>
              <div className="flex justify-between text-sm text-gray-600">
                <span>Delivery</span>
                <span className="text-emerald-600 font-medium">{total >= 999 ? "Free" : "Rs.49"}</span>
              </div>
              <div className="h-px bg-indigo-100" />
              <div className="flex justify-between font-bold text-gray-900">
                <span>Total</span>
                <span>Rs.{(total + (total >= 999 ? 0 : 49)).toLocaleString("en-IN")}</span>
              </div>
            </div>
            <p className="text-xs text-center text-gray-400">Estimated delivery: 2-4 business days</p>
            <button
              onClick={checkout}
              className="w-full bg-gradient-to-r from-indigo-600 to-violet-600 text-white py-4 rounded-2xl font-bold text-base hover:opacity-90 transition-opacity shadow-md"
            >
              Place Order
            </button>
          </div>
        )}
      </div>
    </>
  );
}
