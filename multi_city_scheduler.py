#!/usr/bin/env python3
"""
Multi-City Multi-Market Scheduler
Efficiently schedules scraping across different cities and markets
"""

import time
import schedule
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random

# Import our comprehensive scraper
from scraper.comprehensive_multi_city_scraper import (
    scrape_comprehensive_multi_city,
    scrape_specific_city_markets,
    MARKET_CONFIGS
)

class MultiCityScheduler:
    def __init__(self):
        self.schedule_config = self.load_schedule_config()
        self.last_run_times = {}
        
    def load_schedule_config(self) -> Dict:
        """Load scheduling configuration"""
        default_config = {
            "city_rotation": {
                "enabled": True,
                "major_cities": ["Madrid", "Barcelona", "Valencia", "Sevilla", "Bilbao", "Málaga", "Zaragoza"],
                "minor_cities": ["Murcia", "Palma", "Las Palmas", "Alicante", "Córdoba", "Valladolid"],
                "rotation_days": 7  # Rotate cities every 7 days
            },
            "market_schedules": {
                "carrefour": {"frequency": "daily", "time": "09:00", "max_products_per_city": 40},
                "mercadona": {"frequency": "daily", "time": "10:30", "max_products_per_city": 30},
                "lidl": {"frequency": "daily", "time": "12:00", "max_products": 80},
                "dia": {"frequency": "daily", "time": "13:30", "max_products": 60},
                "consum": {"frequency": "daily", "time": "15:00", "max_products": 70},
                "elcorte": {"frequency": "daily", "time": "16:30", "max_products": 100},
                "condisline": {"frequency": "daily", "time": "18:00", "max_products": 50},
                "bonpreu": {"frequency": "daily", "time": "19:30", "max_products": 60},
                "alcampo": {"frequency": "daily", "time": "21:00", "max_products": 70}
            },
            "comprehensive_runs": {
                "enabled": True,
                "frequency": "weekly",
                "day": "sunday",
                "time": "08:00",
                "max_cities": 5,
                "max_products_per_city": 25
            }
        }
        
        try:
            with open('multi_city_schedule_config.json', 'r') as f:
                config = json.load(f)
            return {**default_config, **config}
        except FileNotFoundError:
            return default_config
    
    def save_schedule_config(self):
        """Save current schedule configuration"""
        with open('multi_city_schedule_config.json', 'w') as f:
            json.dump(self.schedule_config, f, indent=2)
    
    def get_cities_for_rotation(self, day_of_week: int) -> List[str]:
        """Get cities to scrape based on rotation schedule"""
        config = self.schedule_config["city_rotation"]
        
        if not config["enabled"]:
            return config["major_cities"][:5]  # Default to first 5 major cities
        
        # Rotate cities based on day of week
        rotation_days = config["rotation_days"]
        cycle_position = day_of_week % rotation_days
        
        if cycle_position < 5:  # First 5 days: major cities
            cities = config["major_cities"][:5]
        else:  # Remaining days: mix of major and minor cities
            major_cities = config["major_cities"][:3]
            minor_cities = config["minor_cities"][:2]
            cities = major_cities + minor_cities
        
        return cities
    
    def run_city_supporting_market(self, market_name: str):
        """Run a city-supporting market scraper"""
        config = self.schedule_config["market_schedules"].get(market_name, {})
        
        if market_name not in MARKET_CONFIGS:
            print(f"❌ Unknown market: {market_name}")
            return
        
        if not MARKET_CONFIGS[market_name]["city_support"]:
            print(f"⚠️ {market_name} doesn't support cities, skipping city rotation")
            return
        
        # Get cities for today's rotation
        today = datetime.now().weekday()
        cities = self.get_cities_for_rotation(today)
        
        max_products = config.get("max_products_per_city", 30)
        
        print(f"🏪 Running {market_name} for cities: {', '.join(cities)}")
        
        try:
            from scraper.comprehensive_multi_city_scraper import run_market_scraper
            products = run_market_scraper(market_name, cities, max_products)
            
            self.last_run_times[market_name] = datetime.now()
            print(f"✅ {market_name} completed: {products} products")
            
        except Exception as e:
            print(f"❌ Error running {market_name}: {e}")
    
    def run_single_location_market(self, market_name: str):
        """Run a single-location market scraper"""
        config = self.schedule_config["market_schedules"].get(market_name, {})
        
        if market_name not in MARKET_CONFIGS:
            print(f"❌ Unknown market: {market_name}")
            return
        
        if MARKET_CONFIGS[market_name]["city_support"]:
            print(f"⚠️ {market_name} supports cities, use run_city_supporting_market instead")
            return
        
        max_products = config.get("max_products", 50)
        
        print(f"🏪 Running {market_name} (single location)")
        
        try:
            from scraper.comprehensive_multi_city_scraper import run_market_scraper
            products = run_market_scraper(market_name, None, max_products)
            
            self.last_run_times[market_name] = datetime.now()
            print(f"✅ {market_name} completed: {products} products")
            
        except Exception as e:
            print(f"❌ Error running {market_name}: {e}")
    
    def run_comprehensive_weekly(self):
        """Run comprehensive weekly scraping"""
        config = self.schedule_config["comprehensive_runs"]
        
        if not config["enabled"]:
            print("ℹ️ Comprehensive weekly runs disabled")
            return
        
        print("🚀 Starting comprehensive weekly scraping...")
        
        # Get cities for comprehensive run
        cities = self.get_cities_for_rotation(datetime.now().weekday())
        cities = cities[:config.get("max_cities", 5)]
        
        # Select markets for comprehensive run (mix of city-supporting and single-location)
        city_markets = [m for m in MARKET_CONFIGS.keys() if MARKET_CONFIGS[m]["city_support"]][:3]
        single_markets = [m for m in MARKET_CONFIGS.keys() if not MARKET_CONFIGS[m]["city_support"]][:4]
        all_markets = city_markets + single_markets
        
        max_products_per_city = config.get("max_products_per_city", 25)
        max_products_per_market = 40
        
        try:
            scrape_comprehensive_multi_city(
                cities=cities,
                markets=all_markets,
                max_products_per_city=max_products_per_city,
                max_products_per_market=max_products_per_market
            )
            
            self.last_run_times["comprehensive"] = datetime.now()
            print("✅ Comprehensive weekly scraping completed")
            
        except Exception as e:
            print(f"❌ Error in comprehensive scraping: {e}")
    
    def setup_schedules(self):
        """Set up all scheduled jobs"""
        print("⏰ Setting up multi-city multi-market schedules...")
        
        # Clear existing schedules
        schedule.clear()
        
        # Schedule city-supporting markets
        for market_name, config in self.schedule_config["market_schedules"].items():
            if market_name not in MARKET_CONFIGS:
                continue
            
            frequency = config.get("frequency", "daily")
            time_str = config.get("time", "09:00")
            
            if MARKET_CONFIGS[market_name]["city_support"]:
                if frequency == "daily":
                    schedule.every().day.at(time_str).do(self.run_city_supporting_market, market_name)
                elif frequency == "weekly":
                    schedule.every().week.at(time_str).do(self.run_city_supporting_market, market_name)
            else:
                if frequency == "daily":
                    schedule.every().day.at(time_str).do(self.run_single_location_market, market_name)
                elif frequency == "weekly":
                    schedule.every().week.at(time_str).do(self.run_single_location_market, market_name)
        
        # Schedule comprehensive weekly run
        comprehensive_config = self.schedule_config["comprehensive_runs"]
        if comprehensive_config["enabled"]:
            day = comprehensive_config.get("day", "sunday")
            time_str = comprehensive_config.get("time", "08:00")
            
            if day == "sunday":
                schedule.every().sunday.at(time_str).do(self.run_comprehensive_weekly)
            elif day == "monday":
                schedule.every().monday.at(time_str).do(self.run_comprehensive_weekly)
            # Add more days as needed
        
        print(f"✅ Scheduled {len(schedule.jobs)} jobs")
    
    def show_schedule_status(self):
        """Show current schedule status"""
        print("📅 Multi-City Multi-Market Schedule Status")
        print("=" * 50)
        
        print(f"🏙️ City Rotation: {'Enabled' if self.schedule_config['city_rotation']['enabled'] else 'Disabled'}")
        print(f"🔄 Rotation Days: {self.schedule_config['city_rotation']['rotation_days']}")
        
        print(f"\n📊 Market Schedules:")
        for market, config in self.schedule_config["market_schedules"].items():
            frequency = config.get("frequency", "daily")
            time_str = config.get("time", "09:00")
            city_support = MARKET_CONFIGS.get(market, {}).get("city_support", False)
            support_text = "City-supporting" if city_support else "Single-location"
            
            print(f"  🏪 {market}: {frequency} at {time_str} ({support_text})")
        
        comprehensive = self.schedule_config["comprehensive_runs"]
        if comprehensive["enabled"]:
            day = comprehensive.get("day", "sunday")
            time_str = comprehensive.get("time", "08:00")
            print(f"\n🚀 Comprehensive Weekly: {day} at {time_str}")
        
        print(f"\n⏰ Total Scheduled Jobs: {len(schedule.jobs)}")
        
        # Show last run times
        if self.last_run_times:
            print(f"\n🕒 Last Run Times:")
            for market, last_run in self.last_run_times.items():
                print(f"  {market}: {last_run.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def run_scheduler(self):
        """Run the scheduler"""
        print("🚀 Starting Multi-City Multi-Market Scheduler")
        print("Press Ctrl+C to stop")
        
        self.setup_schedules()
        self.show_schedule_status()
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            print("\n⏹️ Scheduler stopped by user")
        except Exception as e:
            print(f"\n❌ Scheduler error: {e}")

def main():
    """Main function"""
    scheduler = MultiCityScheduler()
    
    # Show current status
    scheduler.show_schedule_status()
    
    # Option to run scheduler or just show status
    print("\nOptions:")
    print("1. Run scheduler")
    print("2. Show status only")
    print("3. Test city rotation")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        scheduler.run_scheduler()
    elif choice == "2":
        print("✅ Status displayed above")
    elif choice == "3":
        # Test city rotation for different days
        print("\n🧪 Testing city rotation:")
        for day in range(7):
            cities = scheduler.get_cities_for_rotation(day)
            day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][day]
            print(f"  {day_name}: {', '.join(cities)}")

if __name__ == "__main__":
    main()
