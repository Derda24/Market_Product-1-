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

BASE_URL = "https://www.compraonline.bonpreuesclat.cat"

print("🚀 Bonpreu scraper starting...")

# Test Supabase connection at startup
print("🔄 Checking Supabase connection...")
try:
    test = supabase.table("products").select("count").limit(1).execute()
    print("✅ Supabase connection successful")
except Exception as e:
    print(f"❌ Supabase connection failed: {str(e)}")
    print("Please check your .env file contains valid SUPABASE_URL and SUPABASE_KEY")
    exit(1)

def save_debug_html(html, filename="bonpreu_debug.html"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ HTML saved as {filename}")

async def get_all_categories(page):
    """Extract all category URLs from the main page"""
    print("🔍 Extracting all categories...")
    await page.goto(BASE_URL, timeout=60000)
    await page.wait_for_load_state('networkidle')
    
    html = await page.content()
    save_debug_html(html, "bonpreu_main_page.html")
    
    soup = BeautifulSoup(html, "html.parser")
    categories = set()
    
    # Look for category links
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if "/categories/" in href and href.startswith("/"):
            full_url = BASE_URL + href
            categories.add(full_url)
    
    print(f"📂 Found {len(categories)} categories")
    return list(categories)

async def get_product_links_from_category(page, category_url):
    """Get all product links from a category page"""
    try:
        print(f"🔗 Visiting category: {category_url}")
        await page.goto(category_url, timeout=30000)
        await page.wait_for_load_state('networkidle')
        
        # Wait a bit for dynamic content to load
        await page.wait_for_timeout(3000)
        
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        
        # Method 1: Try to find product cards
        product_elements = await page.query_selector_all("a[data-test='product-card-name']")
        links = []
        for el in product_elements:
            href = await el.get_attribute("href")
            if href:
                full_url = BASE_URL + href if href.startswith("/") else href
                links.append(full_url)
        
        # Method 2: Extract from structured data if no products found
        if not links:
            print("   🔍 No product cards found, checking structured data...")
            structured_data = soup.find("script", {"data-test": "product-listing-structured-data"})
            if structured_data:
                try:
                    data = json.loads(structured_data.string)
                    if "itemListElement" in data:
                        for item in data["itemListElement"]:
                            if "url" in item:
                                links.append(item["url"])
                        print(f"   📦 Found {len(links)} products from structured data")
                except Exception as e:
                    print(f"   ⚠️ Error parsing structured data: {e}")
        
        # Method 3: Look for any product links in the HTML
        if not links:
            print("   🔍 Looking for product links in HTML...")
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if "/products/" in href and href.startswith("/"):
                    full_url = BASE_URL + href
                    links.append(full_url)
        
        print(f"   📦 Found {len(links)} products")
        return links
        
    except Exception as e:
        print(f"❌ Error getting products from {category_url}: {e}")
        return []

async def scrape_product_details(page, product_url):
    """Extract product details from a product page"""
    try:
        await page.goto(product_url, timeout=30000)
        await page.wait_for_load_state('networkidle')
        
        # Wait a bit for dynamic content to load
        await page.wait_for_timeout(2000)
        
        # Try multiple selectors for product title
        title_selectors = [
            "[data-test='product-title']",
            "h1",
            ".product-title",
            ".product-name",
            "h1[data-test]",
            "[data-test*='title']"
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
            debug_filename = f"bonpreu_product_debug_{product_url.split('/')[-1]}.html"
            save_debug_html(html, debug_filename)
            print(f"⚠️ Product title not found for {product_url}")
            print(f"   💾 Saved debug HTML as {debug_filename}")
            return None
        
        # Try multiple selectors for price
        price_selectors = [
            "[data-test='product-price']",
            ".price",
            ".product-price",
            "[data-test*='price']",
            ".price-value"
        ]
        
        price_elem = None
        for selector in price_selectors:
            try:
                price_elem = await page.query_selector(selector)
                if price_elem:
                    break
            except:
                continue
        
        # Try multiple selectors for quantity
        quantity_selectors = [
            "[data-test='product-quantity']",
            ".quantity",
            ".product-quantity",
            "[data-test*='quantity']",
            ".weight"
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
    existing_product = get_product_by_name_and_store(name, "bonpreu")
    
    if existing_product:
        if existing_product['price'] != price:
            update_product_price(existing_product['id'], price, store_id="bonpreu")
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
            store_id="bonpreu",
            quantity=quantity
        )
            print(f"   ✅ Added: {name} - {price}€ {quantity}")
            return "inserted"
        except Exception as e:
            print(f"   ❌ Failed to insert product: {str(e)}")
            return "error"

async def scrape_bonpreu_products():
    """Main scraping function for Bonpreu"""
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
            
            for idx, category_url in enumerate(categories, 1):
                print(f"\n[{idx}/{len(categories)}] Processing category: {category_url}")
                
                # Extract category name from URL
                category_name = category_url.split("/")[-1] if "/" in category_url else "unknown"
                
                # Get product links from this category
                product_urls = await get_product_links_from_category(page, category_url)
                
                if not product_urls:
                    print(f"   ⚠️ No products found in category")
                    continue
                
                # Process each product
                for i, product_url in enumerate(product_urls, 1):
                    print(f"   [{i}/{len(product_urls)}] Fetching product details...")
                    
                    product_data = await scrape_product_details(page, product_url)
                    if product_data:
                        result = await process_product(product_data, category_name)
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
            
            print("\n🎉 Bonpreu scraping completed!")
            print(f"   Total products added: {total_inserted}")
            print(f"   Total products updated: {total_updated}")
            print(f"   Total products skipped: {total_skipped}")
            print(f"   Total errors: {total_errors}")
            
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

    # Run the scraper
    asyncio.run(scrape_bonpreu_products())
