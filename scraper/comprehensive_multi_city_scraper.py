#!/usr/bin/env python3
"""
Comprehensive Multi-City Multi-Market Scraper
Scrapes products from all available markets across different Spanish cities
"""

import time
import random
import json
from datetime import datetime
from typing import List, Dict, Optional

# Import all available scrapers
from utils.db import get_city_stats
from utils.logger import log_debug_message as log

def load_cities():
    """Load city data from JSON file"""
    try:
        with open('data/cities_es.json', 'r', encoding='utf-8') as f:
            cities = json.load(f)
        return cities
    except Exception as e:
        print(f"❌ Error loading cities: {e}")
        return []

# Market configurations with their capabilities
MARKET_CONFIGS = {
    'carrefour': {
        'city_support': True,
        'scraper_module': 'scraper.carrefour_city',
        'scraper_function': 'scrape_multiple_cities_carrefour',
        'categories': ['alimentacion', 'bebidas', 'congelados', 'frescos'],
        'max_products_per_city': 40,
        'delay_between_cities': (15, 25)
    },
    'mercadona': {
        'city_support': True,
        'scraper_module': 'scraper.mercadona_city', 
        'scraper_function': 'scrape_multiple_cities_mercadona',
        'categories': ['alimentacion', 'bebidas', 'congelados', 'frescos'],
        'max_products_per_city': 30,
        'delay_between_cities': (10, 20)
    },
    'elcorte': {
        'city_support': False,  # Single location scraper
        'scraper_module': 'scraper.El_Corte_Inglés',
        'scraper_function': 'scrape_elcorte',
        'categories': ['aceites-y-vinagres', 'arroz-legumbres-y-pasta', 'azucar-cacao-y-edulcorantes'],
        'max_products': 100,
        'delay_between_runs': (30, 45)
    },
    'lidl': {
        'city_support': False,
        'scraper_module': 'scraper.lidl',
        'scraper_function': 'scrape_lidl',
        'categories': ['alimentacion', 'bebidas'],
        'max_products': 80,
        'delay_between_runs': (25, 40)
    },
    'dia': {
        'city_support': False,
        'scraper_module': 'scraper.dia',
        'scraper_function': 'scrape_dia',
        'categories': ['alimentacion', 'bebidas'],
        'max_products': 60,
        'delay_between_runs': (20, 35)
    },
    'consum': {
        'city_support': False,
        'scraper_module': 'scraper.consum',
        'scraper_function': 'scrape_consum',
        'categories': ['alimentacion', 'bebidas'],
        'max_products': 70,
        'delay_between_runs': (25, 40)
    },
    'condisline': {
        'city_support': False,
        'scraper_module': 'scraper.condisline',
        'scraper_function': 'main',
        'categories': ['aceites-y-vinagres', 'arroz-legumbres-y-pasta', 'conservas'],
        'max_products': 50,
        'delay_between_runs': (20, 35)
    },
    'bonpreu': {
        'city_support': False,
        'scraper_module': 'scraper.bonpreu',
        'scraper_function': 'scrape_bonpreu',
        'categories': ['alimentacion', 'bebidas'],
        'max_products': 60,
        'delay_between_runs': (20, 35)
    },
    'alcampo': {
        'city_support': False,
        'scraper_module': 'scraper.alcampo',
        'scraper_function': 'scrape_alcampo',
        'categories': ['alimentacion', 'bebidas'],
        'max_products': 70,
        'delay_between_runs': (25, 40)
    },
    'bonarea': {
        'city_support': False,
        'scraper_module': 'scraper.bonarea',
        'scraper_function': 'scrape_bonarea',
        'categories': ['alimentacion', 'bebidas'],
        'max_products': 50,
        'delay_between_runs': (20, 35)
    },
    'eroski': {
        'city_support': False,
        'scraper_module': 'scraper.eroski',
        'scraper_function': 'scrape_eroski',
        'categories': ['alimentacion', 'bebidas'],
        'max_products': 60,
        'delay_between_runs': (20, 35)
    },
    'caprabo': {
        'city_support': False,
        'scraper_module': 'scraper.caprabo',
        'scraper_function': 'scrape_caprabo',
        'categories': ['alimentacion', 'bebidas'],
        'max_products': 50,
        'delay_between_runs': (20, 35)
    },
    'aldi': {
        'city_support': False,
        'scraper_module': 'scraper.aldi',
        'scraper_function': 'scrape_aldi',
        'categories': ['alimentacion', 'bebidas'],
        'max_products': 60,
        'delay_between_runs': (20, 35)
    }
}

def run_market_scraper(market_name: str, cities: Optional[List[str]] = None, max_products: Optional[int] = None):
    """
    Run a specific market scraper
    
    Args:
        market_name (str): Name of the market to scrape
        cities (list): List of cities (only for city-supporting markets)
        max_products (int): Maximum products to scrape
    """
    config = MARKET_CONFIGS.get(market_name)
    if not config:
        print(f"❌ Unknown market: {market_name}")
        return 0
    
    print(f"\n🏪 Starting {market_name} scraper...")
    
    try:
        # Import the scraper module
        module = __import__(config['scraper_module'], fromlist=[config['scraper_function']])
        scraper_function = getattr(module, config['scraper_function'])
        
        if config['city_support'] and cities:
            # Multi-city scraper
            max_per_city = max_products or config['max_products_per_city']
            return scraper_function(cities=cities, max_products_per_city=max_per_city)
        else:
            # Single location scraper - check if it accepts parameters
            import inspect
            sig = inspect.signature(scraper_function)
            if 'max_products' in sig.parameters:
                max_prod = max_products or config['max_products']
                return scraper_function(max_products=max_prod)
            else:
                # No parameters accepted, call without any
                return scraper_function()
            
    except Exception as e:
        print(f"❌ Error running {market_name}: {e}")
        return 0

def scrape_comprehensive_multi_city(
    cities: Optional[List[str]] = None,
    markets: Optional[List[str]] = None,
    max_products_per_city: int = 25,
    max_products_per_market: int = 50
):
    """
    Comprehensive multi-city, multi-market scraping
    
    Args:
        cities (list): List of cities to scrape (None = all major cities)
        markets (list): List of markets to scrape (None = all available)
        max_products_per_city (int): Max products per city for city-supporting markets
        max_products_per_market (int): Max products for single-location markets
    """
    print("🚀 Starting Comprehensive Multi-City Multi-Market Scraping")
    print("=" * 60)
    
    # Load cities
    cities_data = load_cities()
    if not cities_data:
        print("❌ No cities loaded, aborting")
        return
    
    # Determine cities to scrape
    if cities is None:
        # Major cities (population > 200k)
        major_cities = [city['name'] for city in cities_data if city['population'] > 200000]
        target_cities = major_cities[:8]  # Top 8 major cities
    else:
        target_cities = cities
    
    # Determine markets to scrape
    if markets is None:
        available_markets = list(MARKET_CONFIGS.keys())
    else:
        available_markets = [m for m in markets if m in MARKET_CONFIGS]
    
    print(f"🏙️ Target cities: {', '.join(target_cities)}")
    print(f"🏪 Available markets: {', '.join(available_markets)}")
    
    # Show initial stats
    print("\n📊 Initial city statistics:")
    initial_stats = get_city_stats()
    if initial_stats:
        # Filter out None keys and sort
        filtered_stats = {k: v for k, v in initial_stats.items() if k is not None}
        for city, count in sorted(filtered_stats.items()):
            print(f"  {city}: {count} products")
    else:
        print("  No city statistics available")
    
    total_products = 0
    start_time = datetime.now()
    
    # Separate city-supporting and single-location markets
    city_markets = [m for m in available_markets if MARKET_CONFIGS[m]['city_support']]
    single_markets = [m for m in available_markets if not MARKET_CONFIGS[m]['city_support']]
    
    print(f"\n🏙️ City-supporting markets: {', '.join(city_markets)}")
    print(f"🏪 Single-location markets: {', '.join(single_markets)}")
    
    # Run city-supporting markets
    for market in city_markets:
        print(f"\n{'='*50}")
        print(f"🏪 Running {market.upper()} for all cities...")
        
        products = run_market_scraper(market, target_cities, max_products_per_city)
        total_products += products or 0
        
        print(f"✅ {market}: {products} total products")
        
        # Delay between city-supporting markets
        if market != city_markets[-1]:
            delay = random.uniform(30, 60)
            print(f"⏳ Waiting {delay:.1f}s before next city-supporting market...")
            time.sleep(delay)
    
    # Run single-location markets
    for market in single_markets:
        print(f"\n{'='*50}")
        print(f"🏪 Running {market.upper()} (single location)...")
        
        products = run_market_scraper(market, None, max_products_per_market)
        total_products += products or 0
        
        print(f"✅ {market}: {products} products")
        
        # Delay between single-location markets
        if market != single_markets[-1]:
            config = MARKET_CONFIGS[market]
            delay_min, delay_max = config['delay_between_runs']
            delay = random.uniform(delay_min, delay_max)
            print(f"⏳ Waiting {delay:.1f}s before next market...")
            time.sleep(delay)
    
    # Final statistics
    end_time = datetime.now()
    duration = end_time - start_time
    
    print(f"\n{'='*60}")
    print(f"🎉 COMPREHENSIVE SCRAPING COMPLETE!")
    print(f"⏱️ Duration: {duration}")
    print(f"📊 Total products processed: {total_products}")
    print(f"🏙️ Cities scraped: {len(target_cities)}")
    print(f"🏪 Markets scraped: {len(available_markets)}")
    
    # Show final city stats
    print(f"\n📊 Final city statistics:")
    final_stats = get_city_stats()
    if final_stats:
        # Filter out None keys and sort
        filtered_final_stats = {k: v for k, v in final_stats.items() if k is not None}
        for city, count in sorted(filtered_final_stats.items()):
            print(f"  {city}: {count} products")
    else:
        print("  No city statistics available")

def scrape_specific_city_markets(city: str, markets: List[str], max_products: int = 30):
    """
    Scrape specific markets for a single city
    
    Args:
        city (str): City name to scrape
        markets (list): List of market names to scrape
        max_products (int): Maximum products per market
    """
    print(f"🎯 Scraping {city} with markets: {', '.join(markets)}")
    
    city_markets = [m for m in markets if MARKET_CONFIGS[m]['city_support']]
    single_markets = [m for m in markets if not MARKET_CONFIGS[m]['city_support']]
    
    total_products = 0
    
    # Run city-supporting markets for this specific city
    for market in city_markets:
        print(f"\n🏪 Running {market} for {city}...")
        products = run_market_scraper(market, [city], max_products)
        total_products += products or 0
        print(f"✅ {market} for {city}: {products} products")
        
        if market != city_markets[-1]:
            time.sleep(random.uniform(10, 20))
    
    # Run single-location markets (they don't support cities)
    for market in single_markets:
        print(f"\n🏪 Running {market} (single location)...")
        products = run_market_scraper(market, None, max_products)
        total_products += products or 0
        print(f"✅ {market}: {products} products")
        
        if market != single_markets[-1]:
            time.sleep(random.uniform(15, 25))
    
    print(f"\n🎉 {city} scraping complete! Total: {total_products} products")

def get_market_status():
    """Get status of all available markets"""
    print("📊 Market Status Report")
    print("=" * 50)
    
    for market, config in MARKET_CONFIGS.items():
        city_support = "✅ Yes" if config['city_support'] else "❌ No"
        categories = len(config['categories'])
        max_products = config.get('max_products_per_city', config.get('max_products', 'N/A'))
        
        print(f"🏪 {market.upper()}")
        print(f"   City Support: {city_support}")
        print(f"   Categories: {categories}")
        print(f"   Max Products: {max_products}")
        print()

if __name__ == "__main__":
    # Example usage options:
    
    # Option 1: Comprehensive scraping (all markets, all major cities)
    # scrape_comprehensive_multi_city()
    
    # Option 2: Specific cities and markets
    # scrape_comprehensive_multi_city(
    #     cities=['Madrid', 'Barcelona', 'Valencia'],
    #     markets=['carrefour', 'mercadona', 'lidl', 'dia']
    # )
    
    # Option 3: Single city with multiple markets
    # scrape_specific_city_markets('Barcelona', ['carrefour', 'mercadona', 'lidl'])
    
    # Option 4: Show market status
    get_market_status()
