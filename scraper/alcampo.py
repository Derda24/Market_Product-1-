from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from utils.db import insert_product, get_product_by_name_and_store, update_product_price
from utils.logger import log_debug_message
import time
import re

BASE_URL = "https://www.compraonline.alcampo.es"
CATEGORY_PATH = "/supermercado/verduras-y-hortalizas"
OUTPUT_HTML = "alcampo_debug.html"
OUTPUT_PNG = "alcampo_debug.png"

def extract_alcampo_products(page, category):
    """Extract products from Alcampo category page"""
    try:
        # Wait for products to load - try multiple possible selectors
        selectors_to_try = [
            '[data-test="fop-title"]',
            '[data-test="product-title"]',
            '[data-test="product-name"]',
            '.product-title',
            '.product-name',
            'h3[data-test*="title"]',
            'h3[data-test*="name"]',
            'article',
            '.product-card',
            '.product-item'
        ]
        
        products_found = False
        for selector in selectors_to_try:
            try:
                page.wait_for_selector(selector, timeout=5000)
                print(f"SUCCESS: Found products with selector: {selector}")
                products_found = True
                break
            except PlaywrightTimeout:
                continue
        
        if not products_found:
            # If no specific selectors work, wait for any content to load
            page.wait_for_timeout(10000)  # Wait 10 seconds for dynamic content
            print("WAIT Waited for dynamic content to load")
            
    except Exception as e:
        print(f"WARN Error waiting for products: {e}")

    # Try to find products with various selectors
    product_elements = []
    selectors_to_try = [
        '[data-test="fop-title"]',
        '[data-test="product-title"]',
        '[data-test="product-name"]',
        '.product-title',
        '.product-name',
        'h3[data-test*="title"]',
        'h3[data-test*="name"]',
        'article',
        '.product-card',
        '.product-item',
        '[data-test*="product"]',
        '[class*="product"]'
    ]
    
    for selector in selectors_to_try:
        elements = page.query_selector_all(selector)
        if elements:
            print(f"🔎 Found {len(elements)} elements with selector: {selector}")
            product_elements = elements
            break
    
    if not product_elements:
        print("ERROR: No product elements found with any selector")
        page.screenshot(path=OUTPUT_PNG, full_page=True)
        with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
            f.write(page.content())
        print(f"📸 Screenshot saved to {OUTPUT_PNG}, HTML saved to {OUTPUT_HTML}")
        return []

    print(f"🔎 Found {len(product_elements)} products.")

    results = []
    for i, el in enumerate(product_elements, 1):
        try:
            # Try different ways to extract product name
            name = None
            name_selectors = [
                '[data-test="fop-title"]',
                '[data-test="product-title"]',
                '[data-test="product-name"]',
                '.product-title',
                '.product-name',
                'h3',
                'h2',
                'span',
                'p'
            ]
            
            for name_selector in name_selectors:
                name_el = el.query_selector(name_selector)
                if name_el:
                    name = name_el.inner_text().strip()
                    if name and len(name) > 2:  # Make sure it's not empty or too short
                        break
            
            if not name:
                # Fallback: get text from the element itself
                name = el.inner_text().strip()
                if len(name) > 50:  # If it's too long, take first part
                    name = name[:50] + "..."
            
            if not name:
                print(f"WARN Skipped product {i}: Could not extract name")
                continue

            # Find the product container - look for parent elements that might contain the price
            container = None
            current_el = el
            for _ in range(5):  # Go up to 5 levels to find container
                try:
                    parent = current_el.query_selector('xpath=..')
                    if parent:
                        current_el = parent
                        # Check if this parent contains price information
                        parent_text = parent.inner_text()
                        if '€' in parent_text and len(parent_text) > len(name):
                            container = parent
                            break
                except:
                    break
            
            if not container:
                container = el  # Use the original element as fallback

            # Try to find price in the container
            price = None
            price_selectors = [
                '[data-test="fop-price"]',
                '[data-test="product-price"]',
                '.price',
                '.product-price',
                'span[class*="price"]',
                '[class*="price"]',
                '[data-test*="price"]',
                'span[class*="Price"]',
                '[class*="Price"]',
                'span[class*="cost"]',
                '[class*="cost"]',
                'span[class*="value"]',
                '[class*="value"]'
            ]
            
            for price_selector in price_selectors:
                price_el = container.query_selector(price_selector)
                if price_el:
                    price_text = price_el.inner_text().strip()
                    if '€' in price_text or 'EUR' in price_text or 'euro' in price_text.lower():
                        try:
                            # Extract numeric value from price text
                            price_match = re.search(r'(\d+[.,]\d+|\d+)', price_text.replace(',', '.'))
                            if price_match:
                                price = float(price_match.group(1).replace(',', '.'))
                                break
                        except ValueError:
                            continue
            
            if not price:
                # Try to find price in the entire container text
                container_text = container.inner_text()
                price_match = re.search(r'(\d+[.,]\d+|\d+)\s*€', container_text)
                if price_match:
                    try:
                        price = float(price_match.group(1).replace(',', '.'))
                    except ValueError:
                        pass
            
            if not price:
                print(f"WARN Skipped product {i}: Could not extract price. Product text: {name[:50]}...")
                continue

            # Try to find quantity
            quantity = "1 unit"
            quantity_selectors = [
                '[data-test="fop-size"] span',
                '[data-test="product-size"]',
                '.size',
                '.quantity',
                '[class*="size"]',
                '[class*="quantity"]'
            ]
            
            for quantity_selector in quantity_selectors:
                quantity_el = el.query_selector(quantity_selector)
                if quantity_el:
                    quantity = quantity_el.inner_text().strip()
                    break

            results.append({
                "name": name,
                "price": price,
                "quantity": quantity,
                "category": category,
            })
        except Exception as e:
            print(f"WARN Error processing product {i}: {e}")
    return results

def extract_bonarea_products(page):
    product_elements = page.query_selector_all('div.block-product')
    print(f"Found {len(product_elements)} products.")
    products = []
    for i, el in enumerate(product_elements, 1):
        try:
            name = el.query_selector('.text > p').inner_text().strip()
            quantity = el.query_selector('.weight').inner_text().strip()
            price_text = el.query_selector('.price > span').inner_text().strip()
            price = float(price_text.split('€')[0].replace(',', '.').strip())
            image_url = el.query_selector('.foto img').get_attribute('src')
            products.append({
                "name": name,
                "quantity": quantity,
                "price": price,
                "image_url": image_url,
            })
        except Exception as e:
            print(f"Error processing product {i}: {e}")
    return products

def scrape_alcampo():
    print("Starting Alcampo scraper...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )

        try:
            print("GLOBE Visiting homepage...")
            page.goto(BASE_URL, timeout=60000)
            time.sleep(3)
            print("Current URL:", page.url)

            # Handle cookie popup
            try:
                cookie_button = page.query_selector('button[data-test="cookie-accept"]') or \
                                page.query_selector('button:has-text("Aceptar")') or \
                                page.query_selector('button:has-text("Acepto")') or \
                                page.query_selector('button:has-text("Accept")')
                if cookie_button:
                    cookie_button.click()
                    print("COOKIE Cookie popup accepted")
                    time.sleep(2)
            except Exception:
                print("WARN Cookie popup not found or already accepted.")

            # Handle any other popups that might appear
            def handle_popups():
                try:
                    # Try to close any modal or popup
                    close_buttons = [
                        'button[aria-label="Close"]',
                        'button[class*="close"]',
                        'button[class*="Close"]',
                        '.modal-close',
                        '.popup-close',
                        'button:has-text("×")',
                        'button:has-text("X")',
                        'button:has-text("Cerrar")',
                        'button:has-text("Close")'
                    ]
                    
                    for selector in close_buttons:
                        try:
                            close_btn = page.query_selector(selector)
                            if close_btn and close_btn.is_visible():
                                close_btn.click()
                                print(f"🔒 Closed popup with selector: {selector}")
                                time.sleep(1)
                                break
                        except:
                            continue
                    
                    # Try to click outside any modal
                    try:
                        page.click('body', position={'x': 100, 'y': 100})
                        time.sleep(1)
                    except:
                        pass
                        
                except Exception as e:
                    print(f"WARN Error handling popups: {e}")

            # Handle initial popups
            handle_popups()

            # Try direct navigation to categories instead of clicking
            categories_to_try = [
                {"name": "Frescos", "url": f"{BASE_URL}/supermercado/frescos"},
                {"name": "Alimentación", "url": f"{BASE_URL}/supermercado/alimentacion"},
                {"name": "Bebidas", "url": f"{BASE_URL}/supermercado/bebidas"},
                {"name": "Congelados", "url": f"{BASE_URL}/supermercado/congelados"},
                {"name": "Desayuno", "url": f"{BASE_URL}/supermercado/desayuno"},
                {"name": "Verduras", "url": f"{BASE_URL}/supermercado/verduras-y-hortalizas"},
                {"name": "Frutas", "url": f"{BASE_URL}/supermercado/frutas"},
                {"name": "Lácteos", "url": f"{BASE_URL}/supermercado/lacteos"}
            ]
            
            all_products = []
            
            for category in categories_to_try:
                print(f"\nSEARCH Scraping category: {category['name']}")
                
                try:
                    # Navigate directly to category URL
                    print(f"🌐 Navigating to: {category['url']}")
                    page.goto(category['url'], timeout=60000)
                    time.sleep(3)
                    
                    # Handle any popups that appear
                    handle_popups()
                    
                    print(f"Current URL: {page.url}")
                    
                    # Scroll to load products for this category
                    print(f"SCROLL Scrolling to load {category['name']} products...")
                    for i in range(10):  # Reduced scroll count
                        page.mouse.wheel(0, 800)
                        time.sleep(0.8)
                        
                        # Check if more products loaded
                        current_products = page.query_selector_all('[data-test="fop-title"]')
                        if i % 3 == 0:
                            print(f"CHART Found {len(current_products)} products in {category['name']}...")
                    
                    # Wait for dynamic content
                    page.wait_for_timeout(3000)
                    
                    # Extract products from this category
                    category_products = extract_alcampo_products(page, category['name'].lower())
                    all_products.extend(category_products)
                    
                    print(f"SUCCESS: Extracted {len(category_products)} products from {category['name']}")
                    
                except Exception as e:
                    print(f"ERROR: Error scraping {category['name']}: {e}")
                    continue
            
            # If direct navigation didn't work, try clicking approach as fallback
            if not all_products:
                print("RETRY Trying fallback approach with category clicking...")
                page.goto(BASE_URL, timeout=60000)
                time.sleep(3)
                handle_popups()
                
                # Try clicking on main category links
                category_selectors = [
                    'a[href*="frescos"]',
                    'a[href*="alimentacion"]',
                    'a[href*="bebidas"]',
                    'a[href*="congelados"]',
                    'a[href*="desayuno"]',
                    'a:has-text("Frescos")',
                    'a:has-text("Alimentación")',
                    'a:has-text("Bebidas")',
                    'a:has-text("Congelados")',
                    'a:has-text("Desayuno")'
                ]
                
                for selector in category_selectors:
                    try:
                        category_link = page.query_selector(selector)
                        if category_link and category_link.is_visible():
                            print(f"🖱️ Clicking category with selector: {selector}")
                            category_link.click()
                            page.wait_for_timeout(3000)
                            handle_popups()
                            
                            # Scroll and extract products
                            for i in range(8):
                                page.mouse.wheel(0, 800)
                                time.sleep(0.8)
                            
                            page.wait_for_timeout(3000)
                            category_products = extract_alcampo_products(page, "general")
                            all_products.extend(category_products)
                            
                            print(f"SUCCESS: Extracted {len(category_products)} products via clicking")
                            break
                    except Exception as e:
                        print(f"ERROR: Error with selector {selector}: {e}")
                        continue
            
            if not all_products:
                print("ERROR: No products found from any category.")
                # Save debug info
                page.screenshot(path=OUTPUT_PNG, full_page=True)
                with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
                    f.write(page.content())
                print(f"📸 Debug info saved to {OUTPUT_PNG} and {OUTPUT_HTML}")
                return

            print(f"\nProcessing {len(all_products)} total products...")
            for i, product in enumerate(all_products, 1):
                try:
                    existing_product = get_product_by_name_and_store(product["name"], "alcampo")
                    if existing_product:
                        if existing_product['price'] != product["price"]:
                            print(f"RETRY [{i}] Price updated: {product['name']} {existing_product['price']}€ → {product['price']}€")
                            update_product_price(existing_product['id'], product["price"])
                        else:
                            print(f"SKIP [{i}] No change: {product['name']}")
                    else:
                        insert_product(product["name"], product["price"], product["category"], "alcampo", product["quantity"])
                        print(f"SUCCESS: [{i}] Inserted: {product['name']} — {product['price']}€ ({product['quantity']})")
                except Exception as e:
                    print(f"ERROR: DB error on product {i}: {e}")

        except Exception as e:
            print(f"ERROR: Scraping failed: {e}")
        finally:
            browser.close()
            print("FINISH Scraper finished.")

if __name__ == "__main__":
    scrape_alcampo()
