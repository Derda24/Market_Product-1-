// Image quality assessment and fallback utilities

/**
 * Assess image quality based on various factors
 * @param {string} imageUrl - The image URL to assess
 * @param {Object} product - The product object
 * @returns {Object} Quality assessment result
 */
export const assessImageQuality = (imageUrl, product) => {
  if (!imageUrl) {
    return {
      score: 0,
      shouldUseFallback: true,
      reason: 'No image URL provided'
    };
  }

  let score = 100;
  const issues = [];

  // Check for common low-quality indicators
  const url = imageUrl.toLowerCase();
  
  // Check for placeholder or default images
  if (url.includes('placeholder') || url.includes('default') || url.includes('no-image')) {
    score -= 50;
    issues.push('Placeholder image detected');
  }

  // Check for very small images (likely low quality)
  if (url.includes('thumb') || url.includes('small') || url.includes('mini')) {
    score -= 30;
    issues.push('Small image detected');
  }

  // Check for generic product images
  if (url.includes('generic') || url.includes('stock')) {
    score -= 40;
    issues.push('Generic stock image');
  }

  // Check for watermarked images
  if (url.includes('watermark') || url.includes('logo')) {
    score -= 20;
    issues.push('Watermarked image');
  }

  // Check for very long URLs (might be data URLs or complex paths)
  if (imageUrl.length > 500) {
    score -= 10;
    issues.push('Complex image URL');
  }

  return {
    score: Math.max(0, score),
    shouldUseFallback: score < 30,
    reason: issues.length > 0 ? issues.join(', ') : 'Good quality image',
    issues
  };
};

/**
 * Get category-based placeholder icon
 * @param {string} category - Product category
 * @returns {string} Emoji icon for the category
 */
export const getCategoryIcon = (category) => {
  const categoryIcons = {
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
    'Bakery': '🥐',
    'Deli': '🥪',
    'Organic': '🌱',
    'Gluten Free': '🌾',
    'Vegan': '🌿',
    'default': '🛍️'
  };

  return categoryIcons[category] || categoryIcons.default;
};

/**
 * Get store-specific color scheme
 * @param {string} storeId - Store identifier
 * @returns {Object} Color scheme object
 */
export const getStoreColors = (storeId) => {
  const storeColors = {
    'lidl.es': { 
      primary: 'text-blue-600', 
      bg: 'bg-blue-50',
      gradient: 'from-blue-400 to-blue-600'
    },
    'carrefour.es': { 
      primary: 'text-red-600', 
      bg: 'bg-red-50',
      gradient: 'from-red-400 to-red-600'
    },
    'aldi': { 
      primary: 'text-orange-600', 
      bg: 'bg-orange-50',
      gradient: 'from-orange-400 to-orange-600'
    },
    'bonarea': { 
      primary: 'text-green-600', 
      bg: 'bg-green-50',
      gradient: 'from-green-400 to-green-600'
    },
    'bonpreu': { 
      primary: 'text-purple-600', 
      bg: 'bg-purple-50',
      gradient: 'from-purple-400 to-purple-600'
    },
    'condisline': { 
      primary: 'text-indigo-600', 
      bg: 'bg-indigo-50',
      gradient: 'from-indigo-400 to-indigo-600'
    },
    'mercadona.es': { 
      primary: 'text-pink-600', 
      bg: 'bg-pink-50',
      gradient: 'from-pink-400 to-pink-600'
    },
    'El Corte Inglés': { 
      primary: 'text-yellow-600', 
      bg: 'bg-yellow-50',
      gradient: 'from-yellow-400 to-yellow-600'
    },
    'alcampo': { 
      primary: 'text-teal-600', 
      bg: 'bg-teal-50',
      gradient: 'from-teal-400 to-teal-600'
    },
    'dia.es': { 
      primary: 'text-gray-600', 
      bg: 'bg-gray-50',
      gradient: 'from-gray-400 to-gray-600'
    }
  };

  return storeColors[storeId] || {
    primary: 'text-gray-600',
    bg: 'bg-gray-50',
    gradient: 'from-gray-400 to-gray-600'
  };
};

/**
 * Generate a fallback image component
 * @param {Object} product - Product object
 * @returns {Object} Fallback image configuration
 */
export const generateFallbackImage = (product) => {
  const icon = getCategoryIcon(product.category);
  const colors = getStoreColors(product.store_id);
  
  return {
    icon,
    colors,
    background: `bg-gradient-to-br from-${colors.bg.replace('bg-', '')} to-${colors.bg.replace('bg-', '')} opacity-80`,
    text: product.category
  };
};

/**
 * Check if image should be replaced with fallback
 * @param {string} imageUrl - Image URL
 * @param {Object} product - Product object
 * @returns {boolean} Whether to use fallback
 */
export const shouldUseImageFallback = (imageUrl, product) => {
  const assessment = assessImageQuality(imageUrl, product);
  return assessment.shouldUseFallback;
}; 