#!/usr/bin/env python3
"""
Carrefour City-Specific Scraper
Scrapes products from Carrefour for specific Spanish cities
"""

import time
import random
import re
from playwright.sync_api import sync_playwright
from utils.db import insert_product, get_product_by_name_and_store, update_product_price, supabase
from utils.logger import log_debug_message as log

def scrape_carrefour_city(city_name="Barcelona", max_products=50):
    """
    Scrape Carrefour products for a specific city
    
    Args:
        city_name (str): Name of the city to scrape
        max_products (int): Maximum number of products to scrape
    """
    print(f"START Starting Carrefour scraper for {city_name}...")
    
    # City-specific store codes for Carrefour
    city_store_codes = {
        'Madrid': 'madrid-centro',
        'Barcelona': 'barcelona-centro',
        'Valencia': 'valencia-centro', 
        'Sevilla': 'sevilla-centro',
        'Bilbao': 'bilbao-centro',
        'Málaga': 'malaga-centro',
        'Zaragoza': 'zaragoza-centro',
        'Murcia': 'murcia-centro',
        'Palma': 'palma-centro',
        'Las Palmas': 'las-palmas-centro'
    }
    
    store_code = city_store_codes.get(city_name, 'barcelona-centro')
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Set user agent
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            print(f"🌍 Scraping Carrefour for {city_name} (store: {store_code})")
            
            # Go to Carrefour main page
            page.goto("https://www.carrefour.es")
            print("SUCCESS Page loaded successfully!")

            # Wait for page to load
            page.wait_for_load_state("networkidle", timeout=30000)

            # Try to set location/store
            try:
                # Look for store/location selector
                store_selector = page.query_selector('[data-test="store-selector"], .store-selector, [class*="store"]')
                if store_selector:
                    print("🏪 Found store selector, setting location...")
                    store_selector.click()
                    time.sleep(2)
                    
                    # Try to find and click on the city store
                    city_option = page.query_selector(f'text="{city_name}"')
                    if city_option:
                        city_option.click()
                        time.sleep(3)
                        print(f"✅ Store set to {city_name}")
                    else:
                        print(f"⚠️ Could not find {city_name} store")
                else:
                    print("ℹ️ No store selector found, using default store")
            except Exception as e:
                print(f"⚠️ Could not set store: {e}")

            # Navigate to food categories
            categories = [
                "alimentacion",
                "bebidas", 
                "congelados",
                "frescos"
            ]
            
            inserted_count = 0
            updated_count = 0
            skipped_count = 0
            
            for category in categories:
                try:
                    print(f"📦 Scraping category: {category}")
                    
                    # Build category URL
                    category_url = f"https://www.carrefour.es/c/{category}"
                    page.goto(category_url)
                    page.wait_for_load_state("networkidle", timeout=30000)
                    
                    # Wait for products to load
                    page.wait_for_selector('.product-card, [data-test="product-card"]', timeout=15000)
                    
                    # Find product elements
                    product_elements = page.query_selector_all('.product-card, [data-test="product-card"]')
                    if not product_elements:
                        product_elements = page.query_selector_all('[class*="product"]')
                    
                    if not product_elements:
                        print(f"⚠️ No products found for category {category}")
                        continue
                    
                    print(f"🔎 Found {len(product_elements)} products in {category}")
                    
                    # Process products
                    for i, product in enumerate(product_elements[:max_products//len(categories)], 1):
                        try:
                            # Product name
                            name_element = product.query_selector('.product-name, .product-title, h3, h4')
                            if not name_element:
                                continue
                            name = name_element.inner_text().strip()
                            
                            # Add city indicator
                            city_name_clean = name.replace(f" ({city_name})", "").strip()
                            final_name = f"{city_name_clean} ({city_name})"
                            
                            # Product price
                            price_element = product.query_selector('.price, .product-price, [class*="price"]')
                            if not price_element:
                                continue
                            
                            price_text = price_element.inner_text().strip()
                            price_match = re.search(r'(\d+[.,]\d+)', price_text)
                            if not price_match:
                                continue
                            
                            price = float(price_match.group(1).replace(',', '.'))
                            
                            # Product quantity
                            quantity_element = product.query_selector('.quantity, .product-quantity, [class*="quantity"]')
                            quantity = quantity_element.inner_text().strip() if quantity_element else None
                            
                            # Check if product already exists
                            existing_product = get_product_by_name_and_store(final_name, "carrefour")
                            
                            if existing_product:
                                # Update price if different
                                if abs(existing_product['price'] - price) > 0.01:
                                    update_product_price(existing_product['id'], price, "carrefour")
                                    updated_count += 1
                                    print(f"✅ Updated: {final_name} - {price}€")
                                else:
                                    skipped_count += 1
                            else:
                                # Insert new product with city information
                                insert_product(
                                    name=final_name,
                                    price=price,
                                    category=category,
                                    store_id="carrefour",
                                    quantity=quantity,
                                    city=city_name
                                )
                                inserted_count += 1
                                print(f"✅ Inserted: {final_name} - {price}€")
                            
                            # Small delay
                            time.sleep(random.uniform(0.1, 0.3))
                            
                        except Exception as e:
                            print(f"ERROR Product {i}: {str(e)}")
                            continue
                    
                    # Delay between categories
                    time.sleep(random.uniform(2, 5))
                    
                except Exception as e:
                    print(f"⚠️ Error scraping category {category}: {e}")
                    continue
            
            print(f"🎉 Carrefour scraping for {city_name} complete!")
            print(f"📊 Results: {inserted_count} inserted, {updated_count} updated, {skipped_count} skipped")

        except Exception as e:
            print(f"ERROR Carrefour scraping failed for {city_name}: {str(e)}")
        finally:
            browser.close()

    return inserted_count + updated_count

def scrape_multiple_cities_carrefour(cities=None, max_products_per_city=40):
    """
    Scrape Carrefour for multiple cities
    
    Args:
        cities (list): List of city names to scrape
        max_products_per_city (int): Maximum products per city
    """
    if cities is None:
        cities = ['Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Bilbao']
    
    print(f"🚀 Starting multi-city Carrefour scraping for {len(cities)} cities")
    
    total_products = 0
    for city in cities:
        try:
            print(f"\n🏙️ Scraping {city}...")
            products = scrape_carrefour_city(city, max_products_per_city)
            total_products += products
            print(f"✅ {city}: {products} products processed")
            
            # Delay between cities
            delay = random.uniform(15, 25)
            print(f"⏳ Waiting {delay:.1f}s before next city...")
            time.sleep(delay)
            
        except Exception as e:
            print(f"❌ Error scraping {city}: {e}")
            continue
    
    print(f"\n🎉 Multi-city Carrefour scraping complete! Total products: {total_products}")

if __name__ == "__main__":
    # Test with a few cities
    test_cities = ['Madrid', 'Barcelona', 'Valencia']
    scrape_multiple_cities_carrefour(cities=test_cities, max_products_per_city=20)
