// lib/priceTracking.ts

export interface PriceHistory {
  id: string;
  product_id: string;
  price: number;
  store_id: string;
  recorded_at: string;
  valid_until: string | null;
  is_current: boolean;
}

export interface PriceAnalytics {
  currentPrice: number;
  previousPrice: number | null;
  priceChange: number | null;
  percentageChange: number | null;
  weeklyAverage: number;
  monthlyAverage: number;
  lowestPrice: number;
  highestPrice: number;
  priceHistory: PriceHistory[];
}

export async function getPriceHistory(productId: string): Promise<PriceAnalytics> {
  const res = await fetch(`/api/priceTracking?productId=${encodeURIComponent(productId)}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error: ${res.status} - ${text}`);
  }
  const json = await res.json();
  return json.priceHistory;
} 