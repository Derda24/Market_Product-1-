import time
import datetime
from playwright.sync_api import sync_playwright
from utils.db import insert_product, get_product_by_name_and_store, update_product_price, supabase
from utils.logger import log_debug_message as log
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = "https://www.bonarea-online.com"

print("Script starting...")

# Test Supabase connection at startup
print("RETRY Checking Supabase connection...")
try:
    test = supabase.table("products").select("count").limit(1).execute()
    print("SUCCESS: Supabase connection successful")
except Exception as e:
    print(f"ERROR: Supabase connection failed: {str(e)}")
    print("Please check your .env file contains valid SUPABASE_URL and SUPABASE_KEY")
    exit(1)

def scroll_to_load_all_products(page, pause_time=2, max_scrolls=20):
    last_height = 0
    for i in range(max_scrolls):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_time)
        new_height = page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
            print(f"SUCCESS: All products loaded after {i+1} scrolls.")
            break
        last_height = new_height
        print(f"RETRY Scrolled {i+1} times")

def extract_bonarea_products(page, category):
    """Extract products from BonÀrea main page"""
    try:
        # Wait for products to load
        page.wait_for_selector('.block-product', timeout=15000)
    except Exception as e:
        print(f"WARN Error waiting for products: {e}")

    # Find all product elements
    product_elements = page.query_selector_all('.block-product')
    
    if not product_elements:
        print("ERROR: No product elements found")
        page.screenshot(path="bonarea_debug.png", full_page=True)
        with open("bonarea_debug.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print("📸 Screenshot saved to bonarea_debug.png, HTML saved to bonarea_debug.html")
        return []

    print(f"🔎 Found {len(product_elements)} products.")

    results = []
    for i, el in enumerate(product_elements, 1):
        try:
            # Extract product name
            name_el = el.query_selector('.text p')
            if not name_el:
                print(f"WARN Skipped product {i}: Could not find name")
                continue
            name = name_el.inner_text().strip()
            
            if not name:
                print(f"WARN Skipped product {i}: Empty name")
                continue

            # Extract price
            price_el = el.query_selector('.price span')
            if not price_el:
                print(f"WARN Skipped product {i}: Could not find price")
                continue
                
            price_text = price_el.inner_text().strip()
            try:
                # Extract numeric value from price text
                import re
                price_match = re.search(r'(\d+[.,]\d+|\d+)', price_text.replace(',', '.'))
                if price_match:
                    price = float(price_match.group(1).replace(',', '.'))
                else:
                    print(f"WARN Skipped product {i}: Invalid price format")
                    continue
            except ValueError:
                print(f"WARN Skipped product {i}: Could not parse price")
                continue

            # Extract quantity
            quantity_el = el.query_selector('.weight')
            quantity = quantity_el.inner_text().strip() if quantity_el else "1 unit"

            results.append({
                "name": name,
                "price": price,
                "quantity": quantity,
                "category": category,
            })
        except Exception as e:
            print(f"WARN Error processing product {i}: {e}")
    return results

def scrape_bonarea():
    print("Starting BonÀrea scraper...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )

        try:
            print("GLOBE Visiting BonÀrea homepage...")
            page.goto(f"{BASE_URL}/ca/shop", timeout=60000)
            time.sleep(3)
            print("Current URL:", page.url)

            # Handle cookie popup if present
            try:
                cookie_button = page.query_selector('button:has-text("Acceptar")') or \
                               page.query_selector('button:has-text("Aceptar")') or \
                               page.query_selector('button:has-text("Accept")')
                if cookie_button:
                    cookie_button.click()
                    print("COOKIE Cookie popup accepted")
                    time.sleep(2)
            except Exception:
                print("WARN Cookie popup not found or already accepted.")

            # Scroll to load more products
            print("SCROLL Scrolling to load products...")
            for i in range(15):
                page.mouse.wheel(0, 1000)
                time.sleep(0.5)
                
                # Check if more products loaded
                current_products = page.query_selector_all('.block-product')
                if i % 5 == 0:
                    print(f"CHART Found {len(current_products)} products so far...")

            # Wait for any remaining dynamic content
            print("WAIT Waiting for dynamic content to load...")
            page.wait_for_timeout(5000)
            
            # Final scroll to bottom to ensure everything is loaded
            page.mouse.wheel(0, 2000)
            time.sleep(2)

            page.wait_for_timeout(3000)
            page.screenshot(path="bonarea_debug.png", full_page=True)

            products = extract_bonarea_products(page, "general")
            if not products:
                print("ERROR: No products found.")
                return

            print(f"Processing {len(products)} products...")
            for i, product in enumerate(products, 1):
                try:
                    existing_product = get_product_by_name_and_store(product["name"], "bonarea")
                    if existing_product:
                        if existing_product['price'] != product["price"]:
                            print(f"RETRY [{i}] Price updated: {product['name']} {existing_product['price']}€ → {product['price']}€")
                            update_product_price(existing_product['id'], product["price"])
                        else:
                            print(f"SKIP [{i}] No change: {product['name']}")
                    else:
                        insert_product(product["name"], product["price"], product["category"], "bonarea", product["quantity"])
                        print(f"SUCCESS: [{i}] Inserted: {product['name']} — {product['price']}€ ({product['quantity']})")
                except Exception as e:
                    print(f"ERROR: DB error on product {i}: {e}")

        except Exception as e:
            print(f"ERROR: Scraping failed: {e}")
        finally:
            browser.close()
            print("FINISH Scraper finished.")

if __name__ == "__main__":
    # Verify Playwright installation
    print("SEARCH Checking required packages...")
    try:
        import playwright
        print("SUCCESS: Playwright is installed")
    except ImportError:
        print("ERROR: Playwright is not installed")
        print("Please run: pip install playwright")
        print("Then run: playwright install")
        exit(1)

    scrape_bonarea()