from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from utils.db import insert_product, get_product_by_name_and_store, update_product_price
from utils.logger import log_debug_message
import time
import re
import random

BASE_URL = "https://supermercado.eroski.es/en/"
OUTPUT_HTML = "eroski_debug.html"
OUTPUT_PNG = "eroski_debug.png"

def extract_eroski_products(page):
    """Extract products from Eroski category page"""
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
        try:
            elements = page.query_selector_all(selector)
            if elements:
                print(f"🔎 Found {len(elements)} elements with selector: {selector}")
                product_elements = elements
                break
        except Exception as e:
            print(f"WARN Error with selector {selector}: {e}")
            continue
    
    if not product_elements:
        print("ERROR No product elements found with any selector")
        try:
            page.screenshot(path=OUTPUT_PNG, full_page=True)
            with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
                f.write(page.content())
            print(f"📸 Screenshot saved to {OUTPUT_PNG}, HTML saved to {OUTPUT_HTML}")
        except Exception as e:
            print(f"WARN Could not save debug files: {e}")
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
                try:
                    name_el = el.query_selector(name_selector)
                    if name_el:
                        name = name_el.inner_text().strip()
                        if name and len(name) > 2:
                            break
                except:
                    continue
            
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
                '.price-value',
                '.product-price-current',
                '.price-amount'
            ]
            
            for price_selector in price_selectors:
                try:
                    price_el = el.query_selector(price_selector)
                    if price_el:
                        price_text = price_el.inner_text().strip()
                        if price_text:
                            # Extract price using regex - try multiple patterns
                            price_patterns = [
                                r'(\d+[.,]\d+|\d+)',  # Standard decimal format
                                r'(\d+,\d+)',          # Comma decimal format
                                r'(\d+\.\d+)',         # Dot decimal format
                                r'(\d+)',              # Integer format
                            ]
                            
                            for pattern in price_patterns:
                                price_match = re.search(pattern, price_text.replace(',', '.'))
                                if price_match:
                                    try:
                                        price_value = price_match.group(1).replace(',', '.')
                                        price = float(price_value)
                                        if price > 0 and price < 1000:  # Reasonable price range
                                            break
                                    except ValueError:
                                        continue
                except:
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
                try:
                    quantity_el = el.query_selector(quantity_selector)
                    if quantity_el:
                        quantity_text = quantity_el.inner_text().strip()
                        if quantity_text:
                            quantity = quantity_text
                            break
                except:
                    continue

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

def scrape_eroski():
    print("START Starting Eroski scraper...")
    
    # Try multiple times with different approaches
    max_retries = 3
    for attempt in range(max_retries):
        print(f"\nRETRY Attempt {attempt + 1}/{max_retries}")
        
        try:
            with sync_playwright() as p:
                # Use different browser configurations to avoid detection
                browser_options = [
                    {"headless": False, "args": ["--no-sandbox", "--disable-blink-features=AutomationControlled"]},
                    {"headless": False, "args": ["--no-sandbox", "--disable-web-security", "--disable-features=VizDisplayCompositor"]},
                    {"headless": False, "args": ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]}
                ]
                
                browser_config = browser_options[attempt % len(browser_options)]
                browser = p.chromium.launch(**browser_config)
                
                # Create context with stealth settings
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1366, "height": 768},
                    locale="es-ES",
                    timezone_id="Europe/Madrid",
                    extra_http_headers={
                        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Encoding": "gzip, deflate, br",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1"
                    }
                )
                
                page = context.new_page()
                
                # Add stealth scripts
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['es-ES', 'es', 'en'],
                    });
                """)

                try:
                    print("GLOBE Visiting Eroski homepage...")
                    page.goto(BASE_URL, timeout=60000, wait_until="networkidle")
                    time.sleep(random.uniform(2, 4))
                    print("Current URL:", page.url)

                    # Handle cookie popup
                    try:
                        cookie_selectors = [
                            'button[data-test="cookie-accept"]',
                            'button:has-text("Aceptar")',
                            'button:has-text("Acepto")',
                            'button:has-text("Accept")',
                            'button:has-text("OK")',
                            'button:has-text("Entendido")',
                            'button:has-text("Aceptar todas")',
                            'button:has-text("Aceptar cookies")',
                            '.cookie-accept',
                            '.accept-cookies'
                        ]
                        
                        for selector in cookie_selectors:
                            try:
                                cookie_button = page.query_selector(selector)
                                if cookie_button and cookie_button.is_visible():
                                    cookie_button.click()
                                    print(f"COOKIE Cookie popup accepted with selector: {selector}")
                                    time.sleep(random.uniform(1, 3))
                                    break
                            except:
                                continue
                    except Exception as e:
                        print(f"WARN Cookie popup handling error: {e}")

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
                                'button:has-text("Close")',
                                'button[aria-label="Cerrar"]'
                            ]
                            
                            for selector in close_buttons:
                                try:
                                    close_btn = page.query_selector(selector)
                                    if close_btn and close_btn.is_visible():
                                        close_btn.click()
                                        print(f"🔒 Closed popup with selector: {selector}")
                                        time.sleep(random.uniform(0.5, 1.5))
                                        break
                                except:
                                    continue
                            
                            try:
                                # Click outside any modal
                                page.click('body', position={'x': 100, 'y': 100})
                                time.sleep(0.5)
                            except:
                                pass
                                
                        except Exception as e:
                            print(f"WARN Error handling popups: {e}")

                    handle_popups()

                    # Try different category URLs with fallback options
                    categories_to_try = [
                        {"name": "Frescos", "url": f"{BASE_URL}c/comprar-frescos/c1855", "fallback": f"{BASE_URL}es/supermercado/marketplace/"},
                        {"name": "Alimentación", "url": f"{BASE_URL}c/comprar-alimentos/c1856", "fallback": f"{BASE_URL}es/supermercado/marketplace/"},
                        {"name": "Bebidas", "url": f"{BASE_URL}c/comprar-bebidas/c1857", "fallback": f"{BASE_URL}es/supermercado/marketplace/"},
                        {"name": "Congelados", "url": f"{BASE_URL}c/comprar-congelados/c1858", "fallback": f"{BASE_URL}es/supermercado/marketplace/"},
                        {"name": "Desayuno", "url": f"{BASE_URL}c/comprar-desayuno/c1859", "fallback": f"{BASE_URL}es/supermercado/marketplace/"},
                        {"name": "Lácteos", "url": f"{BASE_URL}c/comprar-lacteos/c1860", "fallback": f"{BASE_URL}es/supermercado/marketplace/"},
                        {"name": "Frutas", "url": f"{BASE_URL}c/comprar-frutas/c1861", "fallback": f"{BASE_URL}es/supermercado/marketplace/"},
                        {"name": "Verduras", "url": f"{BASE_URL}c/comprar-verduras/c1862", "fallback": f"{BASE_URL}es/supermercado/marketplace/"},
                        {"name": "Carnes", "url": f"{BASE_URL}c/comprar-carnes/c1863", "fallback": f"{BASE_URL}es/supermercado/marketplace/"},
                        {"name": "Pescados", "url": f"{BASE_URL}c/comprar-pescados/c1864", "fallback": f"{BASE_URL}es/supermercado/marketplace/"}
                    ]
                    
                    all_products = []
                    
                    for category in categories_to_try:
                        print(f"\nSEARCH Scraping category: {category['name']}")
                        
                        try:
                            print(f"🌐 Navigating to: {category['url']}")
                            page.goto(category['url'], timeout=60000, wait_until="domcontentloaded")
                            time.sleep(random.uniform(2, 4))
                            
                            handle_popups()
                            
                            print(f"Current URL: {page.url}")
                            
                            # Check if we got a 404 or error page
                            if "error404" in page.url or "error" in page.url:
                                print(f"WARN Got error page for {category['name']}, trying fallback URL...")
                                if 'fallback' in category:
                                    try:
                                        print(f"🔄 Trying fallback URL: {category['fallback']}")
                                        page.goto(category['fallback'], timeout=60000, wait_until="domcontentloaded")
                                        time.sleep(random.uniform(2, 4))
                                        handle_popups()
                                        print(f"Fallback URL: {page.url}")
                                    except Exception as e:
                                        print(f"ERROR Fallback URL also failed: {e}")
                                        continue
                                else:
                                    print(f"ERROR No fallback URL for {category['name']}")
                                    continue
                            
                            # Scroll to load products
                            print(f"SCROLL Scrolling to load {category['name']} products...")
                            for i in range(6):
                                page.mouse.wheel(0, random.randint(600, 1000))
                                time.sleep(random.uniform(0.6, 1.2))
                                
                                try:
                                    current_products = page.query_selector_all('[data-test="product-card"]')
                                    if i % 2 == 0:
                                        print(f"CHART Found {len(current_products)} products in {category['name']}...")
                                except:
                                    pass
                            
                            page.wait_for_timeout(random.uniform(2000, 4000))
                            
                            category_products = extract_eroski_products(page)
                            all_products.extend(category_products)
                            
                            print(f"SUCCESS Extracted {len(category_products)} products from {category['name']}")
                            
                        except Exception as e:
                            print(f"ERROR Error scraping {category['name']}: {e}")
                            continue
                    
                    if not all_products:
                        print("ERROR No products found from any category.")
                        try:
                            page.screenshot(path=OUTPUT_PNG, full_page=True)
                            with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
                                f.write(page.content())
                            print(f"📸 Debug info saved to {OUTPUT_PNG} and {OUTPUT_HTML}")
                        except Exception as e:
                            print(f"WARN Could not save debug files: {e}")
                        return

                    print(f"\nBOX Processing {len(all_products)} total products...")
                    for i, product in enumerate(all_products, 1):
                        try:
                            existing_product = get_product_by_name_and_store(product["name"], "eroski")
                            if existing_product:
                                if existing_product['price'] != product["price"]:
                                    print(f"RETRY [{i}] Price updated: {product['name']} {existing_product['price']}€ → {product['price']}€")
                                    update_product_price(existing_product['id'], product["price"])
                                else:
                                    print(f"SKIP [{i}] No change: {product['name']}")
                            else:
                                insert_product(product["name"], product["price"], product["category"], "eroski", product["quantity"])
                                print(f"SUCCESS [{i}] Inserted: {product['name']} — {product['price']}€ ({product['quantity']})")
                        except Exception as e:
                            print(f"ERROR DB error on product {i}: {e}")
                    
                    print("SUCCESS Scraping completed successfully!")
                    return

                except Exception as e:
                    print(f"ERROR Scraping failed: {e}")
                    if attempt < max_retries - 1:
                        print("RETRY Retrying with different configuration...")
                        time.sleep(random.uniform(5, 10))
                    else:
                        print("ERROR All retry attempts failed")
                finally:
                    try:
                        browser.close()
                    except:
                        pass
                        
        except Exception as e:
            print(f"ERROR Browser setup failed: {e}")
            if attempt < max_retries - 1:
                print("RETRY Retrying...")
                time.sleep(random.uniform(3, 7))
            else:
                print("ERROR All retry attempts failed")
    
    print("FINISH Scraper finished.")

if __name__ == "__main__":
    scrape_eroski() 