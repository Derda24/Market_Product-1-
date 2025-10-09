# Image API Setup Guide

## Overview
This guide helps you set up the required API keys for high-quality product images.

## Required APIs

### 1. Google Custom Search API
**Cost**: Free tier includes 100 queries/day
**Setup**:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable "Custom Search API"
4. Create credentials (API Key)
5. Go to [Google Custom Search Engine](https://cse.google.com/)
6. Create a new search engine
7. Enable "Image Search"
8. Get your Search Engine ID (cx)

**Environment Variables**:
```
GOOGLE_API_KEY=your_api_key_here
GOOGLE_CSE_ID=your_search_engine_id_here
```

### 2. Bing Image Search API
**Cost**: Free tier includes 1000 transactions/month
**Setup**:
1. Go to [Microsoft Azure Portal](https://portal.azure.com/)
2. Create a new resource
3. Search for "Bing Search v7"
4. Create the resource
5. Get your API key

**Environment Variables**:
```
BING_API_KEY=your_bing_api_key_here
```

### 3. Open Food Facts API
**Cost**: Free
**Setup**: No API key required, but you can contribute to their database.

## Quality Improvements Made

### 1. Higher Image Resolution
- Google: Changed from `medium` to `large` images
- Bing: Added `size: 'Large'` parameter
- Minimum dimensions: 300x300 pixels

### 2. Better Search Queries
- Added e-commerce site focus
- Improved product name cleaning
- Brand name preservation
- Multiple search strategies

### 3. Quality Filtering
- Aspect ratio checks (prevent distorted images)
- File size requirements
- Source preference (e-commerce > product databases > generic)

### 4. New Image Sources
- E-commerce sites (Amazon, Mercadona, Carrefour, Eroski)
- Open Food Facts (product database)
- Google Custom Search (high quality)
- Bing Image Search (high quality)
- Unsplash (fallback)

## Testing

Run the test script to check image quality:
```bash
python test_image_quality.py
```

## Usage

Update all product images:
```bash
python update_product_images.py
```

Update specific products:
```python
from update_product_images import ProductImageUpdater

updater = ProductImageUpdater()
image_url = updater.find_product_image("Product Name")
```

## Cost Optimization

1. **Google API**: 100 free queries/day
2. **Bing API**: 1000 free transactions/month
3. **Open Food Facts**: Unlimited free usage
4. **E-commerce search**: Uses Google API with site restrictions

## Troubleshooting

### No images found
- Check API keys are set correctly
- Verify internet connection
- Check API quotas

### Low quality images
- Ensure you have Google and Bing API keys
- Check that CSE is configured for image search
- Verify search engine includes image search

### Rate limiting
- Add delays between requests
- Use batch processing
- Monitor API quotas
