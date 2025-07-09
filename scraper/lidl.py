import time
import datetime
import json
import re
from playwright.async_api import async_playwright
from utils.db import insert_product, get_product_by_name_and_store, update_product_price, supabase
from utils.logger import log_debug_message as log
import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import asyncio

# Load environment variables
load_dotenv()

BASE_URL = "https://www.lidl.es"

print("🚀 Lidl scraper starting...")

# Test Supabase connection at startup
print("🔄 Checking Supabase connection...")
try:
    test = supabase.table("products").select("count").limit(1).execute()
    print("✅ Supabase connection successful")
except Exception as e:
    print(f"❌ Supabase connection failed: {str(e)}")
    print("Please check your .env file contains valid SUPABASE_URL and SUPABASE_KEY")
    exit(1)

def save_debug_html(html, filename="lidl_debug.html"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ HTML saved as {filename}")

async def get_all_categories(page):
    """Extract all subcategory URLs from the navigation menu on the main food category page."""
    print("🔍 Extracting all categories from main food page...")
    await page.goto(f"{BASE_URL}/es/c/comprar-alimentos/c1856", timeout=60000)
    await page.wait_for_load_state('networkidle')
    # Handle cookie consent if present
    try:
        await page.click('#onetrust-accept-btn-handler', timeout=5000)
        await page.wait_for_timeout(1000)
    except:
        pass
    # Handle store/location selection overlay if present
    try:
        await page.click('button[aria-label*="Cerrar"], button[aria-label*="close"], button[data-test*="close"]', timeout=5000)
        await page.wait_for_timeout(1000)
    except:
        pass
    # Try clicking all .shifter-handle elements until menu opens
    try:
        handles = await page.query_selector_all('.shifter-handle')
        for idx, handle in enumerate(handles):
            print(f"   Trying to click .shifter-handle #{idx+1}...")
            try:
                await handle.click(timeout=2000)
                await page.wait_for_timeout(1000)
                body_class = await page.evaluate('document.body.className')
                if 'shifter-open' in body_class:
                    print("   ✅ Menu opened!")
                    break
            except Exception as e:
                print(f"   ⚠️ Could not click handle #{idx+1}: {e}")
    except Exception as e:
        print(f"   ⚠️ Could not find or click any .shifter-handle: {e}")
    html = await page.content()
    save_debug_html(html, "lidl_main_page.html")
    soup = BeautifulSoup(html, "html.parser")
    categories = []
    nav = soup.find('div', {'id': 'navigation-menu'})
    if nav:
        for a in nav.find_all('a', href=True):
            href = a['href']
            title = a.get('title') or a.get_text(strip=True)
            # Accept both absolute and relative category links
            if href.startswith('/c/') or href.startswith('c/'):
                full_url = BASE_URL + href if href.startswith('/') else BASE_URL + '/' + href
                categories.append({'title': title, 'url': full_url})
    print(f"📂 Found {len(categories)} subcategories")
    for cat in categories:
        print(f"   - {cat['title']}")
    return categories

async def get_product_links_from_category(page, category_info):
    """Get all product links from a category page, handling dynamic loading."""
    try:
        category_url = category_info["url"]
        category_title = category_info["title"]
        print(f"🔗 Visiting category: {category_title} ({category_url})")
        await page.goto(category_url, timeout=60000)
        # Wait for product grid to appear (dynamic content)
        try:
            await page.wait_for_selector('.product-grid-box-tile', timeout=15000)
        except Exception:
            print(f"   ⚠️ Product grid not found after waiting, will save debug HTML.")
        # Scroll to bottom to trigger lazy loading (repeat a few times)
        for _ in range(5):
            await page.mouse.wheel(0, 10000)
            await page.wait_for_timeout(1000)
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        product_links = []
        product_tiles = soup.select(".product-grid-box-tile")
        for tile in product_tiles:
            link_elem = tile.select_one("a[href*='/p/']")
            if link_elem:
                href = link_elem.get("href", "")
                if href:
                    if href.startswith("http"):
                        full_url = href
                    else:
                        full_url = f"{BASE_URL}/{href.lstrip('/')}"
                    product_links.append(full_url)
        if not product_links:
            debug_filename = f"lidl_category_debug_{category_title.replace(' ', '_')}.html"
            save_debug_html(html, debug_filename)
            print(f"   💾 Saved debug HTML as {debug_filename}")
        product_links = list(set(product_links))
        print(f"   📦 Found {len(product_links)} products")
        return product_links
    except Exception as e:
        print(f"❌ Error getting products from {category_info['title']}: {e}")
        return []

async def scrape_product_details(page, product_url):
    """Extract product details from a product page"""
    try:
        await page.goto(product_url, timeout=30000)
        await page.wait_for_load_state('networkidle')
        
        # Wait a bit for dynamic content to load
        await page.wait_for_timeout(2000)
        
        # Handle cookie consent if present
        try:
            await page.click('#onetrust-accept-btn-handler', timeout=3000)
            await page.wait_for_timeout(1000)
        except:
            pass

        # Try multiple selectors for product title
        title_selectors = [
            "h1",
            ".product-title",
            ".product-name",
            "[data-test='product-title']",
            ".product-details h1",
            ".product-info h1"
        ]
        
        name_elem = None
        for selector in title_selectors:
            try:
                name_elem = await page.query_selector(selector)
                if name_elem:
                    break
            except:
                continue
        
        if not name_elem:
            # Save debug HTML for this product page
            html = await page.content()
            debug_filename = f"lidl_product_debug_{product_url.split('/')[-1]}.html"
            save_debug_html(html, debug_filename)
            print(f"⚠️ Product title not found for {product_url}")
            print(f"   💾 Saved debug HTML as {debug_filename}")
            return None
        
        # Try multiple selectors for price
        price_selectors = [
            ".price",
            ".product-price",
            ".price-value",
            "[data-test='product-price']",
            ".current-price",
            ".price__current"
        ]
        
        price_elem = None
        for selector in price_selectors:
            try:
                price_elem = await page.query_selector(selector)
                if price_elem:
                    break
            except:
                continue
        
        # Try multiple selectors for quantity/weight
        quantity_selectors = [
            ".quantity",
            ".product-quantity",
            ".weight",
            ".product-weight",
            "[data-test='product-quantity']",
            ".unit"
        ]
        
        quantity_elem = None
        for selector in quantity_selectors:
            try:
                quantity_elem = await page.query_selector(selector)
                if quantity_elem:
                    break
            except:
                continue

        if not name_elem or not price_elem:
            print(f"⚠️ Missing name or price for {product_url}")
            return None
        
        name = await name_elem.inner_text()
        price_text = await price_elem.inner_text()
        quantity = await quantity_elem.inner_text() if quantity_elem else ""
        
        # Clean price - handle different formats
        try:
            # Remove currency symbols and clean up
            price_clean = price_text.replace("€", "").replace(",", ".").strip()
            # Extract first number from the text
            price_match = re.search(r'[\d,]+\.?\d*', price_clean)
            if price_match:
                price_clean = price_match.group().replace(",", ".")
            clean_price = float(price_clean)
        except ValueError:
            print(f"⚠️ Invalid price format: {price_text}")
            return None
        
        return {
            "name": name.strip(),
            "price": clean_price,
            "quantity": quantity.strip(),
            "url": product_url
        }
        
    except Exception as e:
        print(f"❌ Error extracting product from {product_url}: {e}")
        return None

async def process_product(product_data, category_name):
    """Process a single product - check if exists, update or insert"""
    name = product_data["name"]
    price = product_data["price"]
    quantity = product_data["quantity"]
    
    print(f"   ✨ Processing: {name}")
    
    # Check if product already exists
    existing_product = get_product_by_name_and_store(name, "lidl")
    
    if existing_product:
        if existing_product['price'] != price:
            update_product_price(existing_product['id'], price, store_id="lidl")
            print(f"   🔄 Updated price for {name}: {existing_product['price']}€ → {price}€")
            return "updated"
        else:
            print(f"   ⏭️ No changes for {name}")
            return "skipped"
    else:
        try:
            insert_product(
                name=name,
                price=price,
                category=category_name,
                store_id="lidl",
                quantity=quantity
            )
            print(f"   ✅ Added: {name} - {price}€ {quantity}")
            return "inserted"
        except Exception as e:
            print(f"   ❌ Failed to insert product: {str(e)}")
            return "error"

async def scrape_lidl_products():
    """Main scraping function for Lidl"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Get all categories
            categories = await get_all_categories(page)
            
            total_inserted = 0
            total_updated = 0
            total_skipped = 0
            total_errors = 0
            
            for idx, category_info in enumerate(categories, 1):
                print(f"\n[{idx}/{len(categories)}] Processing category: {category_info['title']}")
                
                # Get product links from this category
                product_urls = await get_product_links_from_category(page, category_info)
                
                if not product_urls:
                    print(f"   ⚠️ No products found in category")
                    continue
                
                # Process each product
                for i, product_url in enumerate(product_urls, 1):
                    print(f"   [{i}/{len(product_urls)}] Fetching product details...")
                    
                    product_data = await scrape_product_details(page, product_url)
                    if product_data:
                        result = await process_product(product_data, category_info['title'])
                        if result == "inserted":
                            total_inserted += 1
                        elif result == "updated":
                            total_updated += 1
                        elif result == "skipped":
                            total_skipped += 1
                        else:
                            total_errors += 1
                    else:
                        total_errors += 1
                
                print(f"   📊 Category summary:")
                print(f"      Products found: {len(product_urls)}")
                print(f"      Products processed: {len(product_urls)}")
            
            print("\n🎉 Lidl scraping completed!")
            print(f"   Total products added: {total_inserted}")
            print(f"   Total products updated: {total_updated}")
            print(f"   Total products skipped: {total_skipped}")
            print(f"   Total errors: {total_errors}")
            
        finally:
            await browser.close()

async def extract_and_save_category_urls():
    """Extract all Lidl Spain food subcategory URLs from navigation JSON and save to lidl_categories.json."""
    nav_url = f"{BASE_URL}/first-level-navigation-json?warehouseKey=0"
    resp = requests.get(nav_url)
    resp.raise_for_status()
    nav_json = resp.json()
    categories = []
    def extract_categories(nodes):
        for node in nodes:
            url = node.get('url')
            title = node.get('displayName') or node.get('name')
            if url and url.startswith('/es/c/'):
                categories.append({'title': title, 'url': BASE_URL + url})
            # Recursively extract children
            if 'children' in node and node['children']:
                extract_categories(node['children'])
    extract_categories(nav_json)
    with open('lidl_categories.json', 'w', encoding='utf-8') as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved {len(categories)} category URLs to lidl_categories.json")

async def scrape_category_products(page, category_url):
    print(f"\n🔎 Scraping category: {category_url}")
    await page.goto(category_url, timeout=60000)
    await page.wait_for_load_state('networkidle')
    # Accept cookies if present
    try:
        await page.click('#onetrust-accept-btn-handler', timeout=5000)
        await page.wait_for_timeout(1000)
    except:
        pass
    # Wait for product grid
    await page.wait_for_selector('li.grid-item', timeout=15000)
    # Scroll to load all products (lazy loading)
    previous_count = 0
    for _ in range(20):  # max 20 scrolls
        items = await page.query_selector_all('li.grid-item')
        if len(items) == previous_count:
            break
        previous_count = len(items)
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await page.wait_for_timeout(1200)
    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")
    products = []
    for li in soup.select('li.grid-item'):
        a = li.select_one('a.clickable')
        if not a:
            continue
        url = a['href']
        full_url = BASE_URL + url if url.startswith('/') else url
        img = a.select_one('img')
        image_url = img['src'] if img else None
        price = a.select_one('span[class*="_price_"]')
        title = a.select_one('h2[class*="_title_"]')
        products.append({
            'url': full_url,
            'image': image_url,
            'price': price.text.strip() if price else None,
            'title': title.text.strip() if title else None,
        })
    print(f"   🛒 Found {len(products)} products in this category.")
    return products

async def main():
    # Load category URLs from file or define manually
    try:
        with open('lidl_categories.json', encoding='utf-8') as f:
            categories = json.load(f)
    except Exception:
        print("⚠️ Could not load lidl_categories.json. Please run category extraction first or provide category URLs.")
        return
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        all_products = []
        for cat in categories:
            cat_url = cat['url']
            products = await scrape_category_products(page, cat_url)
            for prod in products:
                prod['category'] = cat.get('title')
            all_products.extend(products)
        with open('lidl_products.json', 'w', encoding='utf-8') as f:
            json.dump(all_products, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Saved {len(all_products)} products to lidl_products.json")
        await browser.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "extract_categories":
        asyncio.run(extract_and_save_category_urls())
    else:
        asyncio.run(main())
