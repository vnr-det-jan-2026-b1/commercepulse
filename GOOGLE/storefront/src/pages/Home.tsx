import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { products, CATEGORIES } from "../data/products";
import { tracker } from "../utils/tracker";
import type { CartItem } from "../store/cart";
import type { StockMap } from "../App";

interface Props {
  onAddToCart: (product: (typeof products)[0]) => void;
  cartItems: CartItem[];
  stockMap: StockMap;
}

function StockBadge({ stock }: { stock: number }) {
  if (stock === 0) return <span className="text-xs font-semibold text-red-600 bg-red-50 px-2 py-0.5 rounded-full">Sold Out</span>;
  if (stock <= 3)  return <span className="text-xs font-semibold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">Only {stock} left!</span>;
  return <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">In Stock</span>;
}

export function Home({ onAddToCart, cartItems, stockMap }: Props) {
  const [activeCategory, setActiveCategory] = useState<string>("All");

  useEffect(() => { tracker.pageView(); }, []);

  const filtered = activeCategory === "All"
    ? products
    : products.filter(p => p.category === activeCategory);

  return (
    <div>
      {/* Hero Banner */}
      <div className="bg-gradient-to-br from-indigo-600 via-violet-600 to-purple-700 text-white">
        <div className="max-w-7xl mx-auto px-4 py-16 flex flex-col items-center text-center">
          <span className="bg-white/20 text-white text-xs font-semibold px-3 py-1 rounded-full mb-4 tracking-widest uppercase">Free delivery on orders above Rs.999</span>
          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight mb-4">
            The Future of<br />Tech is Here
          </h1>
          <p className="text-indigo-200 text-lg mb-8 max-w-md">
            Premium electronics, curated for you. From audio to wearables, shop the best at unbeatable prices.
          </p>
          <a href="#products" className="bg-white text-indigo-700 font-bold px-8 py-3 rounded-2xl hover:bg-indigo-50 transition-colors shadow-lg">
            Shop Now
          </a>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-10" id="products">
        {/* Category Filter */}
        <div className="flex gap-2 overflow-x-auto pb-2 mb-8">
          {CATEGORIES.map(cat => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`whitespace-nowrap px-5 py-2 rounded-full text-sm font-semibold transition-all ${
                activeCategory === cat
                  ? "bg-indigo-600 text-white shadow-md"
                  : "bg-white text-gray-600 border border-gray-200 hover:border-indigo-300 hover:text-indigo-600"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-gray-900">
            {activeCategory === "All" ? "All Products" : activeCategory}
            <span className="text-gray-400 font-normal text-sm ml-2">({filtered.length} items)</span>
          </h2>
        </div>

        {/* Product Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {filtered.map((p) => {
            const stock = stockMap[p.id] ?? 10;
            const inCart = cartItems.some((i) => i.product.id === p.id);
            const soldOut = stock === 0;

            return (
              <div
                key={p.id}
                className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 flex flex-col"
              >
                <Link to={`/product/${p.id}`} className="relative block">
                  <img
                    src={p.image}
                    alt={p.name}
                    className={`w-full h-44 object-cover ${soldOut ? "opacity-40 grayscale" : ""}`}
                  />
                  {p.badge && (
                    <span className="absolute top-2 left-2 bg-indigo-600 text-white text-xs font-bold px-2 py-0.5 rounded-full shadow">
                      {p.badge}
                    </span>
                  )}
                </Link>
                <div className="p-4 flex flex-col flex-1">
                  <span className="text-xs text-indigo-500 font-semibold uppercase tracking-wide">{p.category}</span>
                  <Link to={`/product/${p.id}`}>
                    <h3 className="mt-1 text-sm font-bold text-gray-900 hover:text-indigo-600 transition-colors leading-snug line-clamp-2">
                      {p.name}
                    </h3>
                  </Link>
                  <div className="flex items-center gap-1 mt-1.5">
                    <span className="text-yellow-400 text-xs">{"★".repeat(Math.floor(p.rating))}</span>
                    <span className="text-xs text-gray-400">{p.rating} ({p.reviews.toLocaleString()})</span>
                  </div>
                  <div className="mt-auto pt-3 flex items-end justify-between gap-2">
                    <div>
                      <p className="text-lg font-extrabold text-gray-900">Rs.{p.price.toLocaleString("en-IN")}</p>
                      <div className="mt-1"><StockBadge stock={stock} /></div>
                    </div>
                    <button
                      onClick={() => !soldOut && onAddToCart(p)}
                      disabled={soldOut}
                      className={`flex-shrink-0 px-3 py-2 rounded-xl text-xs font-bold transition-all ${
                        soldOut
                          ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                          : inCart
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm"
                      }`}
                    >
                      {soldOut ? "Sold Out" : inCart ? "In Cart" : "Add"}
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
