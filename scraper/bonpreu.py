import time
import datetime
import json
import re
from playwright.sync_api import sync_playwright
from utils.db import insert_product, get_product_by_name_and_store, update_product_price, supabase
from utils.logger import log_debug_message as log
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = "https://www.compraonline.bonpreuesclat.cat"

print("START Bonpreu scraper starting...")

# Test Supabase connection at startup
print("RETRY Checking Supabase connection...")
try:
    test = supabase.table("products").select("count").limit(1).execute()
    print("SUCCESS Supabase connection successful")
except Exception as e:
    print(f"ERROR Supabase connection failed: {str(e)}")
    print("Please check your .env file contains valid SUPABASE_URL and SUPABASE_KEY")
    exit(1)

def save_debug_html(html, filename="bonpreu_debug.html"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"SUCCESS HTML saved as {filename}")

def extract_bonpreu_products(page, category):
    """Extract products from Bonpreu main page"""
    try:
        # Wait for React app to load
        page.wait_for_selector('div[data-test="product-grid"]', timeout=20000)
    except Exception as e:
        print(f"WARN Error waiting for product grid: {e}")
        # Try alternative selectors
        try:
            page.wait_for_selector('[data-test="product-card"]', timeout=15000)
        except Exception:
            try:
                page.wait_for_selector('.product-card', timeout=10000)
            except Exception:
                try:
                    page.wait_for_selector('[class*="product"]', timeout=10000)
                except Exception:
                    print("WARN All product selectors failed")

    # Find all product elements - try multiple selectors
    product_elements = page.query_selector_all('[data-test="product-card"]')
    if not product_elements:
        product_elements = page.query_selector_all('.product-card')
    if not product_elements:
        product_elements = page.query_selector_all('[class*="product"]')
    if not product_elements:
        product_elements = page.query_selector_all('[class*="Product"]')
    if not product_elements:
        product_elements = page.query_selector_all('article')
    if not product_elements:
        product_elements = page.query_selector_all('div[role="article"]')
    
    if not product_elements:
        print("ERROR No product elements found")
        page.screenshot(path="bonpreu_debug.png", full_page=True)
        with open("bonpreu_debug.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print("📸 Screenshot saved to bonpreu_debug.png, HTML saved to bonpreu_debug.html")
        return []

    print(f"🔎 Found {len(product_elements)} products.")

    results = []
    for i, el in enumerate(product_elements, 1):
        try:
            # Extract product name - try multiple selectors
            name_el = el.query_selector('[data-test="product-card-name"]') or \
                     el.query_selector('[data-test="product-name"]') or \
                     el.query_selector('.product-name') or \
                     el.query_selector('.product-title') or \
                     el.query_selector('h3') or \
                     el.query_selector('h2') or \
                     el.query_selector('a') or \
                     el.query_selector('[class*="name"]') or \
                     el.query_selector('[class*="title"]')
            
            if not name_el:
                print(f"WARN Skipped product {i}: Could not find name")
                continue
            name = name_el.inner_text().strip()
            
            if not name:
                print(f"WARN Skipped product {i}: Empty name")
                continue

            # Extract price - try multiple selectors
            price_el = el.query_selector('[data-test="product-card-price"]') or \
                      el.query_selector('[data-test="product-price"]') or \
                      el.query_selector('.product-price') or \
                      el.query_selector('[class*="price"]') or \
                      el.query_selector('span[class*="Price"]') or \
                      el.query_selector('[class*="cost"]') or \
                      el.query_selector('[class*="Price"]')
            
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

            # Extract quantity (if available)
            quantity_el = el.query_selector('.product-quantity') or \
                         el.query_selector('[class*="quantity"]') or \
                         el.query_selector('[class*="weight"]')
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

def scrape_bonpreu():
    print("START Starting Bonpreu scraper...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )

        try:
            print("GLOBE Visiting Bonpreu homepage...")
            page.goto(BASE_URL, timeout=60000)
            time.sleep(3)
            print("Current URL:", page.url)

            # Handle cookie popup if present
            try:
                cookie_button = page.query_selector('button:has-text("Acceptar")') or \
                               page.query_selector('button:has-text("Aceptar")') or \
                               page.query_selector('button:has-text("Accept")') or \
                               page.query_selector('#onetrust-accept-btn-handler')
                if cookie_button:
                    cookie_button.click()
                    print("COOKIE Cookie popup accepted")
                    time.sleep(2)
            except Exception:
                print("WARN Cookie popup not found or already accepted.")

            # Try to navigate to a product category
            try:
                # Look for category links
                category_links = page.query_selector_all('a[href*="/categories/"]')
                if category_links:
                    print("LINK Found category links, clicking first one...")
                    category_links[0].click()
                    time.sleep(3)
                    print("Current URL after category click:", page.url)
                else:
                    print("WARN No category links found, staying on homepage")
            except Exception as e:
                print(f"WARN Error navigating to category: {e}")

            # Scroll to load more products
            print("SCROLL Scrolling to load products...")
            for i in range(15):
                page.mouse.wheel(0, 1000)
                time.sleep(0.5)
                
                # Check if more products loaded
                current_products = page.query_selector_all('[data-test="product-card"]')
                if not current_products:
                    current_products = page.query_selector_all('.product-card')
                if not current_products:
                    current_products = page.query_selector_all('.product-item')
                if i % 5 == 0:
                    print(f"CHART Found {len(current_products)} products so far...")

            # Wait for any remaining dynamic content
            print("WAIT Waiting for dynamic content to load...")
            page.wait_for_timeout(5000)
            
            # Final scroll to bottom to ensure everything is loaded
            page.mouse.wheel(0, 2000)
            time.sleep(2)

            page.wait_for_timeout(3000)
            page.screenshot(path="bonpreu_debug.png", full_page=True)

            products = extract_bonpreu_products(page, "general")
            if not products:
                print("ERROR No products found.")
                return

            print(f"BOX Processing {len(products)} products...")
            for i, product in enumerate(products, 1):
                try:
                    existing_product = get_product_by_name_and_store(product["name"], "bonpreu")
                    if existing_product:
                        if existing_product['price'] != product["price"]:
                            print(f"RETRY [{i}] Price updated: {product['name']} {existing_product['price']}€ → {product['price']}€")
                            update_product_price(existing_product['id'], product["price"])
                        else:
                            print(f"SKIP [{i}] No change: {product['name']}")
                    else:
                        insert_product(product["name"], product["price"], product["category"], "bonpreu", product["quantity"])
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

    scrape_bonpreu()
