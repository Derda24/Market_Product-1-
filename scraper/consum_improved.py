#!/usr/bin/env python3
"""
Improved Consum scraper with better JavaScript handling
"""

import time
import random
import re
from playwright.sync_api import sync_playwright
from utils.db import insert_product, get_product_by_name_and_store, update_product_price, supabase
from utils.logger import log_debug_message as log

def scrape_consum_improved(max_products=70):
    """
    Improved Consum scraper with better JavaScript handling
    """
    print("START Starting improved Consum scraper...")
    
    categories = [
        {'name': 'Frescos', 'url': 'https://www.consum.es/frescos'},
        {'name': 'Alimentación', 'url': 'https://www.consum.es/alimentacion'},
        {'name': 'Bebidas', 'url': 'https://www.consum.es/bebidas'},
        {'name': 'Congelados', 'url': 'https://www.consum.es/congelados'},
        {'name': 'Desayuno', 'url': 'https://www.consum.es/desayuno'},
        {'name': 'Lácteos', 'url': 'https://www.consum.es/lacteos'},
        {'name': 'Frutas', 'url': 'https://www.consum.es/frutas'},
        {'name': 'Verduras', 'url': 'https://www.consum.es/verduras'},
        {'name': 'Carnes', 'url': 'https://www.consum.es/carnes'},
        {'name': 'Pescados', 'url': 'https://www.consum.es/pescados'}
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
                    time.sleep(5)  # Longer wait for JavaScript
                    
                    print(f"Current URL: {page.url}")
                    
                    # Wait for JavaScript to load
                    print("WAIT Waiting for JavaScript to load...")
                    page.wait_for_load_state('networkidle', timeout=10000)
                    
                    # Try to click "Load more" or similar buttons
                    try:
                        load_more_selectors = [
                            'button[class*="load"]',
                            'button[class*="more"]',
                            'button[class*="show"]',
                            '.load-more',
                            '.show-more',
                            '[class*="LoadMore"]'
                        ]
                        
                        for selector in load_more_selectors:
                            try:
                                button = page.query_selector(selector)
                                if button and button.is_visible():
                                    button.click()
                                    print(f"🖱️ Clicked load more button: {selector}")
                                    time.sleep(3)
                                    break
                            except:
                                continue
                    except:
                        pass
                    
                    # Scroll to load products
                    print("SCROLL Scrolling to load products...")
                    for i in range(5):  # More scrolls for JavaScript-heavy sites
                        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                        time.sleep(2)
                        print(f"CHART Scrolled {i+1}/5 times...")
                        
                        # Check if new content loaded
                        current_height = page.evaluate('document.body.scrollHeight')
                        if i > 0 and current_height == prev_height:
                            print("No new content detected, stopping scroll")
                            break
                        prev_height = current_height
                    
                    # Wait for dynamic content
                    print("WAIT Waiting for dynamic content to load...")
                    time.sleep(5)
                    
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
                        '[class*="item"]',
                        '[class*="card"]',
                        '[class*="Product"]',
                        '.item',
                        '.card'
                    ]
                    
                    products_found = False
                    for selector in product_selectors:
                        try:
                            elements = page.query_selector_all(selector)
                            if len(elements) > 0:
                                print(f"🔎 Found {len(elements)} elements with selector: {selector}")
                                products_found = True
                                
                                # Extract products
                                products = extract_consum_products(elements, category['name'])
                                if products:
                                    all_products.extend(products)
                                    print(f"SUCCESS Extracted {len(products)} products from {category['name']}")
                                break
                        except Exception as e:
                            continue
                    
                    if not products_found:
                        print(f"ERROR No product elements found with any selector")
                        page.screenshot(path=f'consum_debug_{category["name"]}.png')
                        
                        # Save HTML for debugging
                        html_content = page.content()
                        with open(f'consum_debug_{category["name"]}.html', 'w', encoding='utf-8') as f:
                            f.write(html_content)
                        
                        # Try fallback approach - look for any clickable elements
                        print("RETRY Trying fallback approach...")
                        fallback_elements = page.query_selector_all('a, button, [role="button"]')
                        if fallback_elements:
                            print(f"Found {len(fallback_elements)} clickable elements, trying to find products...")
                            # Look for product-like text in these elements
                            for elem in fallback_elements[:20]:  # Check first 20
                                try:
                                    text = elem.inner_text().strip()
                                    if text and len(text) > 5 and len(text) < 100:
                                        # Check if it looks like a product name
                                        if any(keyword in text.lower() for keyword in ['€', 'kg', 'g', 'ml', 'l', 'unidad', 'pack']):
                                            print(f"Potential product: {text[:50]}...")
                                except:
                                    continue
                    
                    # Random delay between categories
                    delay = random.uniform(3, 7)
                    print(f"WAIT Waiting {delay:.1f}s before next category...")
                    time.sleep(delay)
                    
                except Exception as e:
                    print(f"ERROR Error scraping {category['name']}: {e}")
                    continue
            
            browser.close()
            
            if all_products:
                return process_consum_products(all_products)
            else:
                print("ERROR No products found from any category.")
                return 0
                
        except Exception as e:
            print(f"ERROR Consum scraping failed: {e}")
            browser.close()
            return 0

def extract_consum_products(elements, category_name):
    """Extract products from Consum elements"""
    products = []
    
    for element in elements:
        try:
            # Extract product name
            name_selectors = ['h3', 'h4', 'h5', '.product-name', '.product-title', '[class*="name"]', 'a', 'span', 'div']
            name = None
            
            for selector in name_selectors:
                try:
                    name_elem = element.query_selector(selector)
                    if name_elem and name_elem.inner_text().strip():
                        text = name_elem.inner_text().strip()
                        # Filter out very short or very long text
                        if 5 < len(text) < 200 and not text.isdigit():
                            name = text
                            break
                except:
                    continue
            
            # If no specific name element found, try getting text from the whole element
            if not name:
                try:
                    text = element.inner_text().strip()
                    # Look for product-like text
                    if 5 < len(text) < 200 and any(keyword in text.lower() for keyword in ['€', 'kg', 'g', 'ml', 'l']):
                        # Split by common separators to get the name part
                        lines = text.split('\n')
                        for line in lines:
                            line = line.strip()
                            if 5 < len(line) < 100 and not line.isdigit():
                                name = line
                                break
                except:
                    pass
            
            if not name:
                continue
            
            # Extract price
            price_selectors = ['.price', '.product-price', '[class*="price"]', '[class*="cost"]', 'span', 'div']
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
            
            # If no specific price element found, look in the whole element text
            if not price_text:
                try:
                    text = element.inner_text()
                    price_match = re.search(r'(\d+[,.]?\d*)\s*€', text)
                    if price_match:
                        price_text = price_match.group(0)
                except:
                    pass
            
            if price_text:
                # Extract numeric price
                price_match = re.search(r'(\d+[,.]?\d*)\s*€', price_text)
                if price_match:
                    price = float(price_match.group(1).replace(',', '.'))
                    
                    product = {
                        'name': name,
                        'price': price,
                        'store': 'Consum',
                        'category': category_name
                    }
                    products.append(product)
                    
        except Exception as e:
            continue
    
    return products

def process_consum_products(products):
    """Process and save Consum products"""
    inserted_count = 0
    updated_count = 0
    skipped_count = 0
    
    print(f"BOX Processing {len(products)} products...")
    
    for i, product in enumerate(products):
        try:
            existing = get_product_by_name_and_store(product['name'], 'Consum')
            
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
                    store_id='Consum'
                )
                print(f"RETRY [{i+1}] New product: {product['name']} - {product['price']:.2f}€")
                inserted_count += 1
                
        except Exception as e:
            print(f"WARN Error processing product {i+1}: {e}")
            continue
    
    print(f"FINISH Scraper finished.")
    return inserted_count + updated_count

if __name__ == "__main__":
    scrape_consum_improved()
