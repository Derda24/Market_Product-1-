from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from utils.db import insert_product, get_product_by_name_and_store, update_product_price
from utils.logger import log_debug_message
import time, os

BASE_URL = "https://www.compraonline.alcampo.es"
CATEGORY_URL = f"{BASE_URL}/supermercado/verduras-y-hortalizas"
OUTPUT_HTML = "alcampo_debug.html"

def extract_product_data(page, category):
    try:
        # Wait for product cards to be visible
        page.wait_for_selector('article[data-test="product-card"]', timeout=15000)
    except PlaywrightTimeout:
        with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
            f.write(page.content())
        print(f"❌ Timeout — HTML saved as {OUTPUT_HTML}")
        return []

    cards = page.query_selector_all('article[data-test="product-card"]')
    print(f"🔎 Found {len(cards)} product cards.")

    results = []
    for i, card in enumerate(cards, 1):
        try:
            name_el = card.query_selector("h2")
            price_el = card.query_selector('[data-test="product-card-price"]')
            quantity_el = card.query_selector('[data-test="product-card-quantity"]')
            
            if not name_el or not price_el:
                print(f"⚠️ Skipped card {i}: Missing name or price")
                continue

            name = name_el.inner_text().strip()
            price_text = price_el.inner_text()
            price = float(price_text.replace("€", "").replace(",", ".").strip())
            quantity = quantity_el.inner_text().strip() if quantity_el else "1 unit"

            results.append({
                "name": name,
                "price": price,
                "quantity": quantity,
                "category": category,
            })
        except Exception as e:
            print(f"⚠️ Error processing card {i}: {e}")

    return results

def scrape_alcampo():
    print("🚀 Starting Alcampo scraper...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print(f"🌐 Visiting {CATEGORY_URL}")

        try:
            page.goto("https://www.compraonline.alcampo.es/", timeout=60000)
            print("✅ Page loaded successfully")
            
            # Wait for page to fully load
            time.sleep(3)
            
            # Try to accept cookies if popup appears
            try:
                cookie_button = page.query_selector('button[data-test="cookie-accept"]') or \
                              page.query_selector('button:has-text("Aceptar")') or \
                              page.query_selector('button:has-text("Accept")')
                if cookie_button:
                    cookie_button.click()
                    time.sleep(1)
                    print("🍪 Cookie popup accepted")
            except Exception:
                pass

            products = extract_product_data(page, "verduras-y-hortalizas")
            if not products:
                print("❌ No products found.")
                return

            print(f"📦 Processing {len(products)} products...")
            
            for i, product in enumerate(products, 1):
                try:
                    # Check if product exists
                    existing_product = get_product_by_name_and_store(product["name"], "alcampo")
                    
                    if existing_product:
                        # Product exists, check for price change
                        if existing_product['price'] != product["price"]:
                            print(f"🔄 [{i}/{len(products)}] Price changed for {product['name']}: {existing_product['price']}€ -> {product['price']}€")
                            update_product_price(existing_product['id'], product["price"])
                        else:
                            print(f"⏭️ [{i}/{len(products)}] No changes for {product['name']}")
                    else:
                        # Product doesn't exist, insert it
                        insert_product(
                            product["name"],
                            product["price"],
                            product["category"],
                            "alcampo",
                            product["quantity"]
                        )
                        print(f"✅ [{i}/{len(products)}] Inserted: {product['name']} — {product['price']}€ ({product['quantity']})")
                except Exception as e:
                    print(f"❌ Error processing product {i}: {e}")

        except Exception as e:
            print(f"❌ Failed: {e}")
        finally:
            browser.close()
            print("🏁 Alcampo scraping completed!")

if __name__ == "__main__":
    scrape_alcampo()
