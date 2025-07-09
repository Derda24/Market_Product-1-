#!/usr/bin/env python3
"""
Test script to debug Bonarea scraper product detection
"""

from utils.db import get_product_by_name_and_store, supabase
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_product_search():
    """Test searching for products in the database"""
    print("🔍 Testing product search in database...")
    
    # Test some sample product names that might exist
    test_products = [
        "Llet pasteuritzada sencera",
        "Iogurt natural 4 u. de 125 g",
        "Sangria Issmut",
        "Melmelada de tomàquet",
        "Formatge Roquefort cunya"
    ]
    
    print(f"\n📊 Checking {len(test_products)} sample products:")
    
    for product_name in test_products:
        result = get_product_by_name_and_store(product_name, "bonarea")
        if result:
            print(f"✅ Found: {product_name} (ID: {result['id']}, Price: {result['price']}€)")
        else:
            print(f"❌ Not found: {product_name}")
    
    # Check total count of Bonarea products
    try:
        result = supabase.table("products").select("count", count="exact").eq("store_id", "bonarea").execute()
        total_count = result.count if hasattr(result, 'count') else len(result.data)
        print(f"\n📈 Total Bonarea products in database: {total_count}")
        
        # Show some sample products
        if total_count > 0:
            sample_products = supabase.table("products").select("name, price, created_at").eq("store_id", "bonarea").limit(5).execute()
            print(f"\n📋 Sample Bonarea products:")
            for product in sample_products.data:
                print(f"  - {product['name']} ({product['price']}€)")
                
    except Exception as e:
        print(f"❌ Error checking database: {e}")

def test_get_product_function():
    """Test the get_product_by_name_and_store function specifically"""
    print("\n🧪 Testing get_product_by_name_and_store function...")
    
    # Test with a product that should exist
    test_name = "Llet pasteuritzada sencera (Mantenir refrigerat)"
    print(f"🔍 Searching for: '{test_name}'")
    
    result = get_product_by_name_and_store(test_name, "bonarea")
    if result:
        print(f"✅ Function returned: {result}")
    else:
        print(f"❌ Function returned None")
        
        # Let's check if there are similar products
        try:
            similar_products = supabase.table("products").select("name").eq("store_id", "bonarea").ilike("name", "%llet%").execute()
            print(f"🔍 Found {len(similar_products.data)} products with 'llet' in name:")
            for product in similar_products.data:
                print(f"  - {product['name']}")
        except Exception as e:
            print(f"❌ Error searching similar products: {e}")

if __name__ == "__main__":
    test_product_search()
    test_get_product_function() 