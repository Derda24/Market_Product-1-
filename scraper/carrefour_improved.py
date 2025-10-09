#!/usr/bin/env python3
"""
Improved Carrefour scraper with better error handling and alternative approaches
"""

import time
import random
import re
from playwright.sync_api import sync_playwright
from utils.db import insert_product, get_product_by_name_and_store, update_product_price, supabase
from utils.logger import log_debug_message as log

def scrape_carrefour_improved(city_name="Barcelona", max_products=50):
    """
    Improved Carrefour scraper with multiple fallback strategies
    """
    print(f"START Starting improved Carrefour scraper for {city_name}...")
    
    # City-specific store codes
    city_store_codes = {
        'Madrid': 'madrid-centro',
        'Barcelona': 'barcelona-centro',
        'Valencia': 'valencia-centro', 
        'Sevilla': 'sevilla-centro',
        'Bilbao': 'bilbao-centro',
        'Málaga': 'malaga-centro',
        'Zaragoza': 'zaragoza-centro',
        'Murcia': 'murcia-centro',
        'Palma': 'palma-centro'
    }
    
    store_code = city_store_codes.get(city_name, 'barcelona-centro')
    
    # Try multiple URLs and approaches
    urls_to_try = [
        f'https://www.carrefour.es/c/alimentacion?store={store_code}',
        f'https://www.carrefour.es/c/alimentacion',
        'https://www.carrefour.es/c/alimentacion',
        'https://www.carrefour.es/supermercado/alimentacion',
        'https://tienda.carrefour.es/alimentacion'
    ]
    
    with sync_playwright() as p:
        # Try different browser configurations
        browser_configs = [
            {'headless': True, 'args': ['--no-sandbox', '--disable-blink-features=AutomationControlled']},
            {'headless': False, 'args': ['--no-sandbox']},
            {'headless': True, 'args': ['--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36']}
        ]
        
        for config_idx, browser_config in enumerate(browser_configs):
            print(f"Trying browser config {config_idx + 1}/3...")
            
            try:
                browser = p.chromium.launch(**browser_config)
                page = browser.new_page()
                
                # Set realistic headers
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                })
                
                for url_idx, url in enumerate(urls_to_try):
                    print(f"  Trying URL {url_idx + 1}/{len(urls_to_try)}: {url}")
                    
                    try:
                        response = page.goto(url, timeout=15000, wait_until='domcontentloaded')
                        
                        # Check if we got blocked
                        if 'cloudflare' in page.url.lower() or 'attention required' in page.title().lower():
                            print(f"    ❌ Blocked by Cloudflare")
                            continue
                        
                        if response and response.status == 200:
                            print(f"    ✅ Successfully loaded: {page.url}")
                            
                            # Wait for content to load
                            time.sleep(5)
                            
                            # Try multiple product selectors
                            product_selectors = [
                                '.product-card',
                                '[data-test="product-card"]',
                                '[class*="ProductCard"]',
                                '[class*="product-card"]',
                                '[class*="ProductTile"]',
                                '[class*="product-tile"]',
                                '[class*="ProductItem"]',
                                '[class*="product-item"]',
                                '.product',
                                '[data-testid*="product"]',
                                '[class*="item"]',
                                '[class*="card"]'
                            ]
                            
                            products_found = False
                            for selector in product_selectors:
                                try:
                                    elements = page.query_selector_all(selector)
                                    if len(elements) > 0:
                                        print(f"    🎯 Found {len(elements)} products with selector: {selector}")
                                        products_found = True
                                        
                                        # Extract products
                                        products = extract_products_improved(page, elements, city_name)
                                        if products:
                                            result = process_products(products, city_name)
                                            browser.close()
                                            return result
                                        break
                                except Exception as e:
                                    continue
                            
                            if not products_found:
                                print(f"    ⚠️ No products found with any selector")
                                # Save debug info
                                page.screenshot(path=f'carrefour_debug_{city_name}_{config_idx}.png')
                                html_content = page.content()
                                with open(f'carrefour_debug_{city_name}_{config_idx}.html', 'w', encoding='utf-8') as f:
                                    f.write(html_content)
                        else:
                            print(f"    ❌ Failed to load: {response.status if response else 'No response'}")
                            
                    except Exception as e:
                        print(f"    ❌ Error loading URL: {str(e)[:100]}")
                        continue
                
                browser.close()
                
            except Exception as e:
                print(f"Browser config {config_idx + 1} failed: {e}")
                try:
                    browser.close()
                except:
                    pass
                continue
        
        print(f"❌ All attempts failed for {city_name}")
        return 0

def extract_products_improved(page, elements, city_name):
    """Extract products with improved error handling"""
    products = []
    
    for i, element in enumerate(elements[:max_products]):
        try:
            # Try multiple name selectors
            name_selectors = [
                'h3', 'h4', '.product-name', '.product-title', 
                '[class*="name"]', '[class*="title"]', 'a', 'span'
            ]
            
            name = None
            for selector in name_selectors:
                try:
                    name_elem = element.query_selector(selector)
                    if name_elem and name_elem.inner_text().strip():
                        name = name_elem.inner_text().strip()
                        break
                except:
                    continue
            
            if not name:
                continue
            
            # Try multiple price selectors
            price_selectors = [
                '.price', '.product-price', '[class*="price"]', 
                '[class*="cost"]', '.amount', 'span'
            ]
            
            price_text = None
            for selector in price_selectors:
                try:
                    price_elem = element.query_selector(selector)
                    if price_elem:
                        price_text = price_elem.inner_text().strip()
                        if '€' in price_text or re.search(r'\d+[,.]\d+', price_text):
                            break
                except:
                    continue
            
            if price_text:
                # Extract numeric price
                price_match = re.search(r'(\d+[,.]?\d*)\s*€', price_text)
                if price_match:
                    price = float(price_match.group(1).replace(',', '.'))
                    
                    product = {
                        'name': name,
                        'price': price,
                        'store': 'Carrefour',
                        'city': city_name,
                        'category': 'alimentacion'
                    }
                    products.append(product)
                    
        except Exception as e:
            print(f"Error extracting product {i}: {e}")
            continue
    
    return products

def process_products(products, city_name):
    """Process and save products to database"""
    inserted_count = 0
    updated_count = 0
    skipped_count = 0
    
    for product in products:
        try:
            existing = get_product_by_name_and_store(product['name'], 'Carrefour', city_name)
            
            if existing:
                if abs(existing['price'] - product['price']) > 0.01:
                    update_product_price(existing['id'], product['price'])
                    print(f"✅ Updated: {product['name']} ({city_name}) - {product['price']:.2f}€")
                    updated_count += 1
                else:
                    print(f"⏭️ Skipped: {product['name']} ({city_name}) - Price unchanged")
                    skipped_count += 1
            else:
                insert_product(
                    name=product['name'],
                    price=product['price'],
                    store='Carrefour',
                    city=city_name,
                    category=product['category']
                )
                print(f"🆕 Inserted: {product['name']} ({city_name}) - {product['price']:.2f}€")
                inserted_count += 1
                
        except Exception as e:
            print(f"❌ Error processing {product['name']}: {e}")
            continue
    
    print(f"🎉 Carrefour scraping for {city_name} complete!")
    print(f"📊 Results: {inserted_count} inserted, {updated_count} updated, {skipped_count} skipped")
    
    return inserted_count + updated_count

if __name__ == "__main__":
    scrape_carrefour_improved()
