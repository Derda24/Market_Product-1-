#!/usr/bin/env python3
"""
Excel to Supabase Import Script with Update Support
Imports product data from Excel file to Supabase database, updating existing products
"""

import pandas as pd
import os
import sys
from supabase import create_client, Client
from typing import List, Dict, Any
import logging
from datetime import datetime
from dotenv import load_dotenv

# Setup logging without emojis for Windows compatibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('excel_import_update.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ExcelToSupabaseImporter:
    def __init__(self):
        """Initialize the importer with Supabase connection"""
        # Load environment variables from .env file
        load_dotenv()
        
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment variables")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        logger.info("Supabase connection initialized")
    
    def validate_excel_file(self, file_path: str) -> bool:
        """Validate that the Excel file exists and has the required columns"""
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False
        
        try:
            df = pd.read_excel(file_path)
            required_columns = ['Name', 'Price', 'Category', 'Store ID', 'Quantity']
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                logger.info(f"Available columns: {list(df.columns)}")
                return False
            
            logger.info(f"Excel file validated: {len(df)} rows found")
            logger.info(f"Columns: {list(df.columns)}")
            return True
            
        except Exception as e:
            logger.error(f"Error reading Excel file: {e}")
            return False
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare data for import"""
        # Create a copy to avoid modifying original
        df_clean = df.copy()
        
        # Remove rows with missing required data
        initial_count = len(df_clean)
        df_clean = df_clean.dropna(subset=['Name', 'Price'])
        
        if len(df_clean) < initial_count:
            logger.warning(f"Removed {initial_count - len(df_clean)} rows with missing Name or Price")
        
        # Convert price to numeric, handle currency symbols
        df_clean['Price'] = pd.to_numeric(df_clean['Price'].astype(str).str.replace('€', '').str.replace('$', '').str.replace(',', '.'), errors='coerce')
        
        # Remove rows with invalid prices
        invalid_prices = df_clean['Price'].isna()
        if invalid_prices.any():
            logger.warning(f"Removed {invalid_prices.sum()} rows with invalid prices")
            df_clean = df_clean[~invalid_prices]
        
        # Clean text fields
        df_clean['Name'] = df_clean['Name'].astype(str).str.strip()
        df_clean['Category'] = df_clean['Category'].astype(str).str.strip()
        df_clean['Store ID'] = df_clean['Store ID'].astype(str).str.strip()
        df_clean['Quantity'] = df_clean['Quantity'].astype(str).str.strip()
        
        # Replace empty strings with None for optional fields
        df_clean['Category'] = df_clean['Category'].replace('', None)
        df_clean['Store ID'] = df_clean['Store ID'].replace('', None)
        df_clean['Quantity'] = df_clean['Quantity'].replace('', None)
        
        logger.info(f"Data cleaned: {len(df_clean)} valid rows remaining")
        return df_clean
    
    def check_existing_product(self, name: str, store_id: str) -> str:
        """Check if a product exists and return its ID"""
        try:
            response = self.supabase.table('products').select('id').eq('name', name).eq('store_id', store_id).limit(1).execute()
            if hasattr(response, 'data') and response.data:
                return response.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"Error checking existing product: {e}")
            return None
    
    def import_to_supabase(self, df: pd.DataFrame, batch_size: int = 100) -> Dict[str, Any]:
        """Import data to Supabase with update support"""
        total_rows = len(df)
        successful_imports = 0
        successful_updates = 0
        failed_imports = 0
        errors = []
        
        logger.info(f"Starting import of {total_rows} rows...")
        
        # Process each row individually to handle updates
        for index, row in df.iterrows():
            try:
                product_data = {
                    'name': row['Name'],
                    'price': float(row['Price']),
                    'category': row['Category'] if pd.notna(row['Category']) else None,
                    'store_id': row['Store ID'] if pd.notna(row['Store ID']) else None,
                    'quantity': row['Quantity'] if pd.notna(row['Quantity']) else None
                }
                
                # Check if product already exists
                existing_id = self.check_existing_product(product_data['name'], product_data['store_id'])
                
                if existing_id:
                    # Update existing product
                    try:
                        result = self.supabase.table('products').update(product_data).eq('id', existing_id).execute()
                        if hasattr(result, 'data') and result.data:
                            successful_updates += 1
                            logger.info(f"Updated product: {product_data['name']}")
                        else:
                            failed_imports += 1
                            errors.append(f"Failed to update product: {product_data['name']}")
                    except Exception as e:
                        failed_imports += 1
                        errors.append(f"Error updating product {product_data['name']}: {e}")
                else:
                    # Insert new product
                    try:
                        result = self.supabase.table('products').insert(product_data).execute()
                        if hasattr(result, 'data') and result.data:
                            successful_imports += 1
                            logger.info(f"Inserted new product: {product_data['name']}")
                        else:
                            failed_imports += 1
                            errors.append(f"Failed to insert product: {product_data['name']}")
                    except Exception as e:
                        failed_imports += 1
                        errors.append(f"Error inserting product {product_data['name']}: {e}")
                
                # Progress update every 50 rows
                if (index + 1) % 50 == 0:
                    logger.info(f"Processed {index + 1}/{total_rows} rows...")
                    
            except Exception as e:
                logger.error(f"Error processing row {index + 1}: {e}")
                failed_imports += 1
                errors.append(f"Row processing error: {e}")
        
        return {
            'total_rows': total_rows,
            'successful_imports': successful_imports,
            'successful_updates': successful_updates,
            'failed_imports': failed_imports,
            'errors': errors
        }
    
    def run_import(self, excel_file_path: str, batch_size: int = 100) -> Dict[str, Any]:
        """Main method to run the complete import process"""
        logger.info("Starting Excel to Supabase import process")
        
        # Step 1: Validate file
        if not self.validate_excel_file(excel_file_path):
            return {'error': 'File validation failed'}
        
        # Step 2: Read and clean data
        try:
            df = pd.read_excel(excel_file_path)
            df_clean = self.clean_data(df)
        except Exception as e:
            logger.error(f"Error reading Excel file: {e}")
            return {'error': f'Error reading Excel file: {e}'}
        
        # Step 3: Import to Supabase
        result = self.import_to_supabase(df_clean, batch_size)
        
        # Step 4: Log results
        logger.info("Import Summary:")
        logger.info(f"   Total rows processed: {result['total_rows']}")
        logger.info(f"   New products inserted: {result['successful_imports']}")
        logger.info(f"   Existing products updated: {result['successful_updates']}")
        logger.info(f"   Failed operations: {result['failed_imports']}")
        
        if result['errors']:
            logger.warning(f"   Errors encountered: {len(result['errors'])}")
            for error in result['errors'][:5]:  # Show first 5 errors
                logger.warning(f"     - {error}")
        
        return result

def main():
    """Main function to run the import"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Import Excel data to Supabase with update support')
    parser.add_argument('excel_file', help='Path to the Excel file')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for imports (default: 100)')
    
    args = parser.parse_args()
    
    try:
        importer = ExcelToSupabaseImporter()
        result = importer.run_import(args.excel_file, args.batch_size)
        
        if 'error' in result:
            logger.error(f"Import failed: {result['error']}")
            sys.exit(1)
        else:
            logger.info("Import completed successfully!")
            if result['failed_imports'] > 0:
                sys.exit(1)  # Exit with error if there were failures
            else:
                sys.exit(0)
                
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 