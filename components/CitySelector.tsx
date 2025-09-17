'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useTranslation } from '@/hooks/useTranslation';
import { City, detectNearestCity } from '@/lib/geo';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

interface CitySelectorProps {
  value?: City | null;
  onChange?: (city: City | null) => void;
}

export const CitySelector: React.FC<CitySelectorProps> = ({ value, onChange }) => {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [cities, setCities] = useState<City[]>([]);
  const [selected, setSelected] = useState<City | null>(value || null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const saved = typeof window !== 'undefined' ? localStorage.getItem('selectedCity') : null;
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setSelected(parsed);
        onChange?.(parsed);
      } catch {}
    } else {
      // Try geolocation
      detectNearestCity().then((c) => {
        if (c) {
          setSelected(c);
          onChange?.(c);
          localStorage.setItem('selectedCity', JSON.stringify(c));
        }
      });
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const fetchCities = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/cities?q=${encodeURIComponent(query)}`, { signal: controller.signal });
        const json = await res.json();
        setCities(json.cities || []);
      } catch {}
      setLoading(false);
    };
    fetchCities();
    return () => controller.abort();
  }, [query]);

  const handleSelect = (c: City) => {
    setSelected(c);
    onChange?.(c);
    if (typeof window !== 'undefined') localStorage.setItem('selectedCity', JSON.stringify(c));
  };

  return (
    <div className="w-full md:w-80 md:ml-auto">
      <div className="relative">
        <div className="flex items-center gap-2">
          <Input
            placeholder={t('cities.searchPlaceholder')}
            value={query}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setQuery(e.target.value)}
            className="h-10 text-sm rounded-full bg-white/90 border-gray-200 shadow-sm"
          />
          {selected && (
            <Button
              variant="ghost"
              className="h-10 text-sm px-2 rounded-full text-blue-700 hover:bg-blue-50"
              onClick={() => handleSelect(selected)}
              title={selected.name}
            >
              🗺️ {selected.name}
            </Button>
          )}
        </div>
        <div className="absolute right-0 mt-2 w-full md:w-[22rem] max-h-64 overflow-auto rounded-xl border border-gray-200 bg-white shadow-xl z-50">
          {loading ? (
            <div className="p-3 text-sm text-gray-500">{t('products.loading')}</div>
          ) : (
            <div className="divide-y divide-gray-100">
              {cities.map((c) => (
                <button
                  key={c.id}
                  onClick={() => handleSelect(c)}
                  className={`w-full text-left px-3 py-2.5 text-sm hover:bg-gray-50 transition-colors ${
                    selected?.id === c.id ? 'bg-blue-50/60' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-gray-800 leading-tight">{c.name}</div>
                      <div className="text-gray-500 text-xs">{c.region}</div>
                    </div>
                    <div className="text-gray-300">→</div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};


