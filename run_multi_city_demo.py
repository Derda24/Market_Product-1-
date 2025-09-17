#!/usr/bin/env python3
"""
Demo script for multi-city multi-market scraping
Shows how to scrape from different markets across different cities
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.comprehensive_multi_city_scraper import (
    scrape_comprehensive_multi_city,
    scrape_specific_city_markets,
    get_market_status,
    MARKET_CONFIGS
)

def demo_market_status():
    """Show available markets and their capabilities"""
    print("🏪 Available Markets and Their Capabilities")
    print("=" * 60)
    get_market_status()

def demo_city_supporting_markets():
    """Demo scraping city-supporting markets"""
    print("\n🏙️ Demo: City-Supporting Markets")
    print("=" * 50)
    
    # Test with 3 major cities and 2 city-supporting markets
    cities = ['Madrid', 'Barcelona', 'Valencia']
    city_markets = ['carrefour', 'mercadona']
    
    print(f"🎯 Cities: {', '.join(cities)}")
    print(f"🏪 Markets: {', '.join(city_markets)}")
    
    for market in city_markets:
        print(f"\n🏪 Running {market.upper()} for all cities...")
        try:
            from scraper.comprehensive_multi_city_scraper import run_market_scraper
            products = run_market_scraper(market, cities, max_products=10)
            print(f"✅ {market}: {products} products processed")
        except Exception as e:
            print(f"❌ Error with {market}: {e}")

def demo_single_location_markets():
    """Demo scraping single-location markets"""
    print("\n🏪 Demo: Single-Location Markets")
    print("=" * 50)
    
    # Test with 2 single-location markets
    single_markets = ['lidl', 'dia']
    
    print(f"🏪 Markets: {', '.join(single_markets)}")
    
    for market in single_markets:
        print(f"\n🏪 Running {market.upper()} (single location)...")
        try:
            from scraper.comprehensive_multi_city_scraper import run_market_scraper
            products = run_market_scraper(market, None, max_products=15)
            print(f"✅ {market}: {products} products processed")
        except Exception as e:
            print(f"❌ Error with {market}: {e}")

def demo_comprehensive_scraping():
    """Demo comprehensive multi-city, multi-market scraping"""
    print("\n🚀 Demo: Comprehensive Multi-City Multi-Market Scraping")
    print("=" * 60)
    
    # Small scale demo
    cities = ['Madrid', 'Barcelona']
    markets = ['carrefour', 'mercadona', 'lidl', 'dia']
    
    print(f"🏙️ Cities: {', '.join(cities)}")
    print(f"🏪 Markets: {', '.join(markets)}")
    
    scrape_comprehensive_multi_city(
        cities=cities,
        markets=markets,
        max_products_per_city=10,
        max_products_per_market=15
    )

def demo_specific_city():
    """Demo scraping specific city with multiple markets"""
    print("\n🎯 Demo: Specific City Multi-Market Scraping")
    print("=" * 50)
    
    city = 'Barcelona'
    markets = ['carrefour', 'mercadona', 'lidl']
    
    print(f"🏙️ City: {city}")
    print(f"🏪 Markets: {', '.join(markets)}")
    
    scrape_specific_city_markets(city, markets, max_products=10)

def main():
    """Main demo function"""
    print("🌍 Multi-City Multi-Market Scraping Demo")
    print("=" * 60)
    print("This demo shows how to scrape from different markets across different cities")
    print()
    
    # Show market capabilities
    demo_market_status()
    
    # Ask user what they want to demo
    print("\nDemo Options:")
    print("1. City-supporting markets only")
    print("2. Single-location markets only") 
    print("3. Comprehensive scraping (mixed)")
    print("4. Specific city with multiple markets")
    print("5. All demos")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == "1":
        demo_city_supporting_markets()
    elif choice == "2":
        demo_single_location_markets()
    elif choice == "3":
        demo_comprehensive_scraping()
    elif choice == "4":
        demo_specific_city()
    elif choice == "5":
        demo_city_supporting_markets()
        demo_single_location_markets()
        demo_comprehensive_scraping()
        demo_specific_city()
    else:
        print("Invalid choice. Running market status only.")
    
    print("\n✅ Demo completed!")

if __name__ == "__main__":
    main()
