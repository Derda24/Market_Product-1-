import time
import datetime
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
from utils.db import insert_product, get_product_by_name_and_store, update_product_price, supabase
from utils.logger import log_debug_message as log
import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

BASE_URL = "https://www.bonarea-online.com/online"

print("🚀 Script starting...")

# Test Supabase connection at startup
print("🔄 Checking Supabase connection...")
try:
    test = supabase.table("products").select("count").limit(1).execute()
    print("✅ Supabase connection successful")
except Exception as e:
    print(f"❌ Supabase connection failed: {str(e)}")
    print("Please check your .env file contains valid SUPABASE_URL and SUPABASE_KEY")
    exit(1)

def scroll_to_load_all_products(page, pause_time=2, max_scrolls=20):
    last_height = 0
    for i in range(max_scrolls):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_time)
        new_height = page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
            print(f"✅ All products loaded after {i+1} scrolls.")
            break
        last_height = new_height
        print(f"🔄 Scrolled {i+1} times")

def click_load_more_until_end(page, button_selector, pause_time=2, max_clicks=20):
    for i in range(max_clicks):
        try:
            if page.is_visible(button_selector):
                page.click(button_selector)
                print(f"🔄 Clicked 'Load more' button ({i+1})")
                time.sleep(pause_time)
            else:
                print("✅ No more 'Load more' button found.")
                break
        except Exception as e:
            print(f"⚠️ Error clicking 'Load more': {e}")
            break

def extract_product_data(page, category_name):
    print(f"\n📦 Processing category: {category_name}")
    products = page.query_selector_all(".block-product-shopping")
    print(f"🔎 Found {len(products)} product(s)")

    if not products:
        print("❌ No products found in this category")
        return False

    inserted_count = 0
    updated_count = 0
    skipped_count = 0
    total_count = len(products)
    current_count = 0

    for product in products:
        current_count += 1
        try:
            # Extract product elements
            name_elem = product.query_selector(".text p")
            price_elem = product.query_selector(".price span")
            weight_elem = product.query_selector(".weight")

            if not name_elem or not price_elem:
                print("⚠️ Missing name or price element, skipping product")
                continue

            # Extract and clean data
            name = name_elem.inner_text().strip()
            price_text = price_elem.inner_text().strip().split(" ")[0].replace(",", ".")
            try:
                price = float(price_text)
            except ValueError:
                print(f"⚠️ Invalid price format for {name}: {price_text}")
                continue

            quantity = weight_elem.inner_text().strip() if weight_elem else ""

            # Progress indicator
            print(f"\n[{current_count}/{total_count}] ✨ Processing: {name}")

            existing_product = get_product_by_name_and_store(name, "bonarea")
            if existing_product:
                if existing_product['price'] != price:
                    update_product_price(existing_product['id'], price, store_id="bonarea")
                    updated_count += 1
                    print(f"🔄 Updated price for {name}")
                else:
                    print(f"⏭️ No changes for {name}")
                    skipped_count += 1
            else:
            try:
                insert_product(
                    name=name,
                    price=price,
                    category=category_name,
                    store_id="bonarea",
                    quantity=quantity
                )
                inserted_count += 1
                print(f"✅ Added: {name} - {price}€ {quantity}")
            except Exception as e:
                print(f"❌ Failed to insert product: {str(e)}")

        except Exception as e:
            print(f"❌ Error processing product: {str(e)}")
            continue

    print(f"\n📊 Category summary for {category_name}:")
    print(f"   Total products found: {total_count}")
    print(f"   Products added: {inserted_count}")
    print(f"   Products updated: {updated_count}")
    print(f"   Products skipped: {skipped_count}")
    
    return True

async def get_all_references_from_sidebar(page):
    # Wait for the page to load
    await page.wait_for_load_state('networkidle')
    html = await page.content()
    with open("debug_bonarea.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved page HTML for inspection as debug_bonarea.html.")
    soup = BeautifulSoup(html, "html.parser")
    references = set()
    # Try to find all data-ref attributes in <a> and <button> elements
    for tag in soup.find_all(['a', 'button'], attrs={"data-ref": True}):
        ref = tag.get("data-ref")
        if ref and ("*" in ref or "_" in ref):
            references.add(ref)
    print(f"Found {len(references)} references.")
    return list(references)

async def fetch_bonarea_products_playwright(reference, category_name, context):
    all_products = []
    api_request = context.request
    response = await api_request.post(
        "https://www.bonarea-online.com/ca/shop/ShoppingBody",
        data={"reference": reference},
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.bonarea-online.com/",
        }
    )
    html = await response.text()
    soup = BeautifulSoup(html, "html.parser")
    products = soup.select(".block-product-shopping")
    for product in products:
        try:
            name_elem = product.select_one(".text p")
            price_elem = product.select_one(".price span")
            weight_elem = product.select_one(".weight")
            if not name_elem or not price_elem:
                continue
            name = name_elem.get_text(strip=True)
            price_text = price_elem.get_text(strip=True).split(" ")[0].replace(",", ".")
            try:
                price = float(price_text)
            except ValueError:
                continue
            quantity = weight_elem.get_text(strip=True) if weight_elem else ""
            all_products.append({
                "name": name,
                "price": price,
                "category": category_name,
                "quantity": quantity
            })
        except Exception as e:
            print(f"❌ Error extracting product: {e}")
    return all_products

def normalize_reference(ref):
    """Convert reference to standard format"""
    return ref.replace("_", "*")

def extract_sub_refs_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    sub_refs = set()

    # 1) Mobile accordion buttons (phone menu)
    for btn in soup.select(".button-menu-phone[data-ref]"):
        parent_ref = normalize_reference(btn["data-ref"])
        sub_refs.add(parent_ref)
        collapse_id = btn.get("data-bs-target", "").lstrip("#")
        collapse_div = soup.find("div", id=collapse_id)
        if collapse_div:
            for a in collapse_div.select("a[href*='/categories/']"):
                code = normalize_reference(a["href"].rsplit("/", 1)[-1])
                sub_refs.add(code)

    # 2) Desktop navbar links (all levels)
    for a in soup.select("ul.navbar-nav li a[href*='/categories/']"):
        code = normalize_reference(a["href"].rsplit("/", 1)[-1])
        sub_refs.add(code)

    # 3) Any other data-ref attributes (deepest level)
    for tag in soup.find_all(["a", "button"], attrs={"data-ref": True}):
        ref = normalize_reference(tag["data-ref"])
        sub_refs.add(ref)

    # 4) Any hrefs that look like category codes (deepest level)
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/categories/" in href:
            code = normalize_reference(href.rsplit("/", 1)[-1])
            if any(c.isdigit() for c in code):
                sub_refs.add(code)

    return sub_refs

async def get_leaf_references(page, reference, visited=None, max_depth=10):
    if visited is None:
        visited = set()
    if reference in visited or len(visited) > max_depth * 100:
        return set()
    visited.add(reference)
    print(f"Processing reference: {reference}")
    html = await fetch_html_for_reference(page, reference)
    sub_refs = extract_sub_refs_from_html(html) - visited
    if not sub_refs:
        print(f"  -> Leaf reference found: {reference}")
        return {reference}
    leaves = set()
    for sub_ref in sub_refs:
        leaves |= await get_leaf_references(page, sub_ref, visited, max_depth)
    return leaves

async def scrape_all_bonarea_products():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        print("🔗 Navigating to BonÀrea main page...")
        await page.goto("https://www.bonarea-online.com/ca/shop", timeout=60000)
        print("🔍 Extracting all top-level references...")
        top_refs = await get_all_references_from_sidebar(page)
        print(f"🔎 Found {len(top_refs)} top-level references.")
        # Recursively find all leaf references
        all_leaf_refs = set()
        for ref in top_refs:
            print(f"🌲 Exploring reference: {ref}")
            leaf_refs = await get_leaf_references(page, ref)
            all_leaf_refs.update(leaf_refs)
        print(f"🍃 Found {len(all_leaf_refs)} leaf references.")
        total_inserted = 0
        total_updated = 0
        total_skipped = 0
        for idx, ref in enumerate(all_leaf_refs, 1):
            print(f"\n[{idx}/{len(all_leaf_refs)}] Fetching products for reference: {ref}")
            products = await fetch_bonarea_products_playwright(ref, ref, context)
            print(f"   Products fetched: {len(products)}")
            inserted_count = 0
            updated_count = 0
            skipped_count = 0
            total_count = len(products)
            for i, product in enumerate(products, 1):
                name = product["name"]
                price = product["price"]
                quantity = product["quantity"]
                print(f"   [{i}/{total_count}] ✨ Processing: {name}")
                existing_product = get_product_by_name_and_store(name, "bonarea")
                if existing_product:
                    if existing_product['price'] != price:
                        update_product_price(existing_product['id'], price, store_id="bonarea")
                        updated_count += 1
                        print(f"   🔄 Updated price for {name}")
                    else:
                        print(f"   ⏭️ No changes for {name}")
                        skipped_count += 1
                else:
                    try:
                        insert_product(
                            name=name,
                            price=price,
                            category=ref,
                            store_id="bonarea",
                            quantity=quantity
                        )
                        inserted_count += 1
                        print(f"   ✅ Added: {name} - {price}€ {quantity}")
                    except Exception as e:
                        print(f"   ❌ Failed to insert product: {str(e)}")
            print(f"   📊 Reference summary for {ref}:")
            print(f"      Products found: {total_count}")
            print(f"      Products added: {inserted_count}")
            print(f"      Products updated: {updated_count}")
            print(f"      Products skipped: {skipped_count}")
            total_inserted += inserted_count
            total_updated += updated_count
            total_skipped += skipped_count
        await browser.close()
        print("\n🎉 Scraping completed!")
        print(f"   Total products added: {total_inserted}")
        print(f"   Total products updated: {total_updated}")
        print(f"   Total products skipped: {total_skipped}")

async def fetch_html_for_reference(page, reference):
    """Fetch HTML for a specific reference using POST request"""
    try:
        # Use the same POST request logic as in your main scraper
        response = await page.request.post(
            "https://www.bonarea.com/shop/ShoppingBody",
            data={"reference": reference}
        )
        return await response.text()
    except Exception as e:
        print(f"Error fetching HTML for reference {reference}: {e}")
        return ""

async def get_all_product_references(page):
    """Get all leaf references that contain products"""
    # Start with the main page to get initial references
    await page.goto("https://www.bonarea.com")
    html = await page.content()
    
    # Get top-level references
    top_level_refs = extract_sub_refs_from_html(html)
    print(f"Found {len(top_level_refs)} top-level references: {top_level_refs}")
    
    # Get all leaf references
    all_leaves = set()
    for ref in top_level_refs:
        leaves = await get_leaf_references(page, ref)
        all_leaves.update(leaves)
    
    print(f"Total leaf references: {len(all_leaves)}")
    return all_leaves

async def test_reference_extraction():
    async with sync_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            all_refs = await get_all_product_references(page)
            print(f"Final references to scrape: {sorted(all_refs)}")
            
            # Test a few references to see if they return products
            for ref in list(all_refs)[:3]:
                html = await fetch_html_for_reference(page, ref)
                soup = BeautifulSoup(html, "html.parser")
                products = soup.select(".product-item")  # Adjust selector
                print(f"Reference {ref}: {len(products)} products")
                
        finally:
            await browser.close()

if __name__ == "__main__":
    # Verify Playwright installation
    print("🔍 Checking required packages...")
    try:
        import playwright
        print("✅ Playwright is installed")
    except ImportError:
        print("❌ Playwright is not installed")
        print("📦 Please run: pip install playwright")
        print("🎭 Then run: playwright install")
        exit(1)

    import asyncio
    asyncio.run(scrape_all_bonarea_products())