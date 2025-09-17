from playwright.sync_api import sync_playwright
from utils.db import insert_product, get_product_by_name_and_store, update_product_price
from utils.proxy_handler import get_browser_with_proxy

def scrape_mercadona():
    print("START Starting Mercadona scraper...")
    with sync_playwright() as p:
        browser = get_browser_with_proxy(p)
        page = browser.new_page()
        
        page.goto("https://tienda.mercadona.es/")
        print("SUCCESS Page loaded successfully!")

        page.wait_for_load_state("networkidle", timeout=120000)

        # Wait for product cards to load
        page.wait_for_selector('.product-cell', timeout=60000)

        products = page.query_selector_all(".product-cell")
        print(f"🔎 Found {len(products)} products")

        inserted_count = 0
        updated_count = 0
        skipped_count = 0

        for i, product in enumerate(products, 1):
            try:
                # Product name
                name_element = product.query_selector(".product-cell__description-name")
                if not name_element:
                    print(f"WARN Product {i}: Name not found!")
                    continue
                name = name_element.inner_text().strip()

                # Product image
                img_element = product.query_selector("img")
                if img_element:
                    image_url = img_element.get_attribute("src")
                else:
                    image_url = None
                    print(f"WARN Product {i} '{name}': Image not found!")

                # Try different price selectors
                price_element = product.query_selector(".product-price__unit-price")  # Alternative price field
                if not price_element:
                    price_element = product.query_selector(".product-cell__price-price")  # Old one we tried

                if not price_element:
                    print(f"WARN Product {i} '{name}': Price not found!")
                    continue

                price_text = price_element.inner_text().strip()

                if not price_text:
                    print(f"WARN Product {i} '{name}': Price is empty!")
                    continue

                price = float(price_text.replace("€", "").replace(",", ".").strip())

                # Check if product exists
                existing_product = get_product_by_name_and_store(name, "mercadona")
                
                if existing_product:
                    # Product exists, check for price change
                    if existing_product['price'] != price:
                        print(f"RETRY [{i}/{len(products)}] Price changed for {name}: {existing_product['price']}€ -> {price}€")
                        update_product_price(existing_product['id'], price)
                        updated_count += 1
                    else:
                        print(f"SKIP [{i}/{len(products)}] No changes for {name}")
                        skipped_count += 1
                else:
                    # Product doesn't exist, insert it
                    insert_product(name, price, "general", "mercadona", "1 unit")
                    print(f"SUCCESS [{i}/{len(products)}] Added: {name} - {price}€")
                    inserted_count += 1

            except Exception as e:
                print(f"WARN Error processing product {i}: {e}")
                continue
        
        print(f"\nCHART Summary:")
        print(f"   Products added: {inserted_count}")
        print(f"   Products updated: {updated_count}")
        print(f"   Products skipped: {skipped_count}")
        
        browser.close()
        print("FINISH Mercadona scraping completed!")

# Run the function
if __name__ == "__main__":
    scrape_mercadona()
