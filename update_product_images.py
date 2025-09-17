#!/usr/bin/env python3
"""
Enhanced Product Image Updater
Fetches product images from multiple sources and updates Supabase database
"""

import requests
import os
import sys
import time
import logging
import json
from supabase import create_client, Client
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import re
from urllib.parse import quote_plus

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('image_update.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ProductImageUpdater:
    def __init__(self):
        """Initialize the updater with Supabase connection and API keys"""
        load_dotenv()
        
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment variables")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        logger.info("Supabase connection initialized")
        
        # API Keys for different image sources
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.google_cse_id = os.getenv('GOOGLE_CSE_ID')
        self.bing_api_key = os.getenv('BING_API_KEY')
        
        # Open Food Facts API base URL
        self.openfoodfacts_api = "https://world.openfoodfacts.org/api/v0/product/"
    
    def clean_product_name(self, name: str) -> str:
        """Clean product name for better search results"""
        # Remove common store prefixes and suffixes
        name = re.sub(r'\b(El Corte Inglés|Carrefour|Dia|Lidl|Mercadona|Alcampo|BonÀrea|Bonpreu|Condis|Eroski)\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\b(Classic|Extra|Premium|Selection|Al Punto|Nuestra Alacena|Marca Blanca|Hacendado|Deliplus|Basic|Natur)\b', '', name, flags=re.IGNORECASE)
        
        # Remove quantity information but keep important product info
        name = re.sub(r'\d+[.,]\d+\s*(kg|g|l|ml|cl|pack|units?|x)\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\(\d+\s*(kg|g|l|ml|cl|pack|units?|x)\)', '', name, flags=re.IGNORECASE)
        
        # Remove common packaging terms but keep important ones
        name = re.sub(r'\b(botella|bolsa|caja|sobre|bandeja|frasco|lata|brik|pack|envase)\b', '', name, flags=re.IGNORECASE)
        
        # Remove price information
        name = re.sub(r'\d+[.,]\d+\s*€', '', name)
        name = re.sub(r'1 KILO A \d+[.,]\d+\s*€', '', name, flags=re.IGNORECASE)
        name = re.sub(r'1 LITRO A \d+[.,]\d+\s*€', '', name, flags=re.IGNORECASE)
        
        # Keep important brand names and product types
        # Don't remove well-known brands that help with search
        important_brands = ['NESCAFÉ', 'DANONE', 'PASCUAL', 'ASTURIANA', 'KAIKU', 'BOMILK', 'LACTURALE', 
                          'PULEVA', 'BIZKAIA ESNEA', 'EUSKAL HERRIA', 'YOSOY', 'ALPRO', 'VERITAS', 
                          'EROSKI BIO', 'ECOCESTA', 'ISABEL', 'CUCA', 'PESCANOVA', 'BONDUELLE', 
                          'SOLIS', 'ORLANDO', 'CAL VALLS', 'LUENGO', 'BRILLANTE', 'SOS', 'LA FALLERA',
                          'FORTALEZA', 'BAQUÉ', 'BONKA', 'DOLCE GUSTO', 'L\'OR', 'DEPOSTRE', 'DHUL',
                          'ROYAL', 'BARNHOUSE', 'GERBLÉ', 'MENÉNDEZ', 'SAIZAR', 'GAILLA', 'LUIS THATE',
                          'EZKUR TXERRI', 'ZAPIAIN', 'BEREZIARTUA', 'PETRITEGI', 'ISASTEGI', 'ZELAIA',
                          'BEGIRISTAIN', 'SEGURA VIUDAS', 'JUVE Y CAMPS', 'CODORNÍU', 'FREIXENET',
                          'VALL D`LLUNA', 'JAUME SERRA', 'BACH', 'ALMA ATLANTICA', 'MIONETTO',
                          'LADRÓN DE MANZANAS', 'MUMM', 'EL GAITERO']
        
        # Clean up extra spaces and punctuation
        name = re.sub(r'\s+', ' ', name)
        name = name.strip()
        
        # If the cleaned name is too short, try to keep some brand info
        if len(name.strip()) < 3:
            # Try to extract brand name from original
            for brand in important_brands:
                if brand.lower() in name.lower():
                    return brand
        
        return name
    
    def search_openfoodfacts(self, product_name: str) -> Optional[str]:
        """Search Open Food Facts for product image"""
        try:
            # Clean the product name
            clean_name = self.clean_product_name(product_name)
            
            # Search API
            search_url = f"https://world.openfoodfacts.org/cgi/search.pl"
            params = {
                'search_terms': clean_name,
                'search_simple': 1,
                'action': 'process',
                'json': 1,
                'page_size': 5  # Get top 5 results
            }
            
            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('products') and len(data['products']) > 0:
                # Get the first product with an image
                for product in data['products']:
                    if product.get('image_front_url'):
                        logger.info(f"Found Open Food Facts image for: {product_name}")
                        return product['image_front_url']
                    elif product.get('image_url'):
                        logger.info(f"Found Open Food Facts image for: {product_name}")
                        return product['image_url']
            
            logger.warning(f"No Open Food Facts image found for: {product_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error searching Open Food Facts for {product_name}: {e}")
            return None
    
    def search_google_images(self, product_name: str) -> Optional[str]:
        """Search Google Custom Search for product images"""
        if not self.google_api_key or not self.google_cse_id:
            logger.warning("Google API key or CSE ID not configured")
            return None
            
        try:
            clean_name = self.clean_product_name(product_name)
            
            # Add "supermercado" or "comida" to improve results
            search_query = f"{clean_name} supermercado producto"
            
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.google_api_key,
                'cx': self.google_cse_id,
                'q': search_query,
                'searchType': 'image',
                'num': 10,  # Increased from 5 to 10
                'imgSize': 'large',  # Changed from 'medium' to 'large'
                'imgType': 'photo',
                'safe': 'active',
                'rights': 'cc_publicdomain|cc_attribute|cc_sharealike|cc_noncommercial|cc_nonderived'  # Better quality images
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'items' in data and len(data['items']) > 0:
                # Get the first image with better quality check
                for item in data['items']:
                    image_url = item['link']
                    # Check if image has reasonable dimensions
                    if 'image' in item and 'width' in item['image'] and 'height' in item['image']:
                        width = int(item['image']['width'])
                        height = int(item['image']['height'])
                        # Prefer images with good aspect ratio and size
                        if width >= 300 and height >= 300 and width/height < 3 and height/width < 3:
                            logger.info(f"Found high-quality Google image for: {product_name}")
                            return image_url
                
                # Fallback to first image if no quality check passed
                image_url = data['items'][0]['link']
                logger.info(f"Found Google image for: {product_name}")
                return image_url
            
            logger.warning(f"No Google image found for: {product_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error searching Google for {product_name}: {e}")
            return None
    
    def search_bing_images(self, product_name: str) -> Optional[str]:
        """Search Bing Image Search for product images"""
        if not self.bing_api_key:
            logger.warning("Bing API key not configured")
            return None
            
        try:
            clean_name = self.clean_product_name(product_name)
            
            # Add "supermercado" to improve results
            search_query = f"{clean_name} supermercado"
            
            url = "https://api.bing.microsoft.com/v7.0/images/search"
            headers = {
                'Ocp-Apim-Subscription-Key': self.bing_api_key
            }
            params = {
                'q': search_query,
                'count': 10,  # Increased from 5 to 10
                'imageType': 'Photo',
                'safeSearch': 'Moderate',
                'maxFileSize': 1048576,  # 1MB minimum
                'minFileSize': 10000,    # 10KB minimum
                'aspect': 'Square',       # Prefer square images
                'size': 'Large'           # Prefer large images
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'value' in data and len(data['value']) > 0:
                # Get the first image with quality check
                for item in data['value']:
                    image_url = item['contentUrl']
                    # Check if image has reasonable dimensions
                    if 'width' in item and 'height' in item:
                        width = int(item['width'])
                        height = int(item['height'])
                        # Prefer images with good aspect ratio and size
                        if width >= 300 and height >= 300 and width/height < 3 and height/width < 3:
                            logger.info(f"Found high-quality Bing image for: {product_name}")
                            return image_url
                
                # Fallback to first image if no quality check passed
                image_url = data['value'][0]['contentUrl']
                logger.info(f"Found Bing image for: {product_name}")
                return image_url
            
            logger.warning(f"No Bing image found for: {product_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error searching Bing for {product_name}: {e}")
            return None
    
    def search_unsplash(self, product_name: str) -> Optional[str]:
        """Search Unsplash for generic food/product images as fallback"""
        try:
            clean_name = self.clean_product_name(product_name)
            
            # Extract main food category from product name
            food_keywords = ['pan', 'leche', 'queso', 'carne', 'pescado', 'fruta', 'verdura', 
                           'arroz', 'pasta', 'aceite', 'vinagre', 'azúcar', 'café', 'té',
                           'yogur', 'mantequilla', 'huevos', 'jamón', 'salchichas', 'atún']
            
            search_term = clean_name
            for keyword in food_keywords:
                if keyword.lower() in clean_name.lower():
                    search_term = keyword
                    break
            
            url = f"https://api.unsplash.com/search/photos"
            headers = {
                'Authorization': f'Client-ID {os.getenv("UNSPLASH_ACCESS_KEY", "")}'
            }
            params = {
                'query': f"{search_term} food",
                'per_page': 1,
                'orientation': 'landscape'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'results' in data and len(data['results']) > 0:
                image_url = data['results'][0]['urls']['regular']
                logger.info(f"Found Unsplash fallback image for: {product_name}")
                return image_url
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching Unsplash for {product_name}: {e}")
            return None
    
    def search_ecommerce_images(self, product_name: str) -> Optional[str]:
        """Search for product images on e-commerce sites"""
        try:
            clean_name = self.clean_product_name(product_name)
            
            # Try different e-commerce search queries
            search_queries = [
                f"{clean_name} producto supermercado",
                f"{clean_name} marca oficial",
                f"{clean_name} imagen producto",
                clean_name  # Just the product name
            ]
            
            for query in search_queries:
                # Try Google Custom Search with e-commerce focus
                if self.google_api_key and self.google_cse_id:
                    url = "https://www.googleapis.com/customsearch/v1"
                    params = {
                        'key': self.google_api_key,
                        'cx': self.google_cse_id,
                        'q': query,
                        'searchType': 'image',
                        'num': 5,
                        'imgSize': 'large',
                        'imgType': 'photo',
                        'safe': 'active',
                        'siteSearch': 'amazon.es|mercadona.es|carrefour.es|eroski.es',  # Focus on e-commerce sites
                        'siteSearchFilter': 'i'  # Include only these sites
                    }
                    
                    response = requests.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    if 'items' in data and len(data['items']) > 0:
                        for item in data['items']:
                            image_url = item['link']
                            # Check if image has reasonable dimensions
                            if 'image' in item and 'width' in item['image'] and 'height' in item['image']:
                                width = int(item['image']['width'])
                                height = int(item['image']['height'])
                                # Prefer images with good aspect ratio and size
                                if width >= 400 and height >= 400 and width/height < 2 and height/width < 2:
                                    logger.info(f"Found high-quality e-commerce image for: {product_name}")
                                    return image_url
                        
                        # Fallback to first image
                        image_url = data['items'][0]['link']
                        logger.info(f"Found e-commerce image for: {product_name}")
                        return image_url
                
                time.sleep(0.5)  # Small delay between queries
            
            logger.warning(f"No e-commerce image found for: {product_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error searching e-commerce for {product_name}: {e}")
            return None
    
    def get_generic_food_image(self, product_name: str) -> Optional[str]:
        """Get a generic food image based on product category"""
        try:
            clean_name = self.clean_product_name(product_name).lower()
            
            # Map product keywords to generic food images
            food_image_map = {
                'pan': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400',
                'leche': 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400',
                'queso': 'https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=400',
                'carne': 'https://images.unsplash.com/photo-1544025162-d76694265947?w=400',
                'pescado': 'https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=400',
                'fruta': 'https://images.unsplash.com/photo-1619566636858-adf3ef4644b9?w=400',
                'verdura': 'https://images.unsplash.com/photo-1540420773420-3366772f4999?w=400',
                'arroz': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400',
                'pasta': 'https://images.unsplash.com/photo-1621996346565-e3dbc353d2e5?w=400',
                'aceite': 'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=400',
                'vinagre': 'https://images.unsplash.com/photo-1582735689369-4fe89db7117c?w=400',
                'azúcar': 'https://images.unsplash.com/photo-1581441363689-1f3c3c414635?w=400',
                'café': 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=400',
                'té': 'https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=400',
                'yogur': 'https://images.unsplash.com/photo-1488477181946-6428a0291777?w=400',
                'mantequilla': 'https://images.unsplash.com/photo-1586444248902-2f64eddc13df?w=400',
                'huevos': 'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=400',
                'jamón': 'https://images.unsplash.com/photo-1544025162-d76694265947?w=400',
                'salchichas': 'https://images.unsplash.com/photo-1544025162-d76694265947?w=400',
                'atún': 'https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=400',
                'conserva': 'https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=400',
                'agua': 'https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=400',
                'bebida': 'https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=400',
                'cerveza': 'https://images.unsplash.com/photo-1510812431401-41d2bd2722f3?w=400',
                'vino': 'https://images.unsplash.com/photo-1510812431401-41d2bd2722f3?w=400',
                'chocolate': 'https://images.unsplash.com/photo-1481391319762-47dff72954d9?w=400',
                'galletas': 'https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=400',
                'dulce': 'https://images.unsplash.com/photo-1488477181946-6428a0291777?w=400',
                'helado': 'https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=400',
                'sopa': 'https://images.unsplash.com/photo-1547592166-23ac45744acd?w=400',
                'salsa': 'https://images.unsplash.com/photo-1582735689369-4fe89db7117c?w=400',
                'especias': 'https://images.unsplash.com/photo-1582735689369-4fe89db7117c?w=400',
                'sal': 'https://images.unsplash.com/photo-1582735689369-4fe89db7117c?w=400',
                'harina': 'https://images.unsplash.com/photo-1586444248902-2f64eddc13df?w=400',
                'miel': 'https://images.unsplash.com/photo-1587049352846-4a222e784d38?w=400',
                'mermelada': 'https://images.unsplash.com/photo-1587049352846-4a222e784d38?w=400'
            }
            
            # Find matching keyword
            for keyword, image_url in food_image_map.items():
                if keyword in clean_name:
                    logger.info(f"Found generic food image for: {product_name} (keyword: {keyword})")
                    return image_url
            
            # Default generic food image if no specific match
            default_image = 'https://images.unsplash.com/photo-1619566636858-adf3ef4644b9?w=400'
            logger.info(f"Using default generic food image for: {product_name}")
            return default_image
            
        except Exception as e:
            logger.error(f"Error getting generic food image for {product_name}: {e}")
            return None
    
    def find_product_image(self, product_name: str) -> Optional[str]:
        """Try multiple sources to find a product image"""
        sources = [
            ("E-commerce Sites", self.search_ecommerce_images),  # New high-priority source
            ("Open Food Facts", self.search_openfoodfacts),
            ("Google Custom Search", self.search_google_images),
            ("Bing Image Search", self.search_bing_images),
            ("Unsplash Fallback", self.search_unsplash),
            ("Generic Food Image", self.get_generic_food_image)
        ]
        
        for source_name, search_func in sources:
            try:
                image_url = search_func(product_name)
                if image_url:
                    logger.info(f"Found image via {source_name} for: {product_name}")
                    return image_url
                time.sleep(0.5)  # Small delay between sources
            except Exception as e:
                logger.error(f"Error with {source_name} for {product_name}: {e}")
                continue
        
        logger.warning(f"No image found from any source for: {product_name}")
        return None
    
    def get_products_without_images(self) -> List[Dict[str, Any]]:
        """Get all products that don't have image_url set"""
        try:
            response = self.supabase.table('products').select('id, name, store_id').is_('image_url', 'null').execute()
            
            if hasattr(response, 'data') and response.data:
                logger.info(f"Found {len(response.data)} products without images")
                return response.data
            else:
                logger.info("No products found without images")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching products without images: {e}")
            return []
    
    def update_product_image(self, product_id: str, image_url: str) -> bool:
        """Update a product's image_url in Supabase"""
        try:
            result = self.supabase.table('products').update({
                'image_url': image_url
            }).eq('id', product_id).execute()
            
            if hasattr(result, 'data') and result.data:
                logger.info(f"Updated image for product ID: {product_id}")
                return True
            else:
                logger.warning(f"Failed to update image for product ID: {product_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating product image: {e}")
            return False
    
    def process_products(self, batch_size: int = 50, delay: float = 0.5) -> Dict[str, Any]:
        """Process all products without images"""
        products = self.get_products_without_images()
        
        if not products:
            logger.info("✅ All products already have images!")
            return {
                'total_products': 0,
                'images_found': 0,
                'images_updated': 0,
                'failed_updates': 0
            }
        
        total_products = len(products)
        images_found = 0
        images_updated = 0
        failed_updates = 0
        
        logger.info(f"🖼️ Processing {total_products} products without images...")
        
        for i, product in enumerate(products):
            try:
                # Quick progress indicator
                if (i + 1) % 5 == 0:
                    logger.info(f"📊 Progress: {i+1}/{total_products} ({((i+1)/total_products*100):.1f}%)")
                
                # Search for image using multiple sources
                image_url = self.find_product_image(product['name'])
                
                if image_url:
                    images_found += 1
                    
                    # Update product with image URL
                    if self.update_product_image(product['id'], image_url):
                        images_updated += 1
                        logger.info(f"✅ [{i+1}/{total_products}] Found image for: {product['name'][:50]}...")
                    else:
                        failed_updates += 1
                        logger.warning(f"❌ [{i+1}/{total_products}] Failed to update: {product['name'][:50]}...")
                else:
                    failed_updates += 1
                    logger.warning(f"❌ [{i+1}/{total_products}] No image found for: {product['name'][:50]}...")
                
                # Shorter delay for faster processing
                time.sleep(delay)
                
            except Exception as e:
                logger.error(f"❌ Error processing product {product['name']}: {e}")
                failed_updates += 1
        
        return {
            'total_products': total_products,
            'images_found': images_found,
            'images_updated': images_updated,
            'failed_updates': failed_updates
        }
    
    def run_update(self, batch_size: int = 50, delay: float = 1.0) -> Dict[str, Any]:
        """Main method to run the image update process"""
        logger.info("Starting enhanced product image update process")
        
        result = self.process_products(batch_size, delay)
        
        # Log results
        logger.info("Image Update Summary:")
        logger.info(f"   Total products processed: {result['total_products']}")
        logger.info(f"   Images found: {result['images_found']}")
        logger.info(f"   Images updated: {result['images_updated']}")
        logger.info(f"   Failed updates: {result['failed_updates']}")
        
        success_rate = (result['images_updated'] / result['total_products'] * 100) if result['total_products'] > 0 else 0
        logger.info(f"   Success rate: {success_rate:.1f}%")
        
        return result

def main():
    """Main function to run the image update"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Update product images from multiple sources')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size for processing (default: 50)')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between requests in seconds (default: 0.5)')
    
    args = parser.parse_args()
    
    try:
        updater = ProductImageUpdater()
        result = updater.run_update(args.batch_size, args.delay)
        
        if result['images_updated'] > 0:
            logger.info("🎉 Image update completed successfully!")
            sys.exit(0)
        elif result['total_products'] == 0:
            logger.info("🎉 All products already have images!")
            sys.exit(0)
        else:
            logger.warning("⚠️ No images were updated")
            sys.exit(1)
                
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 