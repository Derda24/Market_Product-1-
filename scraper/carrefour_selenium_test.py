import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import json
import os

options = uc.ChromeOptions()
options.add_argument("--lang=es-ES")
options.add_argument("--window-size=1280,800")

# Start undetected Chrome
driver = uc.Chrome(options=options)
driver.get("https://www.carrefour.es/supermercado/fruta/cat20010/c")

time.sleep(5)  # Wait for page to load

# Load cookies from file if present
cookie_path = "scraper/carrefour_cookies.json"
if os.path.exists(cookie_path):
    with open(cookie_path, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    for cookie in cookies:
        for k in ["sameSite", "storeId", "hostOnly", "session", "id"]:
            cookie.pop(k, None)
        try:
            driver.add_cookie(cookie)
        except Exception as e:
            print(f"Cookie error: {e}")
    driver.refresh()
    time.sleep(5)
else:
    print("⚠️ Please export your Carrefour cookies as JSON and save them to 'scraper/carrefour_cookies.json'.")
    print("   Then rerun this script.")

# Accept cookies if present
try:
    accept_btn = driver.find_element(By.XPATH, "//button[contains(., 'Aceptar')]")
    accept_btn.click()
    print("🍪 Cookie banner accepted.")
    time.sleep(2)
except Exception:
    pass

# Scroll to load products
for _ in range(5):
    driver.execute_script("window.scrollBy(0, 1000);")
    time.sleep(1)

# Find product cards
products = driver.find_elements(By.CSS_SELECTOR, "li.product-card")
print(f"🛒 Found {len(products)} products")

for product in products:
    try:
        name = product.find_element(By.TAG_NAME, "h2").text
        price = product.find_element(By.CSS_SELECTOR, ".product-card-price__price").text
        print(f"{name} — {price}")
    except Exception as e:
        print(f"❌ Error parsing product: {e}")

driver.quit() 