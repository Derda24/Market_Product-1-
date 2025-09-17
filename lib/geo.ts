export type City = {
  id: number;
  name: string;
  region: string;
  latitude: number;
  longitude: number;
  population?: number;
};

export function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const toRad = (v: number) => (v * Math.PI) / 180;
  const R = 6371; // km
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

export async function detectNearestCity(): Promise<City | null> {
  if (typeof window === 'undefined' || !('geolocation' in navigator)) return null;

  const position = await new Promise<GeolocationPosition>((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: false,
      maximumAge: 600000,
      timeout: 8000,
    });
  }).catch(() => null as any);

  if (!position) return null;

  const { latitude, longitude } = position.coords;
  const res = await fetch(`/api/cities?limit=200`);
  const json = await res.json();
  const cities: City[] = json.cities || [];

  if (!cities.length) return null;

  let nearest: City | null = null;
  let minDist = Number.POSITIVE_INFINITY;
  for (const c of cities) {
    const d = haversineKm(latitude, longitude, c.latitude, c.longitude);
    if (d < minDist) {
      minDist = d;
      nearest = c;
    }
  }
  return nearest;
}


