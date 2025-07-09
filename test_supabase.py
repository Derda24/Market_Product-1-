#!/usr/bin/env python3
"""
Test script to verify Supabase connection and database functions
"""

from utils.db import insert_product, get_product_by_name_and_store, update_product_price, supabase
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_supabase_connection():
    """Test basic Supabase connection"""
    print("🔍 Testing Supabase connection...")
    
    try:
        # Test basic connection
        result = supabase.table("products").select("count").limit(1).execute()
        print("✅ Supabase connection successful!")
        return True
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        print("Please check your .env file contains valid SUPABASE_URL and SUPABASE_KEY")
        return False

def test_insert_product():
    """Test inserting a product"""
    print("\n🧪 Testing product insertion...")
    
    try:
        # Insert a test product
        result = insert_product(
            name="TEST PRODUCT - DELETE ME",
            price=9.99,
            category="test",
            store_id="test_store",
            quantity="1 unit"
        )
        print("✅ Product insertion successful!")
        return True
    except Exception as e:
        print(f"❌ Product insertion failed: {e}")
        return False

def test_get_product():
    """Test getting a product"""
    print("\n🔍 Testing product retrieval...")
    
    try:
        # Get the test product we just inserted
        product = get_product_by_name_and_store("TEST PRODUCT - DELETE ME", "test_store")
        if product:
            print(f"✅ Product found: {product['name']} - {product['price']}€")
            return product
        else:
            print("❌ Product not found")
            return None
    except Exception as e:
        print(f"❌ Product retrieval failed: {e}")
        return None

def test_update_product(product):
    """Test updating a product"""
    if not product:
        print("❌ Cannot test update - no product found")
        return False
    
    print("\n🔄 Testing product update...")
    
    try:
        # Update the price
        new_price = 12.99
        update_product_price(product['id'], new_price)
        print(f"✅ Product price updated from {product['price']}€ to {new_price}€")
        return True
    except Exception as e:
        print(f"❌ Product update failed: {e}")
        return False

def cleanup_test_product():
    """Clean up the test product"""
    print("\n🧹 Cleaning up test product...")
    
    try:
        # Delete the test product
        result = supabase.table("products").delete().eq("name", "TEST PRODUCT - DELETE ME").execute()
        print("✅ Test product cleaned up!")
        return True
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Supabase tests...\n")
    
    # Test 1: Connection
    if not test_supabase_connection():
        return
    
    # Test 2: Insert
    if not test_insert_product():
        return
    
    # Test 3: Get
    product = test_get_product()
    
    # Test 4: Update
    if product:
        test_update_product(product)
    
    # Test 5: Cleanup
    cleanup_test_product()
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    main() 