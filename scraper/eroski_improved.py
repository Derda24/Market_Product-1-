#!/usr/bin/env python3
"""
Improved Eroski scraper with correct URLs and selectors
"""

import time
import random
import re
from playwright.sync_api import sync_playwright
from utils.db import insert_product, get_product_by_name_and_store, update_product_price, supabase
from utils.logger import log_debug_message as log

def scrape_eroski_improved(max_products=60):
    """
    Improved Eroski scraper with correct URLs
    """
    print("START Starting improved Eroski scraper...")
    
    # Correct Eroski URLs
    categories = [
        {'name': 'Frescos', 'url': 'https://supermercado.eroski.es/es/supermercado/marketplace/frescos'},
        {'name': 'Alimentación', 'url': 'https://supermercado.eroski.es/es/supermercado/marketplace/alimentacion'},
        {'name': 'Bebidas', 'url': 'https://supermercado.eroski.es/es/supermercado/marketplace/bebidas'},
        {'name': 'Congelados', 'url': 'https://supermercado.eroski.es/es/supermercado/marketplace/congelados'},
        {'name': 'Desayuno', 'url': 'https://supermercado.eroski.es/es/supermercado/marketplace/desayuno'},
        {'name': 'Lácteos', 'url': 'https://supermercado.eroski.es/es/supermercado/marketplace/lacteos'},
        {'name': 'Frutas', 'url': 'https://supermercado.eroski.es/es/supermercado/marketplace/frutas'},
        {'name': 'Verduras', 'url': 'https://supermercado.eroski.es/es/supermercado/marketplace/verduras'},
        {'name': 'Carnes', 'url': 'https://supermercado.eroski.es/es/supermercado/marketplace/carnes'},
        {'name': 'Pescados', 'url': 'https://supermercado.eroski.es/es/supermercado/marketplace/pescados'}
    ]
    
    all_products = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Set headers
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
            })
            
            for category in categories:
                print(f"SEARCH Scraping category: {category['name']}")
                print(f"🌐 Navigating to: {category['url']}")
                
                try:
                    page.goto(category['url'], timeout=15000)
                    time.sleep(3)
                    
                    print(f"Current URL: {page.url}")
                    
                    # Check if we got redirected to error page
                    if 'error' in page.url.lower() or '404' in page.url.lower():
                        print(f"WARN Got error page for {category['name']}, trying fallback URL...")
                        
                        # Try fallback URLs
                        fallback_urls = [
                            f'https://supermercado.eroski.es/es/supermercado/{category["name"].lower()}',
                            f'https://supermercado.eroski.es/c/comprar-{category["name"].lower()}/c1856',
                            'https://supermercado.eroski.es/es/supermercado/marketplace/'
                        ]
                        
                        for fallback_url in fallback_urls:
                            try:
                                page.goto(fallback_url, timeout=10000)
                                time.sleep(2)
                                if 'error' not in page.url.lower():
                                    print(f"SUCCESS Using fallback URL: {fallback_url}")
                                    break
                            except:
                                continue
                    
                    # Scroll to load products
                    print("SCROLL Scrolling to load products...")
                    for i in range(3):
                        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                        time.sleep(2)
                        print(f"CHART Scrolled {i+1}/3 times...")
                    
                    # Wait for dynamic content
                    print("WAIT Waiting for dynamic content to load...")
                    time.sleep(3)
                    
                    # Try multiple product selectors
                    product_selectors = [
                        '.product-card',
                        '[class*="ProductCard"]',
                        '[class*="product-card"]',
                        '[class*="ProductItem"]',
                        '[class*="product-item"]',
                        '[class*="ProductTile"]',
                        '[class*="product-tile"]',
                        '.product',
                        '[data-testid*="product"]',
                        '[class*="item"]'
                    ]
                    
                    products_found = False
                    for selector in product_selectors:
                        try:
                            elements = page.query_selector_all(selector)
                            if len(elements) > 0:
                                print(f"🔎 Found {len(elements)} elements with selector: {selector}")
                                products_found = True
                                
                                # Extract products
                                products = extract_eroski_products(elements, category['name'])
                                if products:
                                    all_products.extend(products)
                                    print(f"SUCCESS Extracted {len(products)} products from {category['name']}")
                                break
                        except Exception as e:
                            continue
                    
                    if not products_found:
                        print(f"ERROR No product elements found with any selector")
                        page.screenshot(path=f'eroski_debug_{category["name"]}.png')
                        
                        # Save HTML for debugging
                        html_content = page.content()
                        with open(f'eroski_debug_{category["name"]}.html', 'w', encoding='utf-8') as f:
                            f.write(html_content)
                    
                    # Random delay between categories
                    delay = random.uniform(2, 5)
                    print(f"WAIT Waiting {delay:.1f}s before next category...")
                    time.sleep(delay)
                    
                except Exception as e:
                    print(f"ERROR Error scraping {category['name']}: {e}")
                    continue
            
            browser.close()
            
            if all_products:
                return process_eroski_products(all_products)
            else:
                print("ERROR No products found from any category.")
                return 0
                
        except Exception as e:
            print(f"ERROR Eroski scraping failed: {e}")
            browser.close()
            return 0

def extract_eroski_products(elements, category_name):
    """Extract products from Eroski elements"""
    products = []
    
    for element in elements:
        try:
            # Extract product name
            name_selectors = ['h3', 'h4', '.product-name', '.product-title', '[class*="name"]', 'a']
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
            
            # Extract price
            price_selectors = ['.price', '.product-price', '[class*="price"]', '[class*="cost"]', 'span']
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
                        'store': 'Eroski',
                        'category': category_name
                    }
                    products.append(product)
                    
        except Exception as e:
            continue
    
    return products

def process_eroski_products(products):
    """Process and save Eroski products"""
    inserted_count = 0
    updated_count = 0
    skipped_count = 0
    
    print(f"BOX Processing {len(products)} products...")
    
    for i, product in enumerate(products):
        try:
            existing = get_product_by_name_and_store(product['name'], 'Eroski')
            
            if existing:
                if abs(existing['price'] - product['price']) > 0.01:
                    update_product_price(existing['id'], product['price'])
                    print(f"RETRY [{i+1}] Price updated: {product['name']} {existing['price']:.2f}€ -> {product['price']:.2f}€")
                    updated_count += 1
                else:
                    print(f"SKIP [{i+1}] No change: {product['name']}")
                    skipped_count += 1
            else:
                insert_product(
                    name=product['name'],
                    price=product['price'],
                    category=product['category'],
                    store_id='Eroski'
                )
                print(f"RETRY [{i+1}] New product: {product['name']} - {product['price']:.2f}€")
                inserted_count += 1
                
        except Exception as e:
            print(f"WARN Error processing product {i+1}: {e}")
            continue
    
    print(f"FINISH Scraper finished.")
    return inserted_count + updated_count

if __name__ == "__main__":
    scrape_eroski_improved()
