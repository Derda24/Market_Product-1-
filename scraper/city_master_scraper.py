#!/usr/bin/env python3
"""
Master City Scraper
Coordinates scraping products for multiple Spanish cities across different stores
"""

import time
import random
import json
from datetime import datetime
from utils.db import supabase

def load_cities():
    """Load Spanish cities from JSON file"""
    try:
        with open('data/cities_es.json', 'r', encoding='utf-8') as f:
            cities = json.load(f)
        print(f"✅ Loaded {len(cities)} cities")
        return cities
    except Exception as e:
        print(f"❌ Error loading cities: {e}")
        return []

def run_city_scraper(scraper_name, cities, max_products_per_city=30):
    """
    Run a specific city scraper for multiple cities
    
    Args:
        scraper_name (str): Name of the scraper (mercadona_city, carrefour_city, etc.)
        cities (list): List of city names to scrape
        max_products_per_city (int): Maximum products per city
    """
    print(f"\n🚀 Starting {scraper_name} for {len(cities)} cities...")
    
    try:
        if scraper_name == "mercadona_city":
            from scraper.mercadona_city import scrape_multiple_cities_mercadona
            return scrape_multiple_cities_mercadona(cities, max_products_per_city)
        elif scraper_name == "carrefour_city":
            from scraper.carrefour_city import scrape_multiple_cities_carrefour
            return scrape_multiple_cities_carrefour(cities, max_products_per_city)
        else:
            print(f"❌ Unknown scraper: {scraper_name}")
            return 0
    except Exception as e:
        print(f"❌ Error running {scraper_name}: {e}")
        return 0

def get_city_stats():
    """Get statistics about products per city"""
    try:
        # Get product count by city
        response = supabase.table("products").select("city").execute()
        if not hasattr(response, "data") or not response.data:
            return {}
        
        city_counts = {}
        for product in response.data:
            city = product.get('city', 'Unknown')
            city_counts[city] = city_counts.get(city, 0) + 1
        
        return city_counts
    except Exception as e:
        print(f"❌ Error getting city stats: {e}")
        return {}

def scrape_all_cities(major_cities_only=True, max_products_per_city=30):
    """
    Scrape products for all major Spanish cities
    
    Args:
        major_cities_only (bool): If True, only scrape major cities
        max_products_per_city (int): Maximum products per city per store
    """
    print("🌍 Starting comprehensive city scraping...")
    
    # Load cities
    cities_data = load_cities()
    if not cities_data:
        print("❌ No cities loaded, aborting")
        return
    
    # Select cities to scrape
    if major_cities_only:
        # Major Spanish cities (population > 200k)
        target_cities = [city['name'] for city in cities_data if city['population'] > 200000]
        target_cities = target_cities[:10]  # Limit to top 10
    else:
        # All cities
        target_cities = [city['name'] for city in cities_data]
    
    print(f"🎯 Target cities: {', '.join(target_cities)}")
    
    # Available scrapers
    scrapers = [
        "mercadona_city",
        "carrefour_city"
        # Add more city scrapers here as they're created
    ]
    
    total_products = 0
    start_time = datetime.now()
    
    # Show initial stats
    print("\n📊 Initial city statistics:")
    initial_stats = get_city_stats()
    for city, count in sorted(initial_stats.items()):
        print(f"  {city}: {count} products")
    
    # Run each scraper for all cities
    for scraper in scrapers:
        print(f"\n{'='*60}")
        print(f"🏪 Running {scraper}")
        print(f"{'='*60}")
        
        scraper_products = run_city_scraper(scraper, target_cities, max_products_per_city)
        total_products += scraper_products
        
        print(f"✅ {scraper} completed: {scraper_products} products")
        
        # Delay between scrapers
        if scraper != scrapers[-1]:  # Don't delay after last scraper
            delay = random.uniform(30, 60)
            print(f"⏳ Waiting {delay:.1f}s before next scraper...")
            time.sleep(delay)
    
    # Show final stats
    print(f"\n{'='*60}")
    print("📊 Final city statistics:")
    final_stats = get_city_stats()
    for city, count in sorted(final_stats.items()):
        print(f"  {city}: {count} products")
    
    # Show summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    print(f"\n🎉 City scraping complete!")
    print(f"⏱️ Duration: {duration}")
    print(f"📦 Total products processed: {total_products}")
    print(f"🏙️ Cities processed: {len(target_cities)}")
    print(f"🏪 Scrapers used: {len(scrapers)}")

def scrape_specific_cities(cities, stores=None, max_products_per_city=30):
    """
    Scrape specific cities with specific stores
    
    Args:
        cities (list): List of city names to scrape
        stores (list): List of store scrapers to use
        max_products_per_city (int): Maximum products per city per store
    """
    if stores is None:
        stores = ["mercadona_city", "carrefour_city"]
    
    print(f"🎯 Scraping specific cities: {', '.join(cities)}")
    print(f"🏪 Using stores: {', '.join(stores)}")
    
    total_products = 0
    
    for store in stores:
        print(f"\n🏪 Running {store}...")
        store_products = run_city_scraper(store, cities, max_products_per_city)
        total_products += store_products
        print(f"✅ {store}: {store_products} products")
        
        # Delay between stores
        if store != stores[-1]:
            delay = random.uniform(20, 40)
            print(f"⏳ Waiting {delay:.1f}s...")
            time.sleep(delay)
    
    print(f"\n🎉 Specific city scraping complete! Total: {total_products} products")

if __name__ == "__main__":
    # Example usage:
    
    # Option 1: Scrape all major cities
    # scrape_all_cities(major_cities_only=True, max_products_per_city=25)
    
    # Option 2: Scrape specific cities
    test_cities = ['Madrid', 'Barcelona', 'Valencia', 'Sevilla']
    scrape_specific_cities(cities=test_cities, max_products_per_city=20)
