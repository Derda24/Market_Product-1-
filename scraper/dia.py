from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from utils.db import insert_product, get_product_by_name_and_store, update_product_price
from utils.logger import log_debug_message
import time
import re
import random

BASE_URL = "https://www.dia.es"
OUTPUT_HTML = "dia_debug.html"
OUTPUT_PNG = "dia_debug.png"

def extract_dia_products(page):
    """Extract products from Dia category page"""
    try:
        # Wait for products to load
        selectors_to_try = [
            '[data-test="product-card"]',
            '.product-card',
            '.product-item',
            '[class*="product"]',
            'article',
            '.item',
            '.product',
            '[class*="item"]',
            '[class*="card"]'
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
        '.product',
        '[class*="item"]',
        '[class*="card"]',
        '.producto',
        '.articulo'
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
                '.title',
                '[class*="nombre"]',
                '[class*="titulo"]'
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
                '[class*="precio"]',
                '.precio'
            ]
            
            for price_selector in price_selectors:
                try:
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
                '.weight',
                '[class*="cantidad"]',
                '[class*="peso"]'
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

def scrape_dia():
    print("START Starting Dia scraper...")
    
    # Try multiple times with different approaches
    max_retries = 3
    for attempt in range(max_retries):
        print(f"\nRETRY Attempt {attempt + 1}/{max_retries}")
        
        try:
            with sync_playwright() as p:
                # Use different browser configurations to avoid detection
                browser_options = [
                    {"headless": False, "args": ["--no-sandbox", "--disable-blink-features=AutomationControlled", "--disable-web-security", "--disable-features=VizDisplayCompositor"]},
                    {"headless": False, "args": ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-features=VizDisplayCompositor", "--disable-blink-features=AutomationControlled"]},
                    {"headless": False, "args": ["--no-sandbox", "--disable-blink-features=AutomationControlled", "--disable-web-security", "--disable-features=VizDisplayCompositor", "--disable-dev-shm-usage"]}
                ]
                
                browser_config = browser_options[attempt % len(browser_options)]
                browser = p.chromium.launch(**browser_config)
                
                # Try different user agents
                user_agents = [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                    "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
                ]
                
                user_agent = user_agents[attempt % len(user_agents)]
                
                # Create context with stealth settings
                context = browser.new_context(
                    user_agent=user_agent,
                    viewport={"width": 1366, "height": 768},
                    locale="es-ES",
                    timezone_id="Europe/Madrid",
                    extra_http_headers={
                        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Encoding": "gzip, deflate, br",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Cache-Control": "max-age=0",
                        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                        "Sec-Ch-Ua-Mobile": "?0",
                        "Sec-Ch-Ua-Platform": '"Windows"'
                    }
                )
                
                page = context.new_page()
                
                # Add more comprehensive stealth scripts
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
                    Object.defineProperty(navigator, 'platform', {
                        get: () => 'Win32',
                    });
                    Object.defineProperty(navigator, 'hardwareConcurrency', {
                        get: () => 8,
                    });
                    Object.defineProperty(navigator, 'deviceMemory', {
                        get: () => 8,
                    });
                    Object.defineProperty(navigator, 'maxTouchPoints', {
                        get: () => 0,
                    });
                    Object.defineProperty(navigator, 'vendor', {
                        get: () => 'Google Inc.',
                    });
                    Object.defineProperty(navigator, 'cookieEnabled', {
                        get: () => true,
                    });
                    Object.defineProperty(navigator, 'onLine', {
                        get: () => true,
                    });
                    Object.defineProperty(navigator, 'doNotTrack', {
                        get: () => null,
                    });
                    
                    // Override permissions
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                    
                    // Override chrome
                    Object.defineProperty(window, 'chrome', {
                        writable: true,
                        enumerable: true,
                        configurable: true,
                        value: {
                            runtime: {},
                        },
                    });
                """)

                try:
                    print("GLOBE Visiting Dia homepage...")
                    
                    # Try different URLs including mobile versions
                    urls_to_try = [
                        BASE_URL,
                        "https://www.dia.es/tienda-online",
                        "https://www.dia.es/productos",
                        "https://www.dia.es/categorias",
                        "https://m.dia.es",
                        "https://www.dia.es/m",
                        "https://www.dia.es/online",
                        "https://www.dia.es/tienda"
                    ]
                    
                    page_loaded = False
                    for url in urls_to_try:
                        try:
                            print(f"🌐 Trying URL: {url}")
                            
                            # Add random delay before request
                            time.sleep(random.uniform(1, 3))
                            
                            page.goto(url, timeout=60000, wait_until="domcontentloaded")
                            time.sleep(random.uniform(2, 4))
                            
                            # Check if we got access denied
                            page_content = page.content().lower()
                            if "access denied" in page_content or "forbidden" in page_content or "blocked" in page_content:
                                print(f"ERROR Access denied for {url}")
                                continue
                            
                            # Check if page loaded successfully
                            if "dia" in page_content or "producto" in page_content or "tienda" in page_content:
                                print(f"SUCCESS Successfully loaded: {page.url}")
                                page_loaded = True
                                break
                            else:
                                print(f"WARN Page loaded but content doesn't look like Dia: {url}")
                                continue
                            
                        except Exception as e:
                            print(f"ERROR Failed to load {url}: {e}")
                            continue
                    
                    if not page_loaded:
                        print("ERROR Could not load any Dia URLs")
                        continue

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
                            '.accept-cookies',
                            'button[class*="cookie"]',
                            'button[class*="Cookie"]',
                            'button:has-text("Continuar")',
                            'button:has-text("Seguir")'
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

                    # Try to find and click on category links
                    all_products = []
                    
                    # Try different approaches to find products
                    approaches = [
                        # Approach 1: Try to find category links on homepage
                        {
                            "name": "Homepage Categories",
                            "action": lambda: page.query_selector_all('a[href*="categoria"], a[href*="category"], a[href*="producto"], a[href*="product"], a[href*="/tienda"], a[href*="/productos"]')
                        },
                        # Approach 2: Try to find a "Ver todos" or "Ver más" button
                        {
                            "name": "Ver más button",
                            "action": lambda: page.query_selector('button:has-text("Ver más"), button:has-text("Ver todos"), a:has-text("Ver más"), a:has-text("Ver todos"), button:has-text("Comprar"), a:has-text("Comprar")')
                        },
                        # Approach 3: Try to find any product links
                        {
                            "name": "Product links",
                            "action": lambda: page.query_selector_all('a[href*="producto"], a[href*="product"], [class*="product"], [class*="producto"]')
                        },
                        # Approach 4: Try to find navigation menu
                        {
                            "name": "Navigation menu",
                            "action": lambda: page.query_selector('nav, .nav, .navigation, .menu, [class*="nav"], [class*="menu"]')
                        },
                        # Approach 5: Try to find any clickable elements
                        {
                            "name": "Any clickable elements",
                            "action": lambda: page.query_selector_all('a, button, [role="button"], [class*="btn"], [class*="button"]')
                        }
                    ]
                    
                    for approach in approaches:
                        print(f"\nSEARCH Trying approach: {approach['name']}")
                        try:
                            elements = approach['action']()
                            if elements:
                                print(f"SUCCESS Found {len(elements)} elements with {approach['name']}")
                                
                                # If we found category links, try clicking on them
                                if approach['name'] == "Homepage Categories" and len(elements) > 0:
                                    for i, element in enumerate(elements[:5]):  # Try first 5 categories
                                        try:
                                            category_name = element.inner_text().strip()
                                            if category_name and len(category_name) > 2:
                                                print(f"SEARCH Clicking on category: {category_name}")
                                                element.click()
                                                time.sleep(random.uniform(2, 4))
                                                
                                                handle_popups()
                                                
                                                # Scroll to load products
                                                print(f"SCROLL Scrolling to load products...")
                                                for j in range(5):
                                                    page.mouse.wheel(0, random.randint(600, 1000))
                                                    time.sleep(random.uniform(0.6, 1.2))
                                                
                                                page.wait_for_timeout(random.uniform(2000, 4000))
                                                
                                                category_products = extract_dia_products(page)
                                                all_products.extend(category_products)
                                                
                                                print(f"SUCCESS Extracted {len(category_products)} products from {category_name}")
                                                
                                                # Go back to homepage
                                                page.goto(BASE_URL, timeout=60000)
                                                time.sleep(random.uniform(1, 3))
                                                handle_popups()
                                                
                                        except Exception as e:
                                            print(f"ERROR Error with category {i}: {e}")
                                            continue
                                
                                # If we found a "Ver más" button, click it
                                elif approach['name'] == "Ver más button" and elements:
                                    try:
                                        print("SEARCH Clicking 'Ver más' button...")
                                        elements.click()
                                        time.sleep(random.uniform(2, 4))
                                        
                                        handle_popups()
                                        
                                        # Scroll to load products
                                        print(f"SCROLL Scrolling to load products...")
                                        for j in range(6):
                                            page.mouse.wheel(0, random.randint(600, 1000))
                                            time.sleep(random.uniform(0.6, 1.2))
                                        
                                        page.wait_for_timeout(random.uniform(2000, 4000))
                                        
                                        category_products = extract_dia_products(page)
                                        all_products.extend(category_products)
                                        
                                        print(f"SUCCESS Extracted {len(category_products)} products")
                                        
                                    except Exception as e:
                                        print(f"ERROR Error clicking 'Ver más': {e}")
                                
                                # If we found product links, try to extract from current page
                                elif approach['name'] == "Product links":
                                    print("SEARCH Found product elements, extracting...")
                                    
                                    # Scroll to load products
                                    print(f"SCROLL Scrolling to load products...")
                                    for j in range(6):
                                        page.mouse.wheel(0, random.randint(600, 1000))
                                        time.sleep(random.uniform(0.6, 1.2))
                                    
                                    page.wait_for_timeout(random.uniform(2000, 4000))
                                    
                                    category_products = extract_dia_products(page)
                                    all_products.extend(category_products)
                                    
                                    print(f"SUCCESS Extracted {len(category_products)} products")
                                
                                # If we found navigation menu, try to interact with it
                                elif approach['name'] == "Navigation menu" and elements:
                                    try:
                                        print("SEARCH Found navigation menu, trying to interact...")
                                        # Try to find category links in the navigation
                                        nav_links = page.query_selector_all('a[href*="categoria"], a[href*="producto"], a[href*="tienda"]')
                                        if nav_links:
                                            for i, link in enumerate(nav_links[:3]):
                                                try:
                                                    category_name = link.inner_text().strip()
                                                    if category_name and len(category_name) > 2:
                                                        print(f"SEARCH Clicking on nav category: {category_name}")
                                                        link.click()
                                                        time.sleep(random.uniform(2, 4))
                                                        
                                                        handle_popups()
                                                        
                                                        # Scroll to load products
                                                        print(f"SCROLL Scrolling to load products...")
                                                        for j in range(5):
                                                            page.mouse.wheel(0, random.randint(600, 1000))
                                                            time.sleep(random.uniform(0.6, 1.2))
                                                        
                                                        page.wait_for_timeout(random.uniform(2000, 4000))
                                                        
                                                        category_products = extract_dia_products(page)
                                                        all_products.extend(category_products)
                                                        
                                                        print(f"SUCCESS Extracted {len(category_products)} products from {category_name}")
                                                        
                                                        # Go back to homepage
                                                        page.goto(BASE_URL, timeout=60000)
                                                        time.sleep(random.uniform(1, 3))
                                                        handle_popups()
                                                        
                                                except Exception as e:
                                                    print(f"ERROR Error with nav category {i}: {e}")
                                                    continue
                                    except Exception as e:
                                        print(f"ERROR Error with navigation menu: {e}")
                                
                                # If we found any clickable elements, try clicking on them
                                elif approach['name'] == "Any clickable elements" and elements:
                                    try:
                                        print("SEARCH Found clickable elements, trying to interact...")
                                        # Try clicking on elements that might lead to products
                                        for i, element in enumerate(elements[:10]):
                                            try:
                                                element_text = element.inner_text().strip()
                                                if element_text and len(element_text) > 2:
                                                    print(f"SEARCH Clicking on element: {element_text}")
                                                    element.click()
                                                    time.sleep(random.uniform(2, 4))
                                                    
                                                    handle_popups()
                                                    
                                                    # Scroll to load products
                                                    print(f"SCROLL Scrolling to load products...")
                                                    for j in range(5):
                                                        page.mouse.wheel(0, random.randint(600, 1000))
                                                        time.sleep(random.uniform(0.6, 1.2))
                                                    
                                                    page.wait_for_timeout(random.uniform(2000, 4000))
                                                    
                                                    category_products = extract_dia_products(page)
                                                    if category_products:
                                                        all_products.extend(category_products)
                                                        print(f"SUCCESS Extracted {len(category_products)} products from {element_text}")
                                                        break
                                                    
                                                    # Go back to homepage
                                                    page.goto(BASE_URL, timeout=60000)
                                                    time.sleep(random.uniform(1, 3))
                                                    handle_popups()
                                                    
                                            except Exception as e:
                                                print(f"ERROR Error with element {i}: {e}")
                                                continue
                                    except Exception as e:
                                        print(f"ERROR Error with clickable elements: {e}")
                                
                                break  # If we found elements, stop trying other approaches
                            
                        except Exception as e:
                            print(f"ERROR Error with {approach['name']}: {e}")
                            continue
                    
                    if not all_products:
                        print("ERROR No products found from any approach.")
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
                            existing_product = get_product_by_name_and_store(product["name"], "dia")
                            if existing_product:
                                if existing_product['price'] != product["price"]:
                                    print(f"RETRY [{i}] Price updated: {product['name']} {existing_product['price']}€ → {product['price']}€")
                                    update_product_price(existing_product['id'], product["price"])
                                else:
                                    print(f"SKIP [{i}] No change: {product['name']}")
                            else:
                                insert_product(product["name"], product["price"], product["category"], "dia", product["quantity"])
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
    scrape_dia() 