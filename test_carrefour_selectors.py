#!/usr/bin/env python3
"""
Test script to analyze Carrefour website structure and find correct selectors
"""

from playwright.sync_api import sync_playwright
import time

def test_carrefour_selectors():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            print('Testing Carrefour website...')
            page.goto('https://www.carrefour.es/c/alimentacion')
            time.sleep(5)
            
            # Check for different product selectors
            selectors = [
                '.product-card',
                '[data-test="product-card"]',
                '[class*="product"]',
                '[class*="item"]',
                '[class*="card"]',
                '.product-item',
                '.product-tile',
                '[data-testid*="product"]',
                '[class*="Product"]',
                '[class*="ProductCard"]',
                '[class*="productTile"]'
            ]
            
            print("\nTesting selectors:")
            for selector in selectors:
                try:
                    elements = page.query_selector_all(selector)
                    print(f'{selector}: {len(elements)} elements found')
                    if len(elements) > 0:
                        # Get text content of first element
                        first_element = elements[0]
                        text_content = first_element.inner_text()[:100] if first_element.inner_text() else "No text"
                        print(f"  First element preview: {text_content}...")
                except Exception as e:
                    print(f'{selector}: Error - {e}')
            
            # Take screenshot for analysis
            page.screenshot(path='carrefour_current.png')
            print('\nScreenshot saved as carrefour_current.png')
            
            # Check page title and URL
            print(f"\nPage title: {page.title()}")
            print(f"Current URL: {page.url}")
            
        except Exception as e:
            print(f'Error: {e}')
        finally:
            browser.close()

if __name__ == "__main__":
    test_carrefour_selectors()
