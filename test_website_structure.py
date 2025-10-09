#!/usr/bin/env python3
"""
Test script to analyze website structures and find working selectors
"""

from playwright.sync_api import sync_playwright
import time

def test_website_structure():
    websites_to_test = [
        {
            'name': 'Carrefour',
            'url': 'https://www.carrefour.es/c/alimentacion',
            'selectors': ['.product-card', '[data-test="product-card"]', '[class*="product"]', '[class*="Product"]']
        },
        {
            'name': 'Consum', 
            'url': 'https://www.consum.es/alimentacion',
            'selectors': ['.product-card', '[class*="product"]', '[class*="Product"]', '[class*="item"]']
        },
        {
            'name': 'Eroski',
            'url': 'https://supermercado.eroski.es/en/c/comprar-alimentos/c1856',
            'selectors': ['.product-card', '[class*="product"]', '[class*="Product"]']
        }
    ]
    
    for site in websites_to_test:
        print(f"\n{'='*50}")
        print(f"Testing {site['name']}: {site['url']}")
        print(f"{'='*50}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                page.goto(site['url'], timeout=10000)
                time.sleep(3)
                
                print(f"Page loaded: {page.url}")
                print(f"Page title: {page.title()}")
                
                for selector in site['selectors']:
                    try:
                        elements = page.query_selector_all(selector)
                        print(f"  {selector}: {len(elements)} elements")
                        if len(elements) > 0:
                            first_text = elements[0].inner_text()[:50] if elements[0].inner_text() else "No text"
                            print(f"    Preview: {first_text}...")
                    except Exception as e:
                        print(f"  {selector}: Error - {str(e)[:100]}")
                
            except Exception as e:
                print(f"Failed to load {site['name']}: {e}")
            finally:
                browser.close()

if __name__ == "__main__":
    test_website_structure()



