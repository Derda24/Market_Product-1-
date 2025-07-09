from dotenv import load_dotenv
import os
from supabase import create_client
import datetime

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Path to the debug log file
DEBUG_LOG_FILE = "debug_log.txt"

def log_debug_message(message):
    """Logs a debug message to a file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")

def get_categories_by_store(store_id):
    """Fetches all categories for a given store_id from the Supabase 'categories' table."""
    try:
        response = supabase.table("categories").select("*").eq("store_id", store_id).execute()
        log_debug_message(f"📦 get_categories_by_store response: {response}")
        
        if hasattr(response, "data") and response.data:
            return response.data
        else:
            log_debug_message("⚠️ No categories found for given store_id.")
            return []
    except Exception as e:
        log_debug_message(f"❌ Exception in get_categories_by_store: {e}")
        return []

def get_product_by_name_and_store(name, store_id):
    """Fetches a product by its name and store_id."""
    try:
        response = supabase.table("products").select("*").eq("name", name).eq("store_id", store_id).limit(1).execute()
        if hasattr(response, "data") and response.data:
            return response.data[0]
        return None
    except Exception as e:
        log_debug_message(f"❌ Exception in get_product_by_name_and_store: {e}")
        return None

def update_product_price(product_id, new_price, store_id=None):
    """Updates the price of a product and logs the change in price_history."""
    try:
        # 1. Update the product price
        response = supabase.table("products").update({"price": new_price, "updated_at": "now()"}).eq("id", product_id).execute()
        if hasattr(response, "data") and response.data:
            log_debug_message(f"✅ Price updated for product ID {product_id}")
        else:
            log_debug_message(f"❌ Failed to update price for product ID {product_id}")

        # 2. Mark previous price_history as not current
        supabase.table("price_history").update({
            "is_current": False,
            "valid_until": "now()"
        }).eq("product_id", product_id).eq("is_current", True).execute()

        # 3. Insert new price_history row
        # If store_id is not provided, try to fetch it
        if not store_id:
            product = supabase.table("products").select("store_id").eq("id", product_id).limit(1).execute()
            if hasattr(product, "data") and product.data:
                store_id = product.data[0]["store_id"]
            else:
                store_id = "unknown"
        supabase.table("price_history").insert({
            "product_id": product_id,
            "price": new_price,
            "store_id": store_id,
            "is_current": True,
            "recorded_at": "now()"
        }).execute()
    except Exception as e:
        log_debug_message(f"❌ Exception in update_product_price: {e}")

def insert_product(name, price, category, store_id, quantity=None):
    data = {
        "name": name,
        "price": price,
        "category": category,
        "store_id": store_id,
        "quantity": quantity
    }

    log_debug_message(f"Attempting to insert product: {data}")  # Log the data being sent

    try:
        result = supabase.table("products").insert(data).execute()
        log_debug_message(f"Supabase Response: {result}")  # Log the full response

        # Check if the insertion was successful
        if hasattr(result, "data") and result.data:
            print(f"✅ Successfully inserted: {name}")
            log_debug_message(f"✅ Successfully inserted: {name}")
        else:
            print(f"❌ Failed to insert: {name}")
            log_debug_message(f"❌ Failed to insert: {name}")
            log_debug_message(f"Response Details: {result}")
    except Exception as e:
        print(f"❌ Exception during Supabase insert: {e}")
        log_debug_message(f"❌ Exception during Supabase insert: {e}")

if __name__ == "__main__":
    # Example test
    insert_product(
        name="Test Product",
        price=9.99,
        category="test_category",
        store_id="lidl",
        quantity="1"
    )
    