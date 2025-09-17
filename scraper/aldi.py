import time
import re
from playwright.sync_api import sync_playwright
from utils.db import insert_product, get_product_by_name_and_store, update_product_price
from utils.logger import log_debug_message
from utils.proxy_handler import get_browser_with_proxy

def scroll_to_load_all(page, scroll_pause=3, max_scrolls=30):
    """Enhanced scrolling with better detection of new content"""
    prev_height = 0
    prev_product_count = 0
    
    for i in range(max_scrolls):
        # Scroll down
        page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        time.sleep(scroll_pause)
        
        # Check if new content loaded
        curr_height = page.evaluate("document.body.scrollHeight")
        curr_products = len(page.query_selector_all('.mod-article-tile'))
        
        print(f"Scroll {i + 1}/{max_scrolls}: Height={curr_height}, Products={curr_products}")
        
        # Stop if no new content or products
        if curr_height == prev_height and curr_products == prev_product_count:
            print("No new content detected, stopping scroll")
            break
            
        prev_height = curr_height
        prev_product_count = curr_products
        
        # Wait a bit more for dynamic content
        time.sleep(2)

def extract_price(price_text):
    """Extract price from various price formats"""
    if not price_text:
        return None
    
    # Remove common price indicators and clean up
    price_text = price_text.strip()
    price_text = re.sub(r'[^\d,.]', '', price_text)
    price_text = price_text.replace(',', '.')
    
    try:
        return float(price_text)
    except ValueError:
        return None

def scrape_product_page(page, product_url, product_name):
    """Scrape individual product page for more details"""
    try:
        page.goto(product_url, timeout=30000)
        page.wait_for_timeout(3000)
        
        # Look for additional product information
        product_info = {}
        
        # Try to find price
        price_selectors = ['.price', '.price__wrapper', '[class*="price"]']
        for selector in price_selectors:
            price_el = page.query_selector(selector)
            if price_el:
                price_text = price_el.inner_text().strip()
                price = extract_price(price_text)
                if price:
                    product_info['price'] = price
                    break
        
        # Try to find description
        desc_selectors = ['.description', '.product-description', '[class*="description"]']
        for selector in desc_selectors:
            desc_el = page.query_selector(selector)
            if desc_el:
                product_info['description'] = desc_el.inner_text().strip()
                break
        
        return product_info
    except Exception as e:
        print(f"Error scraping product page {product_url}: {e}")
        return {}

def scrape_aldi():
    print("Starting Aldi scraper...")
    
    total_inserted = 0
    total_skipped = 0
    
    with sync_playwright() as p:
        browser = get_browser_with_proxy(p)
        page = browser.new_page()

        try:
            # Focus on main page with enhanced scraping
            print(f"\n🌐 Scraping main page: https://www.aldi.es/")
            
            page.goto("https://www.aldi.es/", timeout=60000)
            page.wait_for_timeout(5000)
            
            current_url = page.evaluate("window.location.href")
            print(f"SUCCESS: Loaded {current_url}")

            # Accept cookies if present
            try:
                btn = page.query_selector('button[data-testid="uc-accept-all-button"]')
                if btn:
                    btn.click()
                    page.wait_for_timeout(2000)
                    log_debug_message("COOKIE Cookie popup accepted.")
                    print("COOKIE Cookie popup accepted.")
            except Exception:
                pass

            # Enhanced scrolling to load all content
            print("🔄 Scrolling to load all content...")
            scroll_to_load_all(page, max_scrolls=30)

            # Wait for products to load
            page.wait_for_selector('.mod-article-tile', timeout=15000)
            
            # Get all products
            products = page.query_selector_all('.mod-article-tile')
            log_debug_message(f"SEARCH Found {len(products)} products on main page.")
            print(f"SEARCH Found {len(products)} products on main page.")

            category_inserted = 0
            category_skipped = 0

            for i, product in enumerate(products, 1):
                try:
                    # Extract product information
                    name_el = product.query_selector('.mod-article-tile__title')
                    price_el = product.query_selector('.price__wrapper')
                    
                    # Try alternative price selectors if main one doesn't work
                    if not price_el:
                        price_el = product.query_selector('.price')
                    if not price_el:
                        price_el = product.query_selector('[class*="price"]')
                    
                    # If still no price element, try to extract from entire product text
                    if not price_el:
                        product_text = product.inner_text()
                        price_match = re.search(r'(\d+[.,]\d+|\d+)\s*€', product_text)
                        if price_match:
                            price_text = price_match.group(1)
                            price = extract_price(price_text)
                        else:
                            price = None
                    else:
                        price_text = price_el.inner_text().strip()
                        price = extract_price(price_text)
                    
                    if not name_el or price is None:
                        continue

                    name = name_el.inner_text().strip()
                    if not name or len(name) < 2:
                        continue
                        
                    quantity = "1 unit"  # Default quantity for Aldi products

                    # Progress indicator
                    print(f"[{i}/{len(products)}] ✨ Processing: {name} - {price}€")

                    # Check if product already exists
                    existing_product = get_product_by_name_and_store(name, "aldi")
                    if existing_product:
                        # Update price if different
                        if existing_product['price'] != price:
                            try:
                                update_product_price(existing_product['id'], price, "aldi")
                                print(f"💰 Updated price: {name} - {price}€ (was {existing_product['price']}€)")
                            except Exception as e:
                                print(f"ERROR: Failed to update price: {str(e)}")
                        else:
                            print(f"ℹ️ Price unchanged: {name} - {price}€")
                        category_skipped += 1
                    else:
                        # Insert new product
                        try:
                            insert_product(
                                name=name,
                                price=price,
                                category="general",
                                store_id="aldi",
                                quantity=quantity
                            )
                            category_inserted += 1
                            print(f"✅ Added: {name} - {price}€ {quantity}")
                        except Exception as e:
                            print(f"ERROR: Failed to insert product: {str(e)}")
                            if "duplicate key" in str(e).lower():
                                category_skipped += 1
                                
                except Exception as e:
                    log_debug_message(f"WARN Error processing product {i}: {e}")
                    print(f"WARN Error processing product {i}: {e}")
            
            total_inserted += category_inserted
            total_skipped += category_skipped
            print(f"📊 Main page summary: {category_inserted} added, {category_skipped} skipped")
            
            # Now try to scrape catalog pages with more products
            print(f"\n🌐 Trying catalog pages...")
            catalog_urls = [
                "https://www.aldi.es/lo-ultimo/verano.html",  # Summer catalog
                "https://www.aldi.es/ofertas.html",  # Offers
                "https://www.aldi.es/folleto.html",  # Brochure
                "https://www.aldi.es/inspirate.html",  # Get inspired
                "https://www.aldi.es/lo-ultimo.html",  # Latest
                "https://www.aldi.es/frescos-y-verduras.html",
                "https://www.aldi.es/carnes-y-pescados.html",
                "https://www.aldi.es/lacteos-y-huevos.html",
                "https://www.aldi.es/pan-y-reposteria.html",
                "https://www.aldi.es/bebidas.html",
                "https://www.aldi.es/despensa.html",
                "https://www.aldi.es/congelados.html",
                "https://www.aldi.es/hogar-y-jardin.html",
                "https://www.aldi.es/limpieza.html",
                "https://www.aldi.es/cuidado-personal.html",
                "https://www.aldi.es/bebes-y-ninos.html",
                "https://www.aldi.es/mascotas.html"
            ]
            
            for catalog_url in catalog_urls:
                try:
                    print(f"\n🔍 Trying catalog: {catalog_url}")
                    page.goto(catalog_url, timeout=30000)
                    page.wait_for_timeout(5000)  # Wait longer for dynamic content
                    
                    current_url = page.evaluate("window.location.href")
                    print(f"Loaded: {current_url}")
                    
                    # Wait for products to load (they might be loaded dynamically)
                    try:
                        page.wait_for_selector('.mod-article-tile', timeout=10000)
                    except:
                        print("No products found immediately, continuing...")
                    
                    # Scroll to load all content
                    scroll_to_load_all(page, max_scrolls=25)
                    
                    # Wait a bit more for any dynamic content
                    page.wait_for_timeout(3000)
                    
                    # Look for products on this page
                    products = page.query_selector_all('.mod-article-tile')
                    if products:
                        print(f"✅ Found {len(products)} products on catalog page!")
                        
                        for i, product in enumerate(products, 1):
                            try:
                                name_el = product.query_selector('.mod-article-tile__title')
                                price_el = product.query_selector('.price__wrapper')
                                
                                if not price_el:
                                    price_el = product.query_selector('.price')
                                if not price_el:
                                    price_el = product.query_selector('[class*="price"]')
                                
                                if not name_el or not price_el:
                                    continue
                                
                                name = name_el.inner_text().strip()
                                price_text = price_el.inner_text().strip()
                                price = extract_price(price_text)
                                
                                if not name or price is None:
                                    continue
                                
                                print(f"  [{i}/{len(products)}] {name} - {price}€")
                                
                                # Check if product already exists
                                existing_product = get_product_by_name_and_store(name, "aldi")
                                if existing_product:
                                    if existing_product['price'] != price:
                                        try:
                                            update_product_price(existing_product['id'], price, "aldi")
                                            print(f"    💰 Updated price: {name} - {price}€ (was {existing_product['price']}€)")
                                        except Exception as e:
                                            print(f"    ERROR: Failed to update price: {str(e)}")
                                    else:
                                        print(f"    ℹ️ Price unchanged: {name} - {price}€")
                                    total_skipped += 1
                                else:
                                    try:
                                        insert_product(
                                            name=name,
                                            price=price,
                                            category="general",
                                            store_id="aldi",
                                            quantity="1 unit"
                                        )
                                        total_inserted += 1
                                        print(f"    ✅ Added: {name} - {price}€")
                                    except Exception as e:
                                        print(f"    ERROR: Failed to insert product: {str(e)}")
                                        if "duplicate key" in str(e).lower():
                                            total_skipped += 1
                                            
                            except Exception as e:
                                print(f"    WARN Error processing product {i}: {e}")
                    else:
                        print(f"❌ No products found on catalog page")
                        
                except Exception as e:
                    print(f"❌ Error loading catalog {catalog_url}: {e}")
                    continue

        except Exception as e:
            log_debug_message(f"ERROR Failed to load Aldi: {e}")
            print(f"ERROR: Failed to load Aldi: {e}")
        finally:
            browser.close()
            print(f"\n🎉 FINISH Aldi scraping completed!")
            print(f"📈 Total summary: {total_inserted} products added, {total_skipped} skipped")

if __name__ == "__main__":
    scrape_aldi()
