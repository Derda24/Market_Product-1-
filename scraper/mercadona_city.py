#!/usr/bin/env python3
"""
Mercadona City-Specific Scraper
Scrapes products from Mercadona for specific Spanish cities
"""

import time
import random
from playwright.sync_api import sync_playwright
from utils.db import insert_product, get_product_by_name_and_store, update_product_price
from utils.proxy_handler import get_browser_with_proxy

def scrape_mercadona_city(city_name="Barcelona", max_products=50):
    """
    Scrape Mercadona products for a specific city
    
    Args:
        city_name (str): Name of the city to scrape
        max_products (int): Maximum number of products to scrape
    """
    print(f"START Starting Mercadona scraper for {city_name}...")
    
    # City-specific URL parameters (Mercadona uses postal codes for location)
    city_postal_codes = {
        'Madrid': '28001',
        'Barcelona': '08001', 
        'Valencia': '46001',
        'Sevilla': '41001',
        'Bilbao': '48001',
        'Málaga': '29001',
        'Zaragoza': '50001',
        'Murcia': '30001',
        'Palma': '07001',
        'Las Palmas': '35001'
    }
    
    postal_code = city_postal_codes.get(city_name, '08001')  # Default to Barcelona
    
    with sync_playwright() as p:
        browser = get_browser_with_proxy(p)
        page = browser.new_page()
        
        try:
            # Set location/city for Mercadona
            print(f"🌍 Setting location to {city_name} (postal code: {postal_code})")
            
            # Go to Mercadona main page
            page.goto("https://tienda.mercadona.es/")
            print("SUCCESS Page loaded successfully!")

            # Wait for page to load
            page.wait_for_load_state("networkidle", timeout=120000)

            # Try to set location if there's a location selector
            try:
                # Look for location selector or postal code input
                location_selector = page.query_selector('[data-test="location-selector"], .location-selector, [class*="location"]')
                if location_selector:
                    print("📍 Found location selector, setting city...")
                    location_selector.click()
                    time.sleep(2)
                    
                    # Try to find and click on the city
                    city_option = page.query_selector(f'text="{city_name}"')
                    if city_option:
                        city_option.click()
                        time.sleep(3)
                        print(f"✅ Location set to {city_name}")
                    else:
                        print(f"⚠️ Could not find {city_name} in location selector")
                else:
                    print("ℹ️ No location selector found, using default location")
            except Exception as e:
                print(f"⚠️ Could not set location: {e}")

            # Wait for product cards to load
            page.wait_for_selector('.product-cell', timeout=60000)

            products = page.query_selector_all(".product-cell")
            print(f"🔎 Found {len(products)} products for {city_name}")

            inserted_count = 0
            updated_count = 0
            skipped_count = 0

            for i, product in enumerate(products[:max_products], 1):
                try:
                    # Product name
                    name_element = product.query_selector(".product-cell__description-name")
                    if not name_element:
                        print(f"WARN Product {i}: Name not found!")
                        continue
                    name = name_element.inner_text().strip()

                    # Add city indicator to product name
                    city_name_clean = name.replace(f" ({city_name})", "").strip()
                    final_name = f"{city_name_clean} ({city_name})"

                    # Product image
                    img_element = product.query_selector("img")
                    if img_element:
                        image_url = img_element.get_attribute("src")
                    else:
                        image_url = None
                        print(f"WARN Product {i} '{final_name}': Image not found!")

                    # Try different price selectors
                    price_element = product.query_selector(".product-price__unit-price")
                    if not price_element:
                        price_element = product.query_selector(".product-cell__price-price")

                    if not price_element:
                        print(f"WARN Product {i} '{final_name}': Price not found!")
                        continue

                    price_text = price_element.inner_text().strip()
                    
                    # Clean price text
                    import re
                    price_match = re.search(r'(\d+[.,]\d+)', price_text)
                    if not price_match:
                        print(f"WARN Product {i} '{final_name}': Could not parse price '{price_text}'")
                        continue
                    
                    price = float(price_match.group(1).replace(',', '.'))

                    # Product quantity
                    quantity_element = product.query_selector(".product-cell__description-quantity")
                    quantity = quantity_element.inner_text().strip() if quantity_element else None

                    # Category (try to determine from context or use default)
                    category = "alimentacion"  # Default category for Mercadona

                    # Check if product already exists
                    existing_product = get_product_by_name_and_store(final_name, "mercadona")
                    
                    if existing_product:
                        # Update price if different
                        if abs(existing_product['price'] - price) > 0.01:
                            update_product_price(existing_product['id'], price, "mercadona")
                            updated_count += 1
                            print(f"✅ Updated: {final_name} - {price}€")
                        else:
                            skipped_count += 1
                            print(f"⏭️ Skipped: {final_name} - Price unchanged")
                    else:
                        # Insert new product with city information
                        insert_product(
                            name=final_name,
                            price=price,
                            category=category,
                            store_id="mercadona",
                            quantity=quantity,
                            city=city_name
                        )
                        inserted_count += 1
                        print(f"✅ Inserted: {final_name} - {price}€")

                    # Small delay between products
                    time.sleep(random.uniform(0.1, 0.3))

                except Exception as e:
                    print(f"ERROR Product {i}: {str(e)}")
                    continue

            print(f"🎉 Mercadona scraping for {city_name} complete!")
            print(f"📊 Results: {inserted_count} inserted, {updated_count} updated, {skipped_count} skipped")

        except Exception as e:
            print(f"ERROR Mercadona scraping failed for {city_name}: {str(e)}")
        finally:
            browser.close()

    return inserted_count + updated_count

def scrape_multiple_cities_mercadona(cities=None, max_products_per_city=30):
    """
    Scrape Mercadona for multiple cities
    
    Args:
        cities (list): List of city names to scrape
        max_products_per_city (int): Maximum products per city
    """
    if cities is None:
        cities = ['Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Bilbao']
    
    print(f"🚀 Starting multi-city Mercadona scraping for {len(cities)} cities")
    
    total_products = 0
    for city in cities:
        try:
            print(f"\n🏙️ Scraping {city}...")
            products = scrape_mercadona_city(city, max_products_per_city)
            total_products += products
            print(f"✅ {city}: {products} products processed")
            
            # Delay between cities
            delay = random.uniform(10, 20)
            print(f"⏳ Waiting {delay:.1f}s before next city...")
            time.sleep(delay)
            
        except Exception as e:
            print(f"❌ Error scraping {city}: {e}")
            continue
    
    print(f"\n🎉 Multi-city Mercadona scraping complete! Total products: {total_products}")

if __name__ == "__main__":
    # Test with a few cities
    test_cities = ['Madrid', 'Barcelona', 'Valencia']
    scrape_multiple_cities_mercadona(cities=test_cities, max_products_per_city=20)
