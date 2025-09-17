import React, { useState, useEffect } from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { getPriceHistory, PriceAnalytics } from '@/lib/priceTracking';
import { calculatePriceMetrics, formatPrice } from '@/lib/priceUtils';
import { shouldUseImageFallback, generateFallbackImage } from '@/utils/imageQuality';
import type { Product, ProductCardProps } from '@/app/types';
import { useTranslation } from '@/hooks/useTranslation';

// Store name mapping with brand colors
const STORE_NAMES: { [key: string]: { name: string; color: string; bgColor: string } } = {
  'lidl.es': { name: 'Lidl', color: 'text-blue-600', bgColor: 'bg-blue-50' },
  'carrefour.es': { name: 'Carrefour', color: 'text-red-600', bgColor: 'bg-red-50' },
  'aldi': { name: 'Aldi', color: 'text-orange-600', bgColor: 'bg-orange-50' },
  'bonarea': { name: 'BonÀrea', color: 'text-green-600', bgColor: 'bg-green-50' },
  'bonpreu': { name: 'Bonpreu', color: 'text-purple-600', bgColor: 'bg-purple-50' },
  'condisline': { name: 'Condisline', color: 'text-indigo-600', bgColor: 'bg-indigo-50' },
  'mercadona.es': { name: 'Mercadona', color: 'text-pink-600', bgColor: 'bg-pink-50' },
  'El Corte Inglés': { name: 'El Corte Inglés', color: 'text-yellow-600', bgColor: 'bg-yellow-50' },
  'alcampo': { name: 'Alcampo', color: 'text-teal-600', bgColor: 'bg-teal-50' },
  'dia.es': { name: 'Dia', color: 'text-gray-600', bgColor: 'bg-gray-50' }
};

// Category-based placeholder images
const CATEGORY_ICONS: { [key: string]: string } = {
  'Fruits and Vegetables': '🥬',
  'Dairy and Eggs': '🥛',
  'Meat and Fish': '🥩',
  'Bread and Pastries': '🥖',
  'Beverages': '🥤',
  'Snacks': '🍿',
  'Frozen Foods': '❄️',
  'Canned Goods': '🥫',
  'Pasta and Rice': '🍝',
  'Oils and Sauces': '🫗',
  'Sweets and Chocolate': '🍫',
  'Cleaning Products': '🧽',
  'Personal Care': '🧴',
  'Baby Products': '👶',
  'Pet Food': '🐕',
  'default': '🛍️'
};

const ProductCard: React.FC<ProductCardProps> = ({ 
  product,
  onSelect, 
  isSelected, 
  showComparison 
}) => {
  const { t } = useTranslation();
  const [priceAnalytics, setPriceAnalytics] = useState<PriceAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);

  const loadPriceHistory = async () => {
    try {
      setIsLoading(true);
      const analytics = await getPriceHistory(product.id);
      setPriceAnalytics(analytics);
    } catch (error) {
      console.error('Error loading price history:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const priceMetrics = product.price ? calculatePriceMetrics(product.price, product.quantity) : { pricePerStandardUnit: 0, standardUnit: '' };
  
  // Enhanced nutrition score display
  const getNutriscoreColor = (score: string) => {
    const colors: { [key: string]: { bg: string; text: string } } = {
      'a': { bg: 'bg-gradient-to-r from-green-400 to-green-600', text: 'text-white' },
      'b': { bg: 'bg-gradient-to-r from-lime-400 to-lime-600', text: 'text-white' },
      'c': { bg: 'bg-gradient-to-r from-yellow-400 to-yellow-600', text: 'text-gray-800' },
      'd': { bg: 'bg-gradient-to-r from-orange-400 to-orange-600', text: 'text-white' },
      'e': { bg: 'bg-gradient-to-r from-red-400 to-red-600', text: 'text-white' }
    };
    return colors[score?.toLowerCase()] || { bg: 'bg-gray-300', text: 'text-gray-700' };
  };

  const getNovaGroupColor = (group: number) => {
    const colors = [
      { bg: 'bg-gradient-to-r from-green-400 to-green-600', text: 'text-white' },
      { bg: 'bg-gradient-to-r from-lime-400 to-lime-600', text: 'text-white' },
      { bg: 'bg-gradient-to-r from-yellow-400 to-yellow-600', text: 'text-gray-800' },
      { bg: 'bg-gradient-to-r from-red-400 to-red-600', text: 'text-white' }
    ];
    return colors[group - 1] || { bg: 'bg-gray-300', text: 'text-gray-700' };
  };

  const getStoreInfo = (storeId: string) => {
    return STORE_NAMES[storeId] || { name: storeId, color: 'text-gray-600', bgColor: 'bg-gray-50' };
  };

  const getCategoryIcon = (category: string) => {
    return CATEGORY_ICONS[category] || CATEGORY_ICONS.default;
  };

  const storeInfo = getStoreInfo(product.store_id);
  const nutriScoreColors = product.nutriscore ? getNutriscoreColor(product.nutriscore) : null;
  const novaColors = product.nova_group ? getNovaGroupColor(product.nova_group) : null;

  return (
    <Card 
      className={`relative overflow-hidden transition-all duration-300 hover:shadow-xl hover:scale-105 group
        ${isSelected ? 'ring-2 ring-blue-500 shadow-xl scale-105' : ''}
        ${showComparison ? 'cursor-pointer' : ''}
        bg-white border-0 shadow-lg hover:shadow-2xl`}
      onClick={() => onSelect && onSelect(product.id)}
    >
      {/* Selection indicator */}
      {showComparison && (
        <div className="absolute top-3 right-3 z-20">
          <div className={`w-7 h-7 rounded-full border-2 flex items-center justify-center transition-all duration-200
            ${isSelected ? 'bg-blue-500 border-blue-500 text-white scale-110' : 'border-gray-300 bg-white/90 backdrop-blur-sm'}`}>
            {isSelected && '✓'}
          </div>
        </div>
      )}

      {/* Price badge */}
      {product.price && (
        <div className="absolute top-3 left-3 z-10">
          <div className="bg-gradient-to-r from-green-400 to-green-600 text-white px-3 py-1 rounded-full text-sm font-bold shadow-lg">
            {formatPrice(product.price)}€
          </div>
        </div>
      )}

      <CardContent className="p-0">
        {/* Enhanced Product Image Section */}
        <div className="relative h-48 bg-gradient-to-br from-gray-50 to-gray-100 overflow-hidden">
          {product.image_url && !imageError && !shouldUseImageFallback(product.image_url, product) ? (
            <>
              {/* Loading skeleton */}
              {!imageLoaded && (
                <div className="absolute inset-0 bg-gradient-to-r from-gray-200 to-gray-300 animate-pulse flex items-center justify-center">
                  <div className="text-gray-400">
                    <svg className="w-8 h-8 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </div>
                </div>
              )}
              
              <img 
                src={product.image_url} 
                alt={product.name}
                className={`w-full h-full object-contain transition-opacity duration-300 ${
                  imageLoaded ? 'opacity-100' : 'opacity-0'
                }`}
                onLoad={() => setImageLoaded(true)}
                onError={() => {
                  setImageError(true);
                  setImageLoaded(true);
                }}
                loading="lazy"
              />
            </>
          ) : (
            /* Enhanced fallback with category icon and store colors */
            (() => {
              const fallback = generateFallbackImage(product) as any;
              return (
                <div className={`w-full h-full flex flex-col items-center justify-center bg-gradient-to-br ${fallback.colors.bg} to-${fallback.colors.bg.replace('bg-', '')}-100`}>
                  <div className="text-6xl mb-2 animate-float">{fallback.icon}</div>
                  <div className="text-gray-600 text-sm text-center px-4 font-medium">
                    {fallback.text}
                  </div>
                </div>
              );
            })()
          )}
          
          {/* Image overlay gradient */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/5 to-transparent pointer-events-none"></div>
        </div>

        <div className="p-4 space-y-3">
          {/* Store Badge */}
          <div className="flex items-center justify-between">
            <span className={`inline-block ${storeInfo.bgColor} ${storeInfo.color} text-xs font-semibold px-3 py-1.5 rounded-full`}>
              {storeInfo.name}
            </span>
            {product.city && (
              <span className="inline-block bg-gradient-to-r from-emerald-50 to-emerald-100 text-emerald-700 text-xs font-semibold px-3 py-1.5 rounded-full border border-emerald-200">
                🗺️ {product.city}
              </span>
            )}
            
            {/* Nutrition badges */}
            <div className="flex gap-2">
              {product.nutriscore && nutriScoreColors && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger>
                      <div className={`${nutriScoreColors.bg} ${nutriScoreColors.text} px-2 py-1 rounded-full text-xs font-bold shadow-sm`}>
                        {product.nutriscore.toUpperCase()}
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{t('productCard.nutriScore')}: {product.nutriscore.toUpperCase()}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
              
              {product.nova_group && novaColors && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger>
                      <div className={`${novaColors.bg} ${novaColors.text} px-2 py-1 rounded-full text-xs font-bold shadow-sm`}>
                        NOVA {product.nova_group}
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{t('productCard.novaGroup')}: {product.nova_group}</p>
                      <p className="text-xs">{t('productCard.novaInfo')}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
          </div>

          {/* Product Name */}
          <h3 className="text-lg font-bold text-gray-800 leading-tight line-clamp-2 group-hover:text-blue-600 transition-colors">
            {product.name}
          </h3>

          {/* Quantity */}
          <div className="text-sm text-gray-600 font-medium">{product.quantity}</div>

          {/* Price per unit */}
          {priceMetrics.pricePerStandardUnit > 0 && (
            <div className="text-sm text-gray-500 font-medium">
              {formatPrice(priceMetrics.pricePerStandardUnit)}€/{priceMetrics.standardUnit}
            </div>
          )}

          {/* Category Badge */}
          <div className="flex items-center gap-2">
            <span className="inline-block bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 text-xs font-medium px-3 py-1.5 rounded-full border border-blue-200">
              {product.category}
            </span>
          </div>

          {/* Enhanced Nutrition Facts */}
          {(product.energy_kcal || product.sugars_100g || product.salt_100g || product.saturated_fat_100g) && (
            <div className="mt-3 p-3 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg border border-gray-200">
              <div className="text-xs font-bold text-gray-700 mb-2 flex items-center gap-1">
                <span>🥗</span> {t('productCard.nutritionPer100g')}
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {product.energy_kcal && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">{t('productCard.energy')}:</span>
                    <span className="font-medium">{product.energy_kcal}kcal</span>
                  </div>
                )}
                {product.sugars_100g && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">{t('productCard.sugars')}:</span>
                    <span className="font-medium">{product.sugars_100g}g</span>
                  </div>
                )}
                {product.salt_100g && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">{t('productCard.salt')}:</span>
                    <span className="font-medium">{product.salt_100g}g</span>
                  </div>
                )}
                {product.saturated_fat_100g && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">{t('productCard.satFat')}:</span>
                    <span className="font-medium">{product.saturated_fat_100g}g</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Action Button */}
          <Button
            variant="outline"
            size="sm"
            className="mt-4 w-full bg-gradient-to-r from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 border-blue-200 text-blue-700 hover:text-blue-800 transition-all duration-200 font-medium"
            onClick={(e) => {
              e.stopPropagation();
              loadPriceHistory();
            }}
            disabled={isLoading || !product.price}
          >
            {isLoading ? (
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {t('products.loading')}
              </div>
            ) : !product.price ? (
              t('productCard.priceUnavailable')
            ) : priceAnalytics ? (
              t('productCard.refreshPriceHistory')
            ) : (
              t('productCard.viewPriceHistory')
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export { ProductCard }; 