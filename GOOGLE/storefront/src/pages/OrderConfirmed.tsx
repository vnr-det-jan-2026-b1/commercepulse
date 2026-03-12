import { Link } from "react-router-dom";

export function OrderConfirmed() {
  return (
    <div className="max-w-lg mx-auto px-4 py-24 text-center">
      <div className="text-6xl mb-6">✅</div>
      <h1 className="text-3xl font-bold text-gray-900 mb-3">Order Confirmed!</h1>
      <p className="text-gray-500 mb-8">
        Thanks for your purchase. Your order has been placed and will be delivered soon.
      </p>
      <Link
        to="/"
        className="inline-block bg-indigo-600 text-white px-8 py-3 rounded-xl font-semibold hover:bg-indigo-700 transition-colors"
      >
        Continue Shopping
      </Link>
    </div>
  );
}
