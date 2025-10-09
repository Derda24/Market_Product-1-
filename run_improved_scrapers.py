#!/usr/bin/env python3
"""
Run all improved and working scrapers to maximize product coverage
"""

import time
from datetime import datetime

def run_improved_scrapers():
    """Run all improved scrapers"""
    print("🚀 Starting comprehensive scraping with improved scrapers...")
    print("=" * 60)
    
    total_products = 0
    start_time = datetime.now()
    
    # Working scrapers from our previous session
    working_scrapers = [
        {
            'name': 'El Corte Inglés',
            'function': 'scraper.El_Corte_Inglés.scrape_elcorte',
            'description': 'Single location - high product count'
        },
        {
            'name': 'Condisline', 
            'function': 'scraper.condisline.main',
            'description': 'Single location - food products'
        },
        {
            'name': 'Bonarea',
            'function': 'scraper.bonarea.scrape_bonarea',
            'description': 'Single location - fresh products'
        },
        {
            'name': 'Alcampo',
            'function': 'scraper.alcampo.scrape_alcampo', 
            'description': 'Single location - with fallback method'
        },
        {
            'name': 'Aldi',
            'function': 'scraper.aldi.scrape_aldi',
            'description': 'Single location - discount store'
        }
    ]
    
    # Improved scrapers
    improved_scrapers = [
        {
            'name': 'Eroski (Improved)',
            'function': 'scraper.eroski_improved.scrape_eroski_improved',
            'description': 'Fixed URLs and selectors'
        }
    ]
    
    # City-supporting scrapers (these had issues but let's try them)
    city_scrapers = [
        {
            'name': 'Mercadona (Multi-city)',
            'function': 'scraper.mercadona_city.scrape_multiple_cities_mercadona',
            'description': 'Multi-city - working well'
        },
        {
            'name': 'Carrefour (Multi-city)', 
            'function': 'scraper.carrefour_city.scrape_multiple_cities_carrefour',
            'description': 'Multi-city - had selector issues'
        }
    ]
    
    all_scrapers = working_scrapers + improved_scrapers + city_scrapers
    
    print(f"📊 Total scrapers to run: {len(all_scrapers)}")
    print(f"🕐 Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {}
    
    for i, scraper in enumerate(all_scrapers, 1):
        print(f"\n{'='*50}")
        print(f"🏪 [{i}/{len(all_scrapers)}] Running {scraper['name']}")
        print(f"📝 {scraper['description']}")
        print(f"{'='*50}")
        
        try:
            # Import and run the scraper
            module_name, function_name = scraper['function'].rsplit('.', 1)
            module = __import__(module_name, fromlist=[function_name])
            scraper_function = getattr(module, function_name)
            
            # Run with appropriate parameters
            if 'multi_city' in scraper['name'].lower():
                if 'mercadona' in scraper['name'].lower():
                    cities = ['Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Málaga', 'Bilbao', 'Zaragoza', 'Murcia', 'Palma']
                    result = scraper_function(cities=cities, max_products_per_city=30)
                elif 'carrefour' in scraper['name'].lower():
                    cities = ['Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Málaga', 'Bilbao', 'Zaragoza', 'Murcia', 'Palma']
                    result = scraper_function(cities=cities, max_products_per_city=40)
                else:
                    result = scraper_function()
            else:
                result = scraper_function()
            
            results[scraper['name']] = result or 0
            total_products += results[scraper['name']]
            
            print(f"✅ {scraper['name']} completed: {results[scraper['name']]} products")
            
        except Exception as e:
            print(f"❌ {scraper['name']} failed: {str(e)[:100]}")
            results[scraper['name']] = 0
        
        # Delay between scrapers
        if i < len(all_scrapers):
            delay = 10  # 10 seconds between scrapers
            print(f"⏳ Waiting {delay}s before next scraper...")
            time.sleep(delay)
    
    # Final summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    print(f"\n{'='*60}")
    print("🎉 COMPREHENSIVE SCRAPING COMPLETED!")
    print(f"{'='*60}")
    print(f"🕐 Duration: {duration}")
    print(f"📊 Total products processed: {total_products}")
    print()
    
    print("📈 Results by scraper:")
    for name, count in results.items():
        status = "✅" if count > 0 else "❌"
        print(f"  {status} {name}: {count} products")
    
    print()
    print("🏆 Top performers:")
    sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
    for i, (name, count) in enumerate(sorted_results[:5], 1):
        if count > 0:
            print(f"  {i}. {name}: {count} products")
    
    return total_products, results

if __name__ == "__main__":
    run_improved_scrapers()
