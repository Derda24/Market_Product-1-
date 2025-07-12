#!/usr/bin/env python3
"""
Product Image Updater with Google Custom Search
Fetches product images from Google Custom Search API as backup
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
        logging.FileHandler('image_update_google.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class GoogleImageUpdater:
    def __init__(self):
        """Initialize the updater with Supabase connection"""
        load_dotenv()
        
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.google_cse_id = os.getenv('GOOGLE_CSE_ID')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment variables")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        logger.info("Supabase connection initialized")
        
        if not self.google_api_key or not self.google_cse_id:
            logger.warning("Google API credentials not found. Set GOOGLE_API_KEY and GOOGLE_CSE_ID for Google search.")
    
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
    
    def search_google_images(self, product_name: str) -> Optional[str]:
        """Search Google Custom Search for product images"""
        if not self.google_api_key or not self.google_cse_id:
            logger.warning("Google API credentials not configured")
            return None
        
        try:
            # Clean the product name
            clean_name = self.clean_product_name(product_name)
            
            # Google Custom Search API
            search_url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.google_api_key,
                'cx': self.google_cse_id,
                'q': f"{clean_name} product",
                'searchType': 'image',
                'num': 1,  # Get first result
                'imgSize': 'medium',
                'imgType': 'photo'
            }
            
            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('items') and len(data['items']) > 0:
                image_url = data['items'][0]['link']
                logger.info(f"Found Google image for: {product_name}")
                return image_url
            
            logger.warning(f"No Google image found for: {product_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error searching Google for {product_name}: {e}")
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
    
    def process_products(self, delay: float = 2.0) -> Dict[str, Any]:
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
        
        logger.info(f"Processing {total_products} products with Google search...")
        
        for i, product in enumerate(products):
            try:
                logger.info(f"Processing {i+1}/{total_products}: {product['name']}")
                
                # Search for image
                image_url = self.search_google_images(product['name'])
                
                if image_url:
                    images_found += 1
                    
                    # Update product with image URL
                    if self.update_product_image(product['id'], image_url):
                        images_updated += 1
                    else:
                        failed_updates += 1
                
                # Add delay to be respectful to the API
                time.sleep(delay)
                
                # Progress update every 5 products
                if (i + 1) % 5 == 0:
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
    
    def run_update(self, delay: float = 2.0) -> Dict[str, Any]:
        """Main method to run the image update process"""
        logger.info("Starting Google image update process")
        
        result = self.process_products(delay)
        
        # Log results
        logger.info("Google Image Update Summary:")
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
    
    parser = argparse.ArgumentParser(description='Update product images from Google Custom Search')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between requests in seconds (default: 2.0)')
    
    args = parser.parse_args()
    
    try:
        updater = GoogleImageUpdater()
        result = updater.run_update(args.delay)
        
        if result['images_updated'] > 0:
            logger.info("Google image update completed successfully!")
            sys.exit(0)
        else:
            logger.warning("No images were updated")
            sys.exit(1)
                
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 