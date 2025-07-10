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

export async function updateProductPrice(productId: string, newPrice: number, storeId: string) {
  try {
    const res = await fetch(`/api/priceTracking/updatePrice?productId=${encodeURIComponent(productId)}&newPrice=${newPrice}&storeId=${encodeURIComponent(storeId)}`);
    const json = await res.json();
    if (json.error) throw new Error(json.error);
    return json.data;
  } catch (error) {
    console.error('Error updating price:', error);
    throw error;
  }
}

export async function getPriceHistory(productId: string): Promise<PriceAnalytics> {
  try {
    const res = await fetch(`/api/priceTracking?productId=${encodeURIComponent(productId)}`);
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`API error: ${res.status} - ${text}`);
    }
    let json;
    try {
      json = await res.json();
    } catch (e) {
      const text = await res.text();
      console.error('Failed to parse JSON. Response text:', text);
      throw new Error('Failed to parse JSON from API response');
    }
    const history = json.priceHistory;
    if (!history || history.length === 0) {
      throw new Error('No price history found');
    }

    // Current price is the most recent one
    const currentPrice = history[0].price;
    // Previous price is the second most recent
    const previousPrice = history.length > 1 ? history[1].price : null;
    // Calculate price change
    const priceChange = previousPrice ? currentPrice - previousPrice : null;
    const percentageChange = previousPrice ? ((currentPrice - previousPrice) / previousPrice) * 100 : null;
    // Calculate weekly average (last 7 days)
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    const weeklyPrices = history.filter((p: PriceHistory) => new Date(p.recorded_at) >= weekAgo);
    const weeklyAverage = weeklyPrices.reduce((sum: number, p: PriceHistory) => sum + p.price, 0) / (weeklyPrices.length || 1);
    // Calculate monthly average (last 30 days)
    const monthAgo = new Date();
    monthAgo.setDate(monthAgo.getDate() - 30);
    const monthlyPrices = history.filter((p: PriceHistory) => new Date(p.recorded_at) >= monthAgo);
    const monthlyAverage = monthlyPrices.reduce((sum: number, p: PriceHistory) => sum + p.price, 0) / (monthlyPrices.length || 1);
    // Get lowest and highest prices
    const lowestPrice = Math.min(...history.map((p: PriceHistory) => p.price));
    const highestPrice = Math.max(...history.map((p: PriceHistory) => p.price));

    return {
      currentPrice,
      previousPrice,
      priceChange,
      percentageChange,
      weeklyAverage,
      monthlyAverage,
      lowestPrice,
      highestPrice,
      priceHistory: history
    };
  } catch (error) {
    console.error('Error fetching price history:', error);
    throw error;
  }
}

export async function getProductsWithPriceChanges(days: number = 7) {
  try {
    const date = new Date();
    date.setDate(date.getDate() - days);

    const res = await fetch(`/api/priceTracking/priceChanges?days=${days}`);
    const json = await res.json();
    return json.priceChanges;
  } catch (error) {
    console.error('Error fetching price changes:', error);
    throw error;
  }
}

export async function analyzePriceTrends(productId: string) {
  const history = await getPriceHistory(productId);
  
  // Calculate weekly price volatility
  const weeklyPrices = history.priceHistory.slice(0, 7);
  const priceChanges = weeklyPrices.map((p, i) => {
    if (i === weeklyPrices.length - 1) return 0;
    return Math.abs(p.price - weeklyPrices[i + 1].price);
  });
  
  const volatility = priceChanges.reduce((sum, change) => sum + change, 0) / priceChanges.length;

  return {
    ...history,
    volatility,
    isVolatile: volatility > 0.5, // Consider prices volatile if average daily change is more than €0.50
    trend: history.priceChange && history.priceChange > 0 ? 'increasing' : 'decreasing'
  };
} 