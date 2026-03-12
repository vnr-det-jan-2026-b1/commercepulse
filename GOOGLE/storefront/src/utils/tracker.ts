import type { Product } from "../data/products";

const API_URL = import.meta.env.VITE_API_URL as string;
const SELLER_ID = (import.meta.env.VITE_SELLER_ID as string) || "SELLER_001";

function getSessionId(): string {
  let sid = sessionStorage.getItem("cp_session_id");
  if (!sid) {
    sid = crypto.randomUUID();
    sessionStorage.setItem("cp_session_id", sid);
  }
  return sid;
}

function send(payload: object) {
  fetch(`${API_URL}/v1/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ seller_id: SELLER_ID, session_id: getSessionId(), ...payload }),
  }).catch(() => {}); // fire-and-forget
}

export const tracker = {
  pageView() {
    send({ event_type: "page_view", page_url: window.location.pathname });
  },
  productView(product: Product) {
    send({
      event_type: "product_view",
      product_id: product.id,
      product_name: product.name,
      price: product.price,
      quantity: 1,
      page_url: window.location.pathname,
    });
  },
  addToCart(product: Product, quantity: number) {
    send({
      event_type: "add_to_cart",
      product_id: product.id,
      product_name: product.name,
      price: product.price,
      quantity,
      page_url: window.location.pathname,
    });
  },
  purchase(items: { product: Product; quantity: number }[]) {
    items.forEach(({ product, quantity }) => {
      send({
        event_type: "purchase",
        product_id: product.id,
        product_name: product.name,
        price: product.price,
        quantity,
        page_url: "/confirmed",
      });
    });
  },
};
