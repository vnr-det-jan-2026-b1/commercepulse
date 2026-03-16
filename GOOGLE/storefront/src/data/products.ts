export interface Product {
  id: string;
  name: string;
  category: string;
  price: number;
  description: string;
  image: string;
  rating: number;
  reviews: number;
  badge?: string;
}

export const CATEGORIES = ['All', 'Audio', 'Accessories', 'Wearables', 'Peripherals', 'Smart Home'] as const;

export const products: Product[] = [
  {
    id: "P001",
    name: "Wireless Earbuds Pro",
    category: "Audio",
    price: 2999,
    description: "30hr battery · Active Noise Cancellation · IPX5 waterproof · Touch controls · 10-min fast charge = 2hr play",
    image: "/products/p001.jpg",
    rating: 4.5,
    reviews: 2847,
    badge: "Best Seller",
  },
  {
    id: "P002",
    name: "20W Fast Charger",
    category: "Accessories",
    price: 799,
    description: "GaN III technology · USB-C Power Delivery · Foldable prongs · Universal compatibility · Charges phone to 50% in 30 min",
    image: "/products/p002.jpg",
    rating: 4.3,
    reviews: 1203,
  },
  {
    id: "P003",
    name: "Smartwatch Series X",
    category: "Wearables",
    price: 8499,
    description: "1.45\" AMOLED always-on · GPS · SpO2 + heart rate · 7-day battery · 50m water resistant · Aluminium case",
    image: "/products/p003.png",
    rating: 4.6,
    reviews: 5120,
    badge: "New",
  },
  {
    id: "P004",
    name: "Mechanical Keyboard",
    category: "Peripherals",
    price: 3499,
    description: "TKL 87-key · Red linear switches · Per-key RGB · USB-C detachable cable · Aluminium top plate · N-key rollover",
    image: "/products/p004.jpg",
    rating: 4.7,
    reviews: 934,
  },
  {
    id: "P005",
    name: "Portable Power Bank 20000mAh",
    category: "Accessories",
    price: 1799,
    description: "65W bi-directional PD · Dual USB-C + USB-A · Charges laptop · Digital % display · Slim 15mm profile",
    image: "/products/p005.jpg",
    rating: 4.4,
    reviews: 3612,
  },
  {
    id: "P006",
    name: "Noise-Cancelling Headphones",
    category: "Audio",
    price: 5999,
    description: "40hr ANC playback · Hi-Res Audio certified · Memory foam earcups · Bluetooth 5.3 · Foldable · 3-mode EQ",
    image: "/products/p006.jpg",
    rating: 4.8,
    reviews: 7841,
    badge: "Top Rated",
  },
  {
    id: "P007",
    name: "Portable Bluetooth Speaker",
    category: "Audio",
    price: 2299,
    description: "360 degree surround sound · 24hr battery · IPX7 waterproof · Built-in powerbank · Dual stereo pairing · Bass radiator",
    image: "/products/p007.jpg",
    rating: 4.4,
    reviews: 2103,
  },
  {
    id: "P008",
    name: "USB-C Hub 7-in-1",
    category: "Accessories",
    price: 1499,
    description: "4K HDMI · 100W PD passthrough · USB-A 3.0 x3 · SD + MicroSD slots · Plug and play · Aluminium shell",
    image: "/products/p008.jpg",
    rating: 4.2,
    reviews: 876,
    badge: "New",
  },
  {
    id: "P009",
    name: "Gaming Mouse RGB",
    category: "Peripherals",
    price: 1299,
    description: "16000 DPI optical sensor · 7 programmable buttons · Per-zone RGB · 80hr wireless battery · Ergonomic right-hand grip",
    image: "/products/p009.jpg",
    rating: 4.5,
    reviews: 1544,
  },
  {
    id: "P010",
    name: "4K Webcam Pro",
    category: "Peripherals",
    price: 4999,
    description: "4K 30fps · 1080p 60fps · AI auto-framing · Built-in noise-cancelling mic · Low-light correction · Privacy cover",
    image: "/products/p010.jpg",
    rating: 4.3,
    reviews: 621,
  },
  {
    id: "P011",
    name: "Fitness Tracker Band",
    category: "Wearables",
    price: 3299,
    description: "1.47\" AMOLED · 14-day battery · 100+ workout modes · 24/7 heart rate and SpO2 · Sleep tracking · 5ATM swim-proof",
    image: "/products/p011.jpg",
    rating: 4.4,
    reviews: 2890,
  },
  {
    id: "P012",
    name: "Smart LED Desk Lamp",
    category: "Smart Home",
    price: 1999,
    description: "Voice and app control · 4 colour temperatures · 10 brightness levels · USB-A charging port · Eye-care flicker-free · Touch dimmer",
    image: "/products/p012.jpg",
    rating: 4.3,
    reviews: 1102,
  },
];
