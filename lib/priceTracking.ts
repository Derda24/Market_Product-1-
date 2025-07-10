// lib/priceTracking.ts

export async function getPriceHistory(productId: string) {
  const res = await fetch(`/api/priceTracking?productId=${encodeURIComponent(productId)}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error: ${res.status} - ${text}`);
  }
  const json = await res.json();
  return json.priceHistory;
} 