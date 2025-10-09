from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from utils.db import insert_product, get_product_by_name_and_store, update_product_price
from utils.logger import log_debug_message
import time
import re

BASE_URL = "https://www.consum.es"
OUTPUT_HTML = "consum_debug.html"
OUTPUT_PNG = "consum_debug.png"

def extract_consum_products(page):
    """Extract products from Consum category page"""
    try:
        # Wait for products to load
        selectors_to_try = [
            '[data-test="product-card"]',
            '.product-card',
            '.product-item',
            '[class*="product"]',
            'article',
            '.item',
            '.product'
        ]
        
        products_found = False
        for selector in selectors_to_try:
            try:
                page.wait_for_selector(selector, timeout=5000)
                print(f"SUCCESS Found products with selector: {selector}")
                products_found = True
                break
            except PlaywrightTimeout:
                continue
        
        if not products_found:
            page.wait_for_timeout(5000)
            print("WAIT Waited for dynamic content to load")
            
    except Exception as e:
        print(f"WARN Error waiting for products: {e}")

    # Try to find products with various selectors
    product_elements = []
    selectors_to_try = [
        '[data-test="product-card"]',
        '.product-card',
        '.product-item',
        '[class*="product"]',
        'article',
        '.item',
        '[data-test*="product"]',
        '.product'
    ]
    
    for selector in selectors_to_try:
        elements = page.query_selector_all(selector)
        if elements:
            print(f"🔎 Found {len(elements)} elements with selector: {selector}")
            product_elements = elements
            break
    
    if not product_elements:
        print("ERROR No product elements found with any selector")
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
                '[data-test="product-name"]',
                '[data-test="product-title"]',
                '.product-name',
                '.product-title',
                'h3',
                'h2',
                'h4',
                'span[class*="name"]',
                'span[class*="title"]',
                'p[class*="name"]',
                'p[class*="title"]',
                '.name',
                '.title'
            ]
            
            for name_selector in name_selectors:
                name_el = el.query_selector(name_selector)
                if name_el:
                    name = name_el.inner_text().strip()
                    if name and len(name) > 2:
                        break
            
            if not name or len(name) < 3:
                print(f"WARN Skipped product {i}: Empty name")
                continue

            # Try different ways to extract price
            price = None
            price_selectors = [
                '[data-test="product-price"]',
                '.product-price',
                '.price',
                'span[class*="price"]',
                'p[class*="price"]',
                '[class*="price"]',
                '.price-current',
                '.price-value'
            ]
            
            for price_selector in price_selectors:
                price_el = el.query_selector(price_selector)
                if price_el:
                    price_text = price_el.inner_text().strip()
                    if price_text:
                        # Extract price using regex
                        price_match = re.search(r'(\d+[.,]\d+|\d+)', price_text.replace(',', '.'))
                        if price_match:
                            try:
                                price = float(price_match.group(1))
                                break
                            except ValueError:
                                continue
            
            if not price:
                print(f"WARN Skipped product {i}: Could not extract price. Product text: {name[:50]}...")
                continue

            # Try to extract quantity
            quantity = "1 unit"
            quantity_selectors = [
                '.product-quantity',
                '.quantity',
                'span[class*="quantity"]',
                'p[class*="quantity"]',
                '.unit-price',
                '.weight'
            ]
            
            for quantity_selector in quantity_selectors:
                quantity_el = el.query_selector(quantity_selector)
                if quantity_el:
                    quantity_text = quantity_el.inner_text().strip()
                    if quantity_text:
                        quantity = quantity_text
                        break

            results.append({
                "name": name,
                "price": price,
                "quantity": quantity,
                "category": "general"
            })
            
        except Exception as e:
            print(f"WARN Error processing product {i}: {e}")
            continue
    
    return results

def scrape_consum():
    print("START Starting Consum scraper...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )

        try:
            print("GLOBE Visiting Consum homepage...")
            page.goto(BASE_URL, timeout=60000)
            time.sleep(3)
            print("Current URL:", page.url)

            # Handle cookie popup
            try:
                cookie_button = page.query_selector('button[data-test="cookie-accept"]') or \
                                page.query_selector('button:has-text("Aceptar")') or \
                                page.query_selector('button:has-text("Acepto")') or \
                                page.query_selector('button:has-text("Accept")') or \
                                page.query_selector('button:has-text("OK")') or \
                                page.query_selector('button:has-text("Entendido")')
                if cookie_button:
                    cookie_button.click()
                    print("COOKIE Cookie popup accepted")
                    time.sleep(2)
            except Exception:
                print("WARN Cookie popup not found or already accepted.")

            # Handle any other popups
            def handle_popups():
                try:
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
                    
                    try:
                        page.click('body', position={'x': 100, 'y': 100})
                        time.sleep(1)
                    except:
                        pass
                        
                except Exception as e:
                    print(f"WARN Error handling popups: {e}")

            handle_popups()

            # Try different category URLs
            categories_to_try = [
                {"name": "Frescos", "url": f"{BASE_URL}/frescos"},
                {"name": "Alimentación", "url": f"{BASE_URL}/alimentacion"},
                {"name": "Bebidas", "url": f"{BASE_URL}/bebidas"},
                {"name": "Congelados", "url": f"{BASE_URL}/congelados"},
                {"name": "Desayuno", "url": f"{BASE_URL}/desayuno"},
                {"name": "Lácteos", "url": f"{BASE_URL}/lacteos"},
                {"name": "Frutas", "url": f"{BASE_URL}/frutas"},
                {"name": "Verduras", "url": f"{BASE_URL}/verduras"},
                {"name": "Carnes", "url": f"{BASE_URL}/carnes"},
                {"name": "Pescados", "url": f"{BASE_URL}/pescados"}
            ]
            
            all_products = []
            
            for category in categories_to_try:
                print(f"\nSEARCH Scraping category: {category['name']}")
                
                try:
                    print(f"🌐 Navigating to: {category['url']}")
                    page.goto(category['url'], timeout=60000)
                    time.sleep(3)
                    
                    handle_popups()
                    
                    print(f"Current URL: {page.url}")
                    
                    # Scroll to load products
                    print(f"SCROLL Scrolling to load {category['name']} products...")
                    for i in range(8):
                        page.mouse.wheel(0, 800)
                        time.sleep(0.8)
                        
                        current_products = page.query_selector_all('[data-test="product-card"]')
                        if i % 3 == 0:
                            print(f"CHART Found {len(current_products)} products in {category['name']}...")
                    
                    page.wait_for_timeout(3000)
                    
                    category_products = extract_consum_products(page)
                    all_products.extend(category_products)
                    
                    print(f"SUCCESS Extracted {len(category_products)} products from {category['name']}")
                    
                except Exception as e:
                    print(f"ERROR Error scraping {category['name']}: {e}")
                    continue
            
            if not all_products:
                print("ERROR No products found from any category.")
                page.screenshot(path=OUTPUT_PNG, full_page=True)
                with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
                    f.write(page.content())
                print(f"📸 Debug info saved to {OUTPUT_PNG} and {OUTPUT_HTML}")
                return

            print(f"\nBOX Processing {len(all_products)} total products...")
            for i, product in enumerate(all_products, 1):
                try:
                    existing_product = get_product_by_name_and_store(product["name"], "consum")
                    if existing_product:
                        if existing_product['price'] != product["price"]:
                            print(f"RETRY [{i}] Price updated: {product['name']} {existing_product['price']}€ → {product['price']}€")
                            update_product_price(existing_product['id'], product["price"])
                        else:
                            print(f"SKIP [{i}] No change: {product['name']}")
                    else:
                        insert_product(product["name"], product["price"], product["category"], "consum", product["quantity"])
                        print(f"SUCCESS [{i}] Inserted: {product['name']} — {product['price']}€ ({product['quantity']})")
                except Exception as e:
                    print(f"ERROR DB error on product {i}: {e}")

        except Exception as e:
            print(f"ERROR Scraping failed: {e}")
        finally:
            browser.close()
            print("FINISH Scraper finished.")

if __name__ == "__main__":
    scrape_consum() 