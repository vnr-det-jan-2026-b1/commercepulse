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
