#!/usr/bin/env python3
"""
Simple scraper runner without Unicode emojis to avoid Windows console issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_mercadona_cities():
    """Run Mercadona for multiple cities"""
    print("Running Mercadona for multiple cities...")
    try:
        from scraper.mercadona_city import scrape_multiple_cities_mercadona
        cities = ['Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Málaga', 'Bilbao', 'Zaragoza', 'Murcia', 'Palma']
        result = scrape_multiple_cities_mercadona(cities=cities, max_products_per_city=30)
        print(f"Mercadona multi-city completed: {result} products")
        return result
    except Exception as e:
        print(f"Error running Mercadona: {e}")
        return 0

def run_carrefour_cities():
    """Run Carrefour for multiple cities"""
    print("Running Carrefour for multiple cities...")
    try:
        from scraper.carrefour_city import scrape_multiple_cities_carrefour
        cities = ['Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Málaga', 'Bilbao', 'Zaragoza', 'Murcia', 'Palma']
        result = scrape_multiple_cities_carrefour(cities=cities, max_products_per_city=30)
        print(f"Carrefour multi-city completed: {result} products")
        return result
    except Exception as e:
        print(f"Error running Carrefour: {e}")
        return 0

def run_condisline():
    """Run Condisline scraper"""
    print("Running Condisline scraper...")
    try:
        from scraper.condisline import main
        result = main()
        print(f"Condisline completed: {result} products")
        return result
    except Exception as e:
        print(f"Error running Condisline: {e}")
        return 0

def check_database_status():
    """Check current database status"""
    print("Checking database status...")
    try:
        from utils.db import get_city_stats
        import json
        stats = get_city_stats()
        print("Current city statistics:")
        print(json.dumps(stats, indent=2))
        return stats
    except Exception as e:
        print(f"Error checking database: {e}")
        return {}

def main():
    """Main function"""
    print("Starting comprehensive scraping session...")
    
    # Check initial status
    initial_stats = check_database_status()
    
    # Run city-supporting markets
    mercadona_products = run_mercadona_cities()
    carrefour_products = run_carrefour_cities()
    
    # Run single-location markets
    condisline_products = run_condisline()
    
    # Check final status
    print("\nChecking final database status...")
    final_stats = check_database_status()
    
    # Calculate totals
    total_products = (mercadona_products or 0) + (carrefour_products or 0) + (condisline_products or 0)
    print(f"\nScraping session completed!")
    print(f"Total products processed: {total_products}")
    
    # Show changes
    if initial_stats and final_stats:
        print("\nChanges in product counts:")
        for city in set(initial_stats.keys()) | set(final_stats.keys()):
            initial = initial_stats.get(city, 0)
            final = final_stats.get(city, 0)
            change = final - initial
            if change != 0:
                print(f"  {city}: {initial} -> {final} ({change:+d})")

if __name__ == "__main__":
    main()
