#!/usr/bin/env python3
"""
Product Image Updater
Fetches product images from Open Food Facts API and updates Supabase database
"""

import requests
import os
import sys
import time
import logging
from supabase import create_client, Client
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import re

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
        """Initialize the updater with Supabase connection"""
        load_dotenv()
        
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment variables")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        logger.info("Supabase connection initialized")
        
        # Open Food Facts API base URL
        self.openfoodfacts_api = "https://world.openfoodfacts.org/api/v0/product/"
    
    def clean_product_name(self, name: str) -> str:
        """Clean product name for better search results"""
        # Remove common store prefixes and suffixes
        name = re.sub(r'\b(El Corte Inglés|Carrefour|Dia|Lidl|Mercadona|Alcampo)\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\b(Classic|Extra|Premium|Selection|Al Punto|Nuestra Alacena)\b', '', name, flags=re.IGNORECASE)
        
        # Remove quantity information
        name = re.sub(r'\d+\s*(kg|g|l|ml|cl|pack|units?|x)\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\(\d+\s*(kg|g|l|ml|cl|pack|units?|x)\)', '', name, flags=re.IGNORECASE)
        
        # Remove common packaging terms
        name = re.sub(r'\b(botella|bolsa|caja|sobre|bandeja|frasco|lata|brik|pack)\b', '', name, flags=re.IGNORECASE)
        
        # Clean up extra spaces and punctuation
        name = re.sub(r'\s+', ' ', name)
        name = name.strip()
        
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
                        logger.info(f"Found image for: {product_name}")
                        return product['image_front_url']
                    elif product.get('image_url'):
                        logger.info(f"Found image for: {product_name}")
                        return product['image_url']
            
            logger.warning(f"No image found for: {product_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error searching Open Food Facts for {product_name}: {e}")
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
    
    def process_products(self, batch_size: int = 50, delay: float = 1.0) -> Dict[str, Any]:
        """Process all products without images"""
        products = self.get_products_without_images()
        
        if not products:
            logger.info("No products to process")
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
        
        logger.info(f"Processing {total_products} products...")
        
        for i, product in enumerate(products):
            try:
                logger.info(f"Processing {i+1}/{total_products}: {product['name']}")
                
                # Search for image
                image_url = self.search_openfoodfacts(product['name'])
                
                if image_url:
                    images_found += 1
                    
                    # Update product with image URL
                    if self.update_product_image(product['id'], image_url):
                        images_updated += 1
                    else:
                        failed_updates += 1
                
                # Add delay to be respectful to the API
                time.sleep(delay)
                
                # Progress update every 10 products
                if (i + 1) % 10 == 0:
                    logger.info(f"Progress: {i+1}/{total_products} products processed")
                
            except Exception as e:
                logger.error(f"Error processing product {product['name']}: {e}")
                failed_updates += 1
        
        return {
            'total_products': total_products,
            'images_found': images_found,
            'images_updated': images_updated,
            'failed_updates': failed_updates
        }
    
    def run_update(self, batch_size: int = 50, delay: float = 1.0) -> Dict[str, Any]:
        """Main method to run the image update process"""
        logger.info("Starting product image update process")
        
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
    
    parser = argparse.ArgumentParser(description='Update product images from Open Food Facts')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size for processing (default: 50)')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests in seconds (default: 1.0)')
    
    args = parser.parse_args()
    
    try:
        updater = ProductImageUpdater()
        result = updater.run_update(args.batch_size, args.delay)
        
        if result['images_updated'] > 0:
            logger.info("Image update completed successfully!")
            sys.exit(0)
        else:
            logger.warning("No images were updated")
            sys.exit(1)
                
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 