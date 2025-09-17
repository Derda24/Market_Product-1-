#!/usr/bin/env python3
"""
Test script for multi-city multi-market scraping
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.comprehensive_multi_city_scraper import (
    scrape_comprehensive_multi_city,
    scrape_specific_city_markets,
    get_market_status
)

def test_market_status():
    """Test market status reporting"""
    print("🧪 Testing market status...")
    get_market_status()

def test_specific_city_markets():
    """Test scraping specific city with multiple markets"""
    print("\n🧪 Testing specific city scraping...")
    
    # Test with Barcelona and a few markets
    test_markets = ['carrefour', 'mercadona', 'lidl']
    scrape_specific_city_markets('Barcelona', test_markets, max_products=15)

def test_comprehensive_small():
    """Test comprehensive scraping with limited scope"""
    print("\n🧪 Testing comprehensive scraping (small scope)...")
    
    # Test with 2 cities and 3 markets
    test_cities = ['Madrid', 'Barcelona']
    test_markets = ['carrefour', 'mercadona', 'lidl']
    
    scrape_comprehensive_multi_city(
        cities=test_cities,
        markets=test_markets,
        max_products_per_city=10,
        max_products_per_market=15
    )

if __name__ == "__main__":
    print("🚀 Starting Multi-City Multi-Market Scraping Tests")
    print("=" * 60)
    
    # Run tests
    test_market_status()
    
    # Uncomment to run actual scraping tests:
    # test_specific_city_markets()
    # test_comprehensive_small()
    
    print("\n✅ Tests completed!")
