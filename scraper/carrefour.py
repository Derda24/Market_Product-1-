import time
import re
from playwright.sync_api import sync_playwright
from utils.db import insert_product, get_product_by_name_and_store, update_product_price, supabase
from utils.logger import log_debug_message as log

BASE_URL = "https://www.carrefour.es"

print("START Carrefour scraper starting...")

# Test Supabase connection at startup
print("RETRY Checking Supabase connection...")
try:
    test = supabase.table("products").select("count").limit(1).execute()
    print("SUCCESS Supabase connection successful")
except Exception as e:
    print(f"ERROR Supabase connection failed: {str(e)}")
    print("Please check your .env file contains valid SUPABASE_URL and SUPABASE_KEY")
    exit(1)

def save_debug_html(html, filename="carrefour_debug.html"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"SUCCESS HTML saved as {filename}")

def extract_carrefour_products(page, category):
    """Extract products from Carrefour category page"""
    try:
        # Wait for products to load
        page.wait_for_selector('.product-card', timeout=15000)
    except Exception as e:
        print(f"WARN Error waiting for products: {e}")
        # Try alternative selectors
        try:
            page.wait_for_selector('[data-test="product-card"]', timeout=10000)
        except Exception:
            try:
                page.wait_for_selector('[class*="product"]', timeout=10000)
            except Exception:
                print("WARN All product selectors failed")

    # Find all product elements
    product_elements = page.query_selector_all('.product-card')
    if not product_elements:
        product_elements = page.query_selector_all('[data-test="product-card"]')
    if not product_elements:
        product_elements = page.query_selector_all('[class*="product"]')
    
    if not product_elements:
        print("ERROR No product elements found")
        page.screenshot(path="carrefour_debug.png", full_page=True)
        with open("carrefour_debug.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print("📸 Screenshot saved to carrefour_debug.png, HTML saved to carrefour_debug.html")
        return []

    print(f"🔎 Found {len(product_elements)} products.")

    results = []
    for i, el in enumerate(product_elements, 1):
        try:
            # Extract product name
            name_el = el.query_selector('h2') or \
                     el.query_selector('h3') or \
                     el.query_selector('.product-title') or \
                     el.query_selector('[data-test="product-title"]') or \
                     el.query_selector('[class*="title"]')
            
            if not name_el:
                print(f"WARN Skipped product {i}: Could not find name")
                continue
            name = name_el.inner_text().strip()
            
            if not name:
                print(f"WARN Skipped product {i}: Empty name")
                continue

            # Extract price
            price_el = el.query_selector('.product-card-price__price') or \
                      el.query_selector('[data-test="product-price"]') or \
                      el.query_selector('.product-price') or \
                      el.query_selector('[class*="price"]')
            
            if not price_el:
                print(f"WARN Skipped product {i}: Could not find price")
                continue
                
            price_text = price_el.inner_text().strip()
            try:
                # Extract numeric value from price text
                price_match = re.search(r'(\d+[.,]\d+|\d+)', price_text.replace(',', '.'))
                if price_match:
                    price = float(price_match.group(1).replace(',', '.'))
                else:
                    print(f"WARN Skipped product {i}: Invalid price format")
                    continue
            except ValueError:
                print(f"WARN Skipped product {i}: Invalid price format")
                continue

            # Extract quantity (optional)
            quantity_el = el.query_selector('[class*="quantity"]') or \
                         el.query_selector('[class*="weight"]') or \
                         el.query_selector('[class*="unit"]')
            quantity = quantity_el.inner_text().strip() if quantity_el else "1 unit"

            results.append({
                "name": name,
                "price": price,
                "category": category,
                "quantity": quantity
            })

        except Exception as e:
            print(f"ERROR Error processing product {i}: {e}")
            continue

    return results

def scrape_carrefour():
    print("START Starting Carrefour scraper...")
    with sync_playwright() as p:
        # Use more stealthy browser settings
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-field-trial-config',
                '--disable-ipc-flooding-protection',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-default-apps',
                '--disable-sync',
                '--disable-translate',
                '--hide-scrollbars',
                '--mute-audio',
                '--no-zygote',
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--disable-background-networking',
                '--disable-sync-preferences',
                '--disable-background-downloads',
                '--disable-client-side-phishing-detection',
                '--disable-component-update',
                '--disable-domain-reliability',
                '--disable-features=TranslateUI'
            ]
        )
        
        # Create context with more stealthy settings
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="es-ES",
            timezone_id="Europe/Madrid",
            geolocation={"latitude": 41.3851, "longitude": 2.1734},  # Barcelona coordinates
            permissions=["geolocation"],
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "max-age=0",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1"
            }
        )
        
        # Add comprehensive stealth scripts
        context.add_init_script("""
            // Override the 'webdriver' property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Override the 'plugins' property
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Override the 'languages' property
            Object.defineProperty(navigator, 'languages', {
                get: () => ['es-ES', 'es', 'en'],
            });
            
            // Override the 'permissions' property
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Override the 'chrome' property
            Object.defineProperty(window, 'chrome', {
                writable: true,
                enumerable: true,
                configurable: true,
                value: {
                    runtime: {},
                },
            });
            
            // Override the 'outerHeight' and 'outerWidth' properties
            Object.defineProperty(window, 'outerHeight', {
                get: () => 1080,
            });
            Object.defineProperty(window, 'outerWidth', {
                get: () => 1920,
            });
            
            // Override the 'screen' property
            Object.defineProperty(window, 'screen', {
                get: () => ({
                    width: 1920,
                    height: 1080,
                    availWidth: 1920,
                    availHeight: 1040,
                    colorDepth: 24,
                    pixelDepth: 24
                }),
            });
            
            // Override the 'devicePixelRatio' property
            Object.defineProperty(window, 'devicePixelRatio', {
                get: () => 1,
            });
            
            // Override the 'innerHeight' and 'innerWidth' properties
            Object.defineProperty(window, 'innerHeight', {
                get: () => 1040,
            });
            Object.defineProperty(window, 'innerWidth', {
                get: () => 1920,
            });
        """)
        
        page = context.new_page()

        try:
            print("GLOBE Visiting Carrefour homepage...")
            
            # First visit the main homepage to establish a session
            page.goto(f"{BASE_URL}", timeout=60000)
            time.sleep(3)
            print("Current URL after homepage:", page.url)

            # Check if we hit the Cloudflare page
            page_content = page.content().lower()
            if "cloudflare" in page_content or "blocked" in page_content:
                print("WARN Hit Cloudflare security check, waiting for manual verification...")
                print("Please manually complete the security check in the browser window")
                print("Then press Enter to continue...")
                input()
                time.sleep(3)
                
                # Check if we're still on the security page
                if "cloudflare" in page.content().lower() or "blocked" in page.content().lower():
                    print("ERROR Still on security page after manual verification")
                    return

            # Handle cookie popup if present
            try:
                cookie_button = page.query_selector('button:has-text("Aceptar")') or \
                               page.query_selector('button:has-text("Accept")') or \
                               page.query_selector('button[data-test*="accept"]')
                if cookie_button:
                    cookie_button.click()
                    print("COOKIE Cookie popup accepted")
                    time.sleep(2)
            except Exception:
                print("WARN Cookie popup not found or already accepted.")

            # Try to navigate to a different category
            print("LINK Navigating to vegetables category...")
            page.goto(f"{BASE_URL}/supermercado/verdura/cat20011/c", timeout=60000)
            time.sleep(3)
            print("Current URL after category navigation:", page.url)

            # Handle any overlays or popups
            try:
                close_button = page.query_selector('button[aria-label*="Cerrar"]') or \
                              page.query_selector('button[aria-label*="close"]') or \
                              page.query_selector('button[data-test*="close"]')
                if close_button:
                    close_button.click()
                    print("STORE Overlay closed")
                    time.sleep(2)
            except Exception:
                print("WARN No overlay found.")

            # Scroll to load more products
            print("SCROLL Scrolling to load products...")
            for i in range(15):
                page.mouse.wheel(0, 1000)
                time.sleep(0.5)
                
                # Check if more products loaded
                current_products = page.query_selector_all('.product-card')
                if not current_products:
                    current_products = page.query_selector_all('[data-test="product-card"]')
                if not current_products:
                    current_products = page.query_selector_all('[class*="product"]')
                if i % 5 == 0:
                    print(f"CHART Found {len(current_products)} products so far...")

            # Wait for any remaining dynamic content
            print("WAIT Waiting for dynamic content to load...")
            page.wait_for_timeout(5000)
            
            # Final scroll to bottom to ensure everything is loaded
            page.mouse.wheel(0, 2000)
            time.sleep(2)

            page.wait_for_timeout(3000)
            
            # Try to take screenshot, but don't fail if it doesn't work
            try:
                page.screenshot(path="carrefour_debug.png", full_page=True)
            except Exception as e:
                print(f"WARN Screenshot failed: {e}")

            products = extract_carrefour_products(page, "verduras")
            if not products:
                print("ERROR No products found.")
                return

            print(f"BOX Processing {len(products)} products...")
            for i, product in enumerate(products, 1):
                try:
                    existing_product = get_product_by_name_and_store(product["name"], "carrefour")
                    if existing_product:
                        if existing_product['price'] != product["price"]:
                            print(f"RETRY [{i}] Price updated: {product['name']} {existing_product['price']}€ → {product['price']}€")
                            update_product_price(existing_product['id'], product["price"])
                        else:
                            print(f"SKIP [{i}] No change: {product['name']}")
                    else:
                        insert_product(product["name"], product["price"], product["category"], "carrefour", product["quantity"])
                        print(f"SUCCESS [{i}] Inserted: {product['name']} — {product['price']}€ ({product['quantity']})")
                except Exception as e:
                    print(f"ERROR DB error on product {i}: {e}")

        except Exception as e:
            print(f"ERROR Scraping failed: {e}")
        finally:
            browser.close()
            print("FINISH Scraper finished.")

if __name__ == "__main__":
    # Verify Playwright installation
    print("SEARCH Checking required packages...")
    try:
        import playwright
        print("SUCCESS Playwright is installed")
    except ImportError:
        print("ERROR Playwright is not installed")
        print("BOX Please run: pip install playwright")
        print("THEATER Then run: playwright install")
        exit(1)

    scrape_carrefour()
