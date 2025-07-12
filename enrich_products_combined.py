import requests
import time
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import json
from datetime import datetime

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USDA_API_KEY = os.getenv('USDA_API_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Translation (LibreTranslate, free, no API key) ---
def translate_to_english(text):
    url = "https://libretranslate.com/translate"
    payload = {
        "q": text,
        "source": "es",
        "target": "en",
        "format": "text"
    }
    response = requests.post(url, data=payload)
    return response.json()["translatedText"]

# --- OpenFoodFacts ---
def query_openfoodfacts(product_name_en):
    url = f'https://world.openfoodfacts.org/cgi/search.pl?search_terms={product_name_en}&search_simple=1&action=process&json=1'
    response = requests.get(url)
    data = response.json()
    if not data['products']:
        return {}
    product = data['products'][0]
    return {
        'nutriscore': product.get('nutriscore_grade'),
        'nova_group': product.get('nova_group'),
        'energy_kcal': product.get('nutriments', {}).get('energy-kcal_100g'),
        'sugars_100g': product.get('nutriments', {}).get('sugars_100g'),
        'salt_100g': product.get('nutriments', {}).get('salt_100g'),
        'saturated_fat_100g': product.get('nutriments', {}).get('saturated-fat_100g'),
    }

# --- USDA ---
def query_usda(product_name_en):
    search_url = f'https://api.nal.usda.gov/fdc/v1/foods/search'
    params = {
        'api_key': USDA_API_KEY,
        'query': product_name_en,
        'pageSize': 1
    }
    response = requests.get(search_url, params=params)
    data = response.json()
    if not data.get('foods'):
        return {}
    food = data['foods'][0]
    nutrients = {nutr['nutrientName']: nutr['value'] for nutr in food.get('foodNutrients', [])}
    return {
        'nutriscore': None,  # Not available in USDA
        'nova_group': None,  # Not available in USDA
        'energy_kcal': nutrients.get('Energy', None),
        'sugars_100g': nutrients.get('Sugars, total including NLEA', None),
        'salt_100g': nutrients.get('Sodium, Na', None),
        'saturated_fat_100g': nutrients.get('Fatty acids, total saturated', None),
    }

# --- Combine Results ---
def combine_data(off_data, usda_data):
    return {
        'nutriscore': off_data.get('nutriscore') or usda_data.get('nutriscore'),
        'nova_group': off_data.get('nova_group') or usda_data.get('nova_group'),
        'energy_kcal': off_data.get('energy_kcal') or usda_data.get('energy_kcal'),
        'sugars_100g': off_data.get('sugars_100g') or usda_data.get('sugars_100g'),
        'salt_100g': off_data.get('salt_100g') or usda_data.get('salt_100g'),
        'saturated_fat_100g': off_data.get('saturated_fat_100g') or usda_data.get('saturated_fat_100g'),
    }

# --- Main Enrichment Loop ---
def enrich_all_products():
    products = supabase.table('products').select('*').execute().data
    for product in products:
        product_id = product['id']
        product_name_es = product['name']
        print(f'🔎 Enriching: {product_name_es}')
        try:
            product_name_en = translate_to_english(product_name_es)
            off_data = query_openfoodfacts(product_name_en)
            usda_data = {}
            if not all(off_data.values()):
                usda_data = query_usda(product_name_en)
            combined = combine_data(off_data, usda_data)
            # Only update if we found at least one field
            if any(combined.values()):
                supabase.table('products').update(combined).eq('id', product_id).execute()
                print(f'✅ Updated {product_name_es} ({product_id})')
            else:
                print(f'❌ No nutrition data found for {product_name_es}')
        except Exception as e:
            print(f'⚠️ Error enriching {product_name_es}: {e}')
        time.sleep(1)  # Be nice to APIs

if __name__ == '__main__':
    enrich_all_products() 