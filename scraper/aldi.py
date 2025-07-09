import time
from playwright.sync_api import sync_playwright
from utils.db import insert_product, get_product_by_name_and_store, update_product_price
from utils.logger import log_debug_message
from utils.proxy_handler import get_browser_with_proxy

def scroll_to_load_all(page, scroll_pause=2, max_scrolls=10):
    prev_height = 0
    for i in range(max_scrolls):
        page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        time.sleep(scroll_pause)
        curr_height = page.evaluate("document.body.scrollHeight")
        if curr_height == prev_height:
            break
        prev_height = curr_height
        log_debug_message(f"🔄 Scroll {i + 1}/{max_scrolls} complete")
        print(f"🔄 Scroll {i + 1}/{max_scrolls} complete")

def scrape_aldi():
    print("🚀 Starting Aldi scraper...")
    with sync_playwright() as p:
        browser = get_browser_with_proxy(p)
        page = browser.new_page()

        try:
            page.goto("https://www.aldi.es/", timeout=60000)
            page.wait_for_timeout(4000)
            log_debug_message("✅ Aldi homepage loaded.")
            print("✅ Aldi homepage loaded.")

            # Accept cookies
            try:
                btn = page.query_selector('button[data-testid="uc-accept-all-button"]')
                if btn:
                    btn.click()
                    page.wait_for_timeout(1000)
                    log_debug_message("🍪 Cookie popup accepted.")
                    print("🍪 Cookie popup accepted.")
            except Exception:
                pass

            scroll_to_load_all(page, max_scrolls=15)

            page.wait_for_selector('.mod-article-tile', timeout=15000)
            products = page.query_selector_all('.mod-article-tile')
            log_debug_message(f"🔍 Found {len(products)} products on page.")
            print(f"🔍 Found {len(products)} products on page.")

            inserted_count = 0
            skipped_count = 0
            total_count = len(products)

            for i, product in enumerate(products, 1):
                try:
                    name_el = product.query_selector('.mod-article-tile__title')
                    price_el = product.query_selector('.price__wrapper')

                    if not name_el or not price_el:
                        continue

                    name = name_el.inner_text().strip()
                    price_text = price_el.inner_text().strip()
                    price = float(price_text.replace("€", "").replace(",", ".").split()[0])
                    quantity = "1 unit"  # Default quantity for Aldi products

                    # Progress indicator
                    print(f"\n[{i}/{total_count}] ✨ Processing: {name}")

                    # Always insert the product (don't check if it exists)
                    try:
                        insert_product(
                            name=name,
                            price=price,
                            category="general",
                            store_id="aldi",
                            quantity=quantity
                        )
                        inserted_count += 1
                        print(f"✅ Added: {name} - {price}€ {quantity}")
                    except Exception as e:
                        print(f"❌ Failed to insert product: {str(e)}")
                        # If it's a duplicate key error, that's expected
                        if "duplicate key" in str(e).lower():
                            print(f"ℹ️ Product already exists: {name}")
                            skipped_count += 1
                except Exception as e:
                    log_debug_message(f"⚠️ Error: {e}")
                    print(f"⚠️ Error processing product {i}: {e}")

        except Exception as e:
            log_debug_message(f"❌ Failed to load Aldi: {e}")
            print(f"❌ Failed to load Aldi: {e}")
        finally:
            browser.close()
            print("🏁 Aldi scraping completed!")

if __name__ == "__main__":
    scrape_aldi()
