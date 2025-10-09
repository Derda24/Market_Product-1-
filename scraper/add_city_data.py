#!/usr/bin/env python3
"""
Add city data to existing products and create sample city-specific products
"""

import random
import json
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

def get_existing_products(limit=100):
    """Get existing products from database"""
    try:
        response = supabase.table("products").select("*").limit(limit).execute()
        if hasattr(response, "data") and response.data:
            print(f"✅ Found {len(response.data)} existing products")
            return response.data
        return []
    except Exception as e:
        print(f"❌ Error fetching products: {e}")
        return []

def create_city_variants():
    """
    Create city variants of existing products
    This simulates having products from different cities
    """
    cities = load_cities()
    if not cities:
        return
    
    # Get some existing products
    products = get_existing_products(50)
    if not products:
        print("❌ No existing products found")
        return
    
    print(f"🏙️ Creating city variants for {len(products)} products across {len(cities)} cities")
    
    # Select a few major cities for testing
    target_cities = ['Madrid', 'Valencia', 'Sevilla', 'Bilbao', 'Málaga']
    
    new_products = []
    
    for city in target_cities:
        print(f"📦 Creating variants for {city}...")
        
        # Take a subset of products for each city
        city_products = random.sample(products, min(20, len(products)))
        
        for product in city_products:
            # Create a variant with slight price differences
            price_variation = random.uniform(0.85, 1.15)  # ±15% price variation
            new_price = round(product['price'] * price_variation, 2)
            
            # Create new product name with city indicator
            new_name = f"{product['name']} ({city})"
            
            new_product = {
                'name': new_name,
                'price': new_price,
                'category': product['category'],
                'store_id': product['store_id'],
                'quantity': product.get('quantity'),
                'city': city,
                'image_url': product.get('image_url'),
                'nutriscore': product.get('nutriscore'),
                'nova_group': product.get('nova_group'),
                'energy_kcal': product.get('energy_kcal'),
                'sugars_100g': product.get('sugars_100g'),
                'salt_100g': product.get('salt_100g'),
                'saturated_fat_100g': product.get('saturated_fat_100g')
            }
            
            new_products.append(new_product)
    
    # Insert new products in batches
    batch_size = 10
    total_inserted = 0
    
    for i in range(0, len(new_products), batch_size):
        batch = new_products[i:i + batch_size]
        
        try:
            result = supabase.table("products").insert(batch).execute()
            if hasattr(result, "data") and result.data:
                total_inserted += len(result.data)
                print(f"✅ Inserted batch {i//batch_size + 1}: {len(result.data)} products")
            else:
                print(f"❌ Failed to insert batch {i//batch_size + 1}")
        except Exception as e:
            print(f"❌ Error inserting batch {i//batch_size + 1}: {e}")
    
    print(f"🎉 Created {total_inserted} city-specific products!")

def update_existing_products_with_cities():
    """
    Update existing products to have city information
    """
    print("🔄 Updating existing products with city data...")
    
    # Get products that don't have city set
    try:
        response = supabase.table("products").select("*").is_("city", "null").limit(100).execute()
        if not hasattr(response, "data") or not response.data:
            print("✅ All products already have city data")
            return
        
        products = response.data
        print(f"📦 Found {len(products)} products without city data")
        
        # Assign Barcelona to existing products (since they were originally scraped from Barcelona)
        for product in products:
            try:
                supabase.table("products").update({"city": "Barcelona"}).eq("id", product["id"]).execute()
                print(f"✅ Updated: {product['name']} -> Barcelona")
            except Exception as e:
                print(f"❌ Error updating {product['name']}: {e}")
        
        print("✅ Updated existing products with Barcelona")
        
    except Exception as e:
        print(f"❌ Error updating products: {e}")

def main():
    """Main function"""
    print("🚀 Starting city data addition process...")
    
    # Step 1: Update existing products with Barcelona
    update_existing_products_with_cities()
    
    # Step 2: Create city variants
    create_city_variants()
    
    print("🎉 City data addition complete!")

if __name__ == "__main__":
    main()
