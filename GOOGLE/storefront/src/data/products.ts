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
    image: "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&q=80",
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
    image: "https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=600&q=80",
    rating: 4.3,
    reviews: 1203,
  },
  {
    id: "P003",
    name: "Smartwatch Series X",
    category: "Wearables",
    price: 8499,
    description: "1.45\" AMOLED always-on · GPS · SpO2 + heart rate · 7-day battery · 50m water resistant · Aluminium case",
    image: "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&q=80",
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
    image: "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&q=80",
    rating: 4.7,
    reviews: 934,
  },
  {
    id: "P005",
    name: "Portable Power Bank 20000mAh",
    category: "Accessories",
    price: 1799,
    description: "65W bi-directional PD · Dual USB-C + USB-A · Charges laptop · Digital % display · Slim 15mm profile",
    image: "https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=600&q=80",
    rating: 4.4,
    reviews: 3612,
  },
  {
    id: "P006",
    name: "Noise-Cancelling Headphones",
    category: "Audio",
    price: 5999,
    description: "40hr ANC playback · Hi-Res Audio certified · Memory foam earcups · Bluetooth 5.3 · Foldable · 3-mode EQ",
    image: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&q=80",
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
    image: "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600&q=80",
    rating: 4.4,
    reviews: 2103,
  },
  {
    id: "P008",
    name: "USB-C Hub 7-in-1",
    category: "Accessories",
    price: 1499,
    description: "4K HDMI · 100W PD passthrough · USB-A 3.0 x3 · SD + MicroSD slots · Plug and play · Aluminium shell",
    image: "https://images.unsplash.com/photo-1625895197185-efcec01cffe0?w=600&q=80",
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
    image: "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=600&q=80",
    rating: 4.5,
    reviews: 1544,
  },
  {
    id: "P010",
    name: "4K Webcam Pro",
    category: "Peripherals",
    price: 4999,
    description: "4K 30fps · 1080p 60fps · AI auto-framing · Built-in noise-cancelling mic · Low-light correction · Privacy cover",
    image: "https://images.unsplash.com/photo-1587826080692-f439cd0b70da?w=600&q=80",
    rating: 4.3,
    reviews: 621,
  },
  {
    id: "P011",
    name: "Fitness Tracker Band",
    category: "Wearables",
    price: 3299,
    description: "1.47\" AMOLED · 14-day battery · 100+ workout modes · 24/7 heart rate and SpO2 · Sleep tracking · 5ATM swim-proof",
    image: "https://images.unsplash.com/photo-1575311373937-040b8e1fd5b6?w=600&q=80",
    rating: 4.4,
    reviews: 2890,
  },
  {
    id: "P012",
    name: "Smart LED Desk Lamp",
    category: "Smart Home",
    price: 1999,
    description: "Voice and app control · 4 colour temperatures · 10 brightness levels · USB-A charging port · Eye-care flicker-free · Touch dimmer",
    image: "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=600&q=80",
    rating: 4.3,
    reviews: 1102,
  },
];
