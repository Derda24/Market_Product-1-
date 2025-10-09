#!/usr/bin/env python3
"""
City-specific scraper for Spanish supermarkets
Scrapes products from different Spanish cities
"""

import time
import json
import random
import re
from playwright.sync_api import sync_playwright
from utils.db import insert_product, supabase
from utils.logger import log_debug_message as log

# Load cities data
def load_cities():
    """Load Spanish cities from JSON file"""
    try:
        with open('data/cities_es.json', 'r', encoding='utf-8') as f:
            cities = json.load(f)
        print(f"✅ Loaded {len(cities)} cities")
        return cities
    except Exception as e:
        print(f"❌ Error loading cities: {e}")
        return []

# Store configurations with city-specific URL patterns
STORE_CONFIGS = {
    'elcorte': {
        'base_url': 'https://www.elcorteingles.es/supermercado',
        'city_param': 'ciudad',  # URL parameter for city
        'categories': [
            'aceites-y-vinagres',
            'arroz-legumbres-y-pasta', 
            'azucar-cacao-y-edulcorantes',
            'conservas',
            'pan-y-reposteria',
            'salsas-condimentos-y-especias'
        ]
    },
    'carrefour': {
        'base_url': 'https://www.carrefour.es',
        'city_param': 'ciudad',
        'categories': [
            'alimentacion',
            'bebidas',
            'congelados',
            'frescos'
        ]
    },
    'mercadona': {
        'base_url': 'https://www.mercadona.es',
        'city_param': 'ciudad',
        'categories': [
            'alimentacion',
            'bebidas',
            'congelados',
            'frescos'
        ]
    }
}

def scrape_city_products(city_name, store_id='elcorte', max_products=50):
    """
    Scrape products for a specific city and store
    
    Args:
        city_name (str): Name of the city to scrape
        store_id (str): Store identifier (elcorte, carrefour, etc.)
        max_products (int): Maximum number of products to scrape
    """
    print(f"🏙️ Starting scrape for {city_name} - {store_id}")
    
    if store_id not in STORE_CONFIGS:
        print(f"❌ Unknown store: {store_id}")
        return
    
    config = STORE_CONFIGS[store_id]
    products_scraped = 0
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Set user agent to avoid detection
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            # Try to scrape from each category
            for category in config['categories']:
                if products_scraped >= max_products:
                    break
                    
                print(f"📦 Scraping category: {category}")
                
                # Build URL with city parameter
                if store_id == 'elcorte':
                    url = f"{config['base_url']}/{category}/?{config['city_param']}={city_name.lower()}"
                else:
                    url = f"{config['base_url']}/?{config['city_param']}={city_name.lower()}&categoria={category}"
                
                print(f"🔗 URL: {url}")
                
                try:
                    page.goto(url, timeout=30000)
                    page.wait_for_load_state('networkidle')
                    
                    # Wait a bit for dynamic content
                    time.sleep(2)
                    
                    # Extract products (this is a simplified version)
                    products = extract_products_from_page(page, category, store_id, city_name)
                    
                    for product in products:
                        if products_scraped >= max_products:
                            break
                            
                        try:
                            # Insert product with city information
                            insert_product(
                                name=product['name'],
                                price=product['price'],
                                category=product['category'],
                                store_id=store_id,
                                quantity=product.get('quantity'),
                                city=city_name
                            )
                            products_scraped += 1
                            print(f"✅ Scraped: {product['name']} - {product['price']}€")
                            
                        except Exception as e:
                            print(f"❌ Error inserting product: {e}")
                    
                    # Random delay between categories
                    time.sleep(random.uniform(2, 5))
                    
                except Exception as e:
                    print(f"⚠️ Error scraping category {category}: {e}")
                    continue
            
            print(f"✅ Scraping complete for {city_name}. Total products: {products_scraped}")
            
        except Exception as e:
            print(f"❌ Error during scraping: {e}")
        finally:
            browser.close()
    
    return products_scraped

def extract_products_from_page(page, category, store_id, city_name):
    """
    Extract product information from the current page
    This is a simplified version - would need to be customized per store
    """
    products = []
    
    try:
        # Wait for products to load
        page.wait_for_selector('.product-card, [data-test="product-card"], .product-item', timeout=10000)
    except:
        print("⚠️ No products found on page")
        return products
    
    # Find product elements (this would need to be customized per store)
    product_elements = page.query_selector_all('.product-card, [data-test="product-card"], .product-item')
    
    for element in product_elements[:10]:  # Limit to 10 products per category
        try:
            # Extract product name
            name_elem = element.query_selector('.product-name, .product-title, h3, h4')
            name = name_elem.inner_text().strip() if name_elem else f"Product from {city_name}"
            
            # Extract price
            price_elem = element.query_selector('.price, .product-price, [class*="price"]')
            price_text = price_elem.inner_text().strip() if price_elem else "0.00"
            
            # Clean price text
            price = float(re.sub(r'[^\d,.]', '', price_text).replace(',', '.'))
            
            # Extract quantity if available
            quantity_elem = element.query_selector('.quantity, .product-quantity, [class*="quantity"]')
            quantity = quantity_elem.inner_text().strip() if quantity_elem else None
            
            if name and price > 0:
                products.append({
                    'name': name,
                    'price': price,
                    'category': category,
                    'quantity': quantity
                })
                
        except Exception as e:
            print(f"⚠️ Error extracting product: {e}")
            continue
    
    return products

def scrape_multiple_cities(cities=None, store_id='elcorte', max_products_per_city=20):
    """
    Scrape products for multiple cities
    
    Args:
        cities (list): List of city names to scrape. If None, scrapes all cities.
        store_id (str): Store identifier
        max_products_per_city (int): Maximum products per city
    """
    if cities is None:
        cities_data = load_cities()
        cities = [city['name'] for city in cities_data[:5]]  # Start with first 5 cities
    
    print(f"🚀 Starting multi-city scrape for {len(cities)} cities")
    
    total_products = 0
    for city in cities:
        try:
            products = scrape_city_products(city, store_id, max_products_per_city)
            total_products += products
            print(f"✅ {city}: {products} products")
            
            # Delay between cities
            time.sleep(random.uniform(5, 10))
            
        except Exception as e:
            print(f"❌ Error scraping {city}: {e}")
            continue
    
    print(f"🎉 Multi-city scrape complete! Total products: {total_products}")

if __name__ == "__main__":
    # Test with a few cities
    test_cities = ['Madrid', 'Valencia', 'Sevilla']
    scrape_multiple_cities(cities=test_cities, store_id='elcorte', max_products_per_city=10)
