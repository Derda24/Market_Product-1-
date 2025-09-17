"use client";

import { useEffect, useState, useCallback } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ProductCard } from "@/components/ProductCard";
import { calculateValueScore, calculatePriceMetrics, formatPrice } from '@/lib/priceUtils';
import { LoadingScreen } from "@/components/LoadingScreen";
import type { Product } from './types';
import FloatingChatWidget from "@/components/FloatingChatWidget";
import { PerformanceMonitor } from "@/components/PerformanceMonitor";
import { useTranslation } from "@/hooks/useTranslation";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { CitySelector } from "@/components/CitySelector";
import type { City } from "@/lib/geo";

// Debug flag for detailed logging
const DEBUG = process.env.NODE_ENV === 'development';

type SortOption = 
  | 'price-asc' 
  | 'price-desc' 
  | 'name' 
  | 'best-value' 
  | 'price-per-unit' 
  | 'bulk-deals'
  | 'recent-changes'
  | 'nutriscore'
  | 'nova-score';

interface PaginationInfo {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

export default function Home() {
  const { t, loading: translationLoading } = useTranslation();
  const [products, setProducts] = useState<Product[]>([]);
  const [filtered, setFiltered] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [store, setStore] = useState("");
  const [priceRange, setPriceRange] = useState([0.01, 100]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedCity, setSelectedCity] = useState<City | null>(null);
  const [sortBy, setSortBy] = useState<SortOption>('price-asc');
  const [compareMode, setCompareMode] = useState(false);
  const [selectedProducts, setSelectedProducts] = useState<Set<string>>(new Set());
  const [initialLoading, setInitialLoading] = useState(true);
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pagination, setPagination] = useState<PaginationInfo | null>(null);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [fallbackMessage, setFallbackMessage] = useState<string | null>(null);

  // Add initial loading effect
  useEffect(() => {
    const timer = setTimeout(() => {
      setInitialLoading(false);
    }, 2000);
    return () => clearTimeout(timer);
  }, []);

  // Update the fetchProducts function to use pagination
  const fetchProducts = useCallback(async (page: number = 1, reset: boolean = false) => {
    try {
      if (reset) {
        setIsLoading(true);
        setProducts([]);
      } else {
        setIsLoadingMore(true);
      }

      const params = new URLSearchParams({
        page: page.toString(),
        limit: '12',
        search: search,
        store: store,
        minPrice: priceRange[0].toString(),
        maxPrice: priceRange[1].toString(),
      });
      if (selectedCity?.name) {
        params.set('city', selectedCity.name);
      }

      const res = await fetch(`/api/products?${params}`);
      const json = await res.json();
      
      if (json.error) {
        throw new Error(json.error);
      }

      const newProducts = json.products || [];
      
      if (reset) {
        setProducts(newProducts);
        setFiltered(sortProducts(newProducts));
      } else {
        setProducts(prev => [...prev, ...newProducts]);
        setFiltered(prev => sortProducts([...prev, ...newProducts]));
      }

      setPagination(json.pagination);
      setHasMore(json.pagination.hasNext);
      setFallbackMessage(json.fallbackMessage || null);
      
    } catch (error) {
      console.error("Error fetching products:", error);
    } finally {
      setIsLoading(false);
      setIsLoadingMore(false);
    }
  }, [search, store, priceRange, sortBy, selectedCity]);

  // Debounced search effect
  useEffect(() => {
    const timer = setTimeout(() => {
      setCurrentPage(1);
      fetchProducts(1, true);
    }, 300);

    return () => clearTimeout(timer);
  }, [search, store, priceRange, sortBy, selectedCity]);

  useEffect(() => {
    fetchProducts(1, true);
  }, []);

  // Toggle product selection for comparison
  const toggleProductSelection = (productId: string) => {
    const newSelection = new Set(selectedProducts);
    if (newSelection.has(productId)) {
      newSelection.delete(productId);
    } else if (newSelection.size < 4) { // Limit to comparing 4 products
      newSelection.add(productId);
    }
    setSelectedProducts(newSelection);
  };

  // Enhanced sorting function with nutrition scores
  const sortProducts = (products: Product[]) => {
    return [...products].sort((a, b) => {
      switch (sortBy) {
        case 'price-asc':
          return (a.price || 0) - (b.price || 0);
          
        case 'price-desc':
          return (b.price || 0) - (a.price || 0);
          
        case 'name':
          return a.name.localeCompare(b.name);
          
        case 'best-value':
          const aScore = calculateValueScore(a.price || 0, a.quantity, a.category);
          const bScore = calculateValueScore(b.price || 0, b.quantity, b.category);
          return bScore - aScore;
          
        case 'price-per-unit':
          const aMetrics = calculatePriceMetrics(a.price || 0, a.quantity);
          const bMetrics = calculatePriceMetrics(b.price || 0, b.quantity);
          return aMetrics.pricePerStandardUnit - bMetrics.pricePerStandardUnit;
          
        case 'bulk-deals':
          const aMetrics2 = calculatePriceMetrics(a.price || 0, a.quantity);
          const bMetrics2 = calculatePriceMetrics(b.price || 0, b.quantity);
          const aBulkScore = (aMetrics2.isMultiPack ? 1 : 0) * (1 / aMetrics2.pricePerStandardUnit);
          const bBulkScore = (bMetrics2.isMultiPack ? 1 : 0) * (1 / bMetrics2.pricePerStandardUnit);
          return bBulkScore - aBulkScore;
          
        case 'recent-changes':
          const aDate = new Date(a.last_updated || 0);
          const bDate = new Date(b.last_updated || 0);
          return bDate.getTime() - aDate.getTime();

        case 'nutriscore':
          const nutriScores: Record<string, number> = { 'a': 5, 'b': 4, 'c': 3, 'd': 2, 'e': 1 };
          const aNutriScore = a.nutriscore ? nutriScores[a.nutriscore.toLowerCase()] || 0 : 0;
          const bNutriScore = b.nutriscore ? nutriScores[b.nutriscore.toLowerCase()] || 0 : 0;
          return bNutriScore - aNutriScore;

        case 'nova-score':
          const aNova = a.nova_group || 5;
          const bNova = b.nova_group || 5;
          return aNova - bNova;  // Lower NOVA scores are better
          
        default:
          return 0;
      }
    });
  };

  // Load more products
  const loadMore = () => {
    if (!isLoadingMore && hasMore) {
      const nextPage = currentPage + 1;
      setCurrentPage(nextPage);
      fetchProducts(nextPage, false);
    }
  };

  // Add a function to handle exiting compare mode and clearing selection
  const handleExitCompare = () => {
    setCompareMode(false);
    setSelectedProducts(new Set());
  };

  return (
    <>
      <LoadingScreen isLoading={initialLoading} />
      
      <main className={`transition-opacity duration-500 ${initialLoading ? 'opacity-0' : 'opacity-100'}`}>
        {/* Enhanced Background with Gradient */}
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 relative overflow-hidden">
          {/* Background decorative elements */}
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            <div className="absolute -top-40 -right-40 w-80 h-80 bg-gradient-to-br from-blue-200 to-indigo-200 rounded-full opacity-20 blur-3xl"></div>
            <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gradient-to-br from-indigo-200 to-purple-200 rounded-full opacity-20 blur-3xl"></div>
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-gradient-to-br from-green-200 to-blue-200 rounded-full opacity-10 blur-3xl"></div>
          </div>

          <div className="relative z-10 p-4 md:p-10">
            {/* Enhanced Header */}
            <div className="text-center mb-12">
              <div className="flex justify-center md:justify-between items-center gap-4 mb-6 flex-wrap">
                <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full shadow-lg">
                  <span className="text-3xl">🛍️</span>
                </div>
                <div className="ml-auto flex items-center gap-3 w-full md:w-auto">
                  <div className="hidden md:block">
                    <LanguageSwitcher />
                  </div>
                  <div className="w-full md:w-[420px]">
                    <CitySelector value={selectedCity} onChange={setSelectedCity} />
                  </div>
                </div>
              </div>
              <h1 className="text-5xl md:text-6xl font-extrabold bg-gradient-to-r from-gray-800 via-blue-800 to-indigo-800 bg-clip-text text-transparent mb-4">
                {selectedCity ? `${selectedCity.name} ${t('header.title')}` : t('header.titleGeneric')}
              </h1>
              <p className="text-xl text-gray-600 max-w-2xl mx-auto leading-relaxed">
                {t('header.subtitleGeneric')}
              </p>
            </div>

            {/* Enhanced Filter Section */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
              {selectedCity && (
                <div className="md:col-span-4 -mt-4 mb-2">
                  <span className="inline-flex items-center gap-2 bg-blue-50 text-blue-700 border border-blue-200 px-3 py-1.5 rounded-full text-sm">
                    🗺️ City: <button className="underline" onClick={() => setSelectedCity(null)}>{selectedCity.name}</button>
                  </span>
                </div>
              )}
              {fallbackMessage && (
                <div className="md:col-span-4 -mt-4 mb-2">
                  <div className="bg-amber-50 text-amber-700 border border-amber-200 px-4 py-2 rounded-lg text-sm">
                    ⚠️ {fallbackMessage}
                  </div>
                </div>
              )}
              <div className="relative">
                <Input
                  placeholder={t('header.searchPlaceholder')}
                  value={search}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearch(e.target.value)}
                  className="h-12 bg-white/80 backdrop-blur-sm border-gray-300 shadow-lg hover:shadow-xl transition-all duration-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <Select onValueChange={(val: string) => setStore(val)}>
                <SelectTrigger className="h-12 bg-white/80 backdrop-blur-sm border-gray-300 shadow-lg hover:shadow-xl transition-all duration-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                  <SelectValue placeholder={t('header.filterByStore')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="lidl.es">Lidl</SelectItem>
                  <SelectItem value="carrefour.es">Carrefour</SelectItem>
                  <SelectItem value="aldi">Aldi</SelectItem>
                  <SelectItem value="bonarea">BonÀrea</SelectItem>
                  <SelectItem value="bonpreu">Bonpreu</SelectItem>
                  <SelectItem value="condisline">Condisline</SelectItem>
                  <SelectItem value="mercadona.es">Mercadona</SelectItem>
                  <SelectItem value="El Corte Inglés">El Corte Inglés</SelectItem>
                  <SelectItem value="alcampo">Alcampo</SelectItem>
                  <SelectItem value="dia.es">Dia</SelectItem>
                </SelectContent>
              </Select>

              <Select onValueChange={(val: string) => setSortBy(val as SortOption)}>
                <SelectTrigger className="h-12 bg-white/80 backdrop-blur-sm border-gray-300 shadow-lg hover:shadow-xl transition-all duration-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                  <SelectValue placeholder="🔄 Sort by" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="price-asc">💰 Price: Low to High</SelectItem>
                  <SelectItem value="price-desc">💎 Price: High to Low</SelectItem>
                  <SelectItem value="name">📝 Name</SelectItem>
                  <SelectItem value="best-value">⭐ Best Value</SelectItem>
                  <SelectItem value="price-per-unit">📊 Price per Unit</SelectItem>
                  <SelectItem value="bulk-deals">📦 Bulk Deals</SelectItem>
                  <SelectItem value="recent-changes">🔄 Recently Updated</SelectItem>
                  <SelectItem value="nutriscore">🥗 Best Nutrition (Nutri-Score)</SelectItem>
                  <SelectItem value="nova-score">🌱 Least Processed (NOVA)</SelectItem>
                </SelectContent>
              </Select>

              <Button
                variant="outline"
                onClick={() => setCompareMode(!compareMode)}
                className={`h-12 bg-white/80 backdrop-blur-sm border-gray-300 shadow-lg hover:shadow-xl transition-all duration-200 ${
                  compareMode ? 'bg-blue-50 border-blue-300 text-blue-700' : ''
                }`}
              >
                {compareMode ? t('products.removeFromComparison') : t('products.addToComparison')}
              </Button>
            </div>

            {/* Enhanced Price Range Slider */}
            <div className="mb-8 bg-white/80 backdrop-blur-sm p-6 rounded-2xl shadow-lg border border-gray-200">
              <div className="flex items-center justify-between mb-4">
                <label className="text-lg font-semibold text-gray-800">
                  💶 {t('header.priceRange')}
                </label>
                <span className="text-sm font-medium text-gray-600">
                  €{priceRange[0]} - €{priceRange[1]}
                </span>
              </div>
              <Slider
                defaultValue={[0, 100]}
                min={0}
                max={100}
                step={1}
                onValueChange={(val: number[]) => setPriceRange(val)}
                className="w-full"
              />
            </div>

            {/* Enhanced Comparison View */}
            {compareMode && (
              <div className="mb-8 bg-white/90 backdrop-blur-sm p-6 rounded-2xl shadow-xl border border-gray-200 overflow-x-auto sticky top-0 z-20">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-bold text-gray-800">{t('comparison.title')}</h3>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleExitCompare}
                    className="text-red-600 border-red-300 hover:bg-red-50"
                  >
                    {t('comparison.close')}
                  </Button>
                </div>
                {selectedProducts.size === 0 ? (
                  <div className="text-center py-8">
                    <div className="text-4xl mb-4">🔍</div>
                    <p className="text-gray-500 text-lg">{t('comparison.addProducts')}</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {filtered
                      .filter(p => selectedProducts.has(p.id))
                      .map(product => (
                        <div key={product.id} className="bg-gradient-to-br from-gray-50 to-gray-100 p-4 rounded-xl border border-gray-200">
                          <h4 className="font-semibold text-gray-800 mb-3">{product.name}</h4>
                          <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                              <span className="text-gray-600">{t('productCard.price')}:</span>
                              <span className="font-medium">{product.price !== null ? formatPrice(product.price) : 'N/A'}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">{t('productCard.category')}:</span>
                              <span className="font-medium">{product.category}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">{t('productCard.store')}:</span>
                              <span className="font-medium">{product.store_id}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">{t('productCard.quantity')}:</span>
                              <span className="font-medium">{product.quantity}</span>
                            </div>
                            {product.price && (
                              <div className="flex justify-between">
                                <span className="text-gray-600">Value Score:</span>
                                <span className="font-medium">{calculateValueScore(product.price, product.quantity, product.category).toFixed(0)}/100</span>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            )}

            {/* Enhanced Product Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
              {filtered.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  onSelect={compareMode ? toggleProductSelection : undefined}
                  isSelected={selectedProducts.has(product.id)}
                  showComparison={compareMode}
                />
              ))}
            </div>

            {/* Load More Button */}
            {hasMore && filtered.length > 0 && (
              <div className="text-center mt-8">
                <Button
                  onClick={loadMore}
                  disabled={isLoadingMore}
                  className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white px-6 py-3 rounded-lg shadow-lg hover:shadow-xl transition-all duration-200"
                >
                  {isLoadingMore ? (
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      {t('products.loading')}
                    </div>
                  ) : (
                    t('products.loadMore')
                  )}
                </Button>
              </div>
            )}

            {/* Enhanced Empty State */}
            {filtered.length === 0 && (
              <div className="text-center py-16">
                <div className="text-6xl mb-6">🔍</div>
                <h3 className="text-2xl font-bold text-gray-800 mb-4">{t('products.noProducts')}</h3>
                <p className="text-gray-600 text-lg mb-6">Try adjusting your filters or search terms to find what you're looking for.</p>
                <Button
                  onClick={() => {
                    setSearch("");
                    setStore("");
                    setPriceRange([0.01, 100]);
                  }}
                  className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white px-6 py-3 rounded-lg shadow-lg hover:shadow-xl transition-all duration-200"
                >
                  Clear All Filters
                </Button>
              </div>
            )}

            {/* Product Count */}
            {filtered.length > 0 && pagination && (
              <div className="text-center mt-8 text-gray-600">
                {t('products.showing')} {filtered.length} {t('products.of')} {pagination.total} {t('products.products')}
                {pagination.totalPages > 1 && (
                  <span className="ml-2">(Page {pagination.page} of {pagination.totalPages})</span>
                )}
              </div>
            )}

            <FloatingChatWidget />
            <PerformanceMonitor 
              productCount={filtered.length} 
              isVisible={DEBUG} 
            />
          </div>
        </div>
      </main>
    </>
  );
}
