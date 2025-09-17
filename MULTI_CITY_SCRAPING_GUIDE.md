# Multi-City Multi-Market Scraping Guide

## 🌍 Overview

We've successfully created a comprehensive multi-city, multi-market scraping system that can scrape products from different markets across different Spanish cities. This system coordinates 13+ different market scrapers and 20+ Spanish cities.

## 🏪 Available Markets

### City-Supporting Markets
These markets can be scraped for specific cities:
- **Carrefour** - 4 categories, 40 products per city
- **Mercadona** - 4 categories, 30 products per city

### Single-Location Markets  
These markets scrape from their main location:
- **El Corte Inglés** - 3 categories, 100 products
- **Lidl** - 2 categories, 80 products
- **Dia** - 2 categories, 60 products
- **Consum** - 2 categories, 70 products
- **Condisline** - 3 categories, 50 products
- **Bonpreu** - 2 categories, 60 products
- **Alcampo** - 2 categories, 70 products
- **Bonarea** - 2 categories, 50 products
- **Eroski** - 2 categories, 60 products
- **Caprabo** - 2 categories, 50 products
- **Aldi** - 2 categories, 60 products

## 🏙️ Available Cities

20 major Spanish cities with population data:
- Madrid (3.2M), Barcelona (1.6M), Valencia (791K), Sevilla (688K)
- Zaragoza (681K), Málaga (578K), Murcia (460K), Palma (409K)
- Las Palmas (380K), Bilbao (345K), Alicante (337K), Córdoba (326K)
- Valladolid (299K), Vigo (295K), Gijón (271K), L'Hospitalet (264K)
- A Coruña (246K), Granada (232K), Elche (234K), Oviedo (220K)

## 🚀 How to Use

### 1. Comprehensive Multi-City Scraping

```python
from scraper.comprehensive_multi_city_scraper import scrape_comprehensive_multi_city

# Scrape all major cities with all markets
scrape_comprehensive_multi_city()

# Scrape specific cities and markets
scrape_comprehensive_multi_city(
    cities=['Madrid', 'Barcelona', 'Valencia'],
    markets=['carrefour', 'mercadona', 'lidl', 'dia'],
    max_products_per_city=25,
    max_products_per_market=40
)
```

### 2. Specific City Multi-Market Scraping

```python
from scraper.comprehensive_multi_city_scraper import scrape_specific_city_markets

# Scrape multiple markets for one city
scrape_specific_city_markets(
    city='Barcelona',
    markets=['carrefour', 'mercadona', 'lidl'],
    max_products=30
)
```

### 3. Individual Market Scraping

```python
from scraper.comprehensive_multi_city_scraper import run_market_scraper

# City-supporting market
run_market_scraper('carrefour', ['Madrid', 'Barcelona'], 40)

# Single-location market
run_market_scraper('lidl', None, 80)
```

## ⏰ Automated Scheduling

Use the multi-city scheduler for automated scraping:

```python
python multi_city_scheduler.py
```

### Schedule Features:
- **City Rotation**: Automatically rotates through different cities each day
- **Market Scheduling**: Each market runs at different times to avoid conflicts
- **Comprehensive Weekly Runs**: Full scraping across all cities and markets on Sundays
- **Configurable**: Easy to modify schedules and parameters

### Default Schedule:
- Carrefour: Daily at 09:00 (city-supporting)
- Mercadona: Daily at 10:30 (city-supporting)
- Lidl: Daily at 12:00 (single-location)
- Dia: Daily at 13:30 (single-location)
- Consum: Daily at 15:00 (single-location)
- El Corte Inglés: Daily at 16:30 (single-location)
- Condisline: Daily at 18:00 (single-location)
- Bonpreu: Daily at 19:30 (single-location)
- Alcampo: Daily at 21:00 (single-location)
- **Comprehensive Weekly**: Sunday at 08:00

## 🧪 Testing and Demo

### Run Market Status Check:
```bash
python test_multi_city_scraping.py
```

### Run Interactive Demo:
```bash
python run_multi_city_demo.py
```

## 📊 Key Features

### ✅ What's Working:
- **13+ Market Scrapers** coordinated through one system
- **20+ Spanish Cities** with population-based prioritization
- **City Rotation** system for efficient coverage
- **Automated Scheduling** with conflict avoidance
- **Mixed Market Support** (city-supporting + single-location)
- **Product Tracking** with city information
- **Price History** tracking per city and market
- **Error Handling** and logging
- **Configurable Parameters** for all aspects

### 🏗️ Architecture:
- **Modular Design**: Each market scraper is independent
- **City Coordination**: Smart rotation and scheduling
- **Database Integration**: Supabase with city tracking
- **Error Recovery**: Continues on failures
- **Resource Management**: Proper delays and rate limiting

## 🎯 Usage Examples

### Example 1: Daily City Rotation
The scheduler automatically rotates through cities:
- Monday: Madrid, Barcelona, Valencia, Sevilla, Bilbao
- Tuesday: Málaga, Zaragoza, Murcia, Palma, Las Palmas
- Wednesday: Alicante, Córdoba, Valladolid, Vigo, Gijón
- And so on...

### Example 2: Market-Specific Scheduling
- **Morning**: City-supporting markets (Carrefour, Mercadona)
- **Afternoon**: Single-location markets (Lidl, Dia, Consum)
- **Evening**: Additional markets (El Corte Inglés, Condisline, etc.)

### Example 3: Comprehensive Coverage
- **Sunday**: Full scraping across all cities and markets
- **Weekdays**: Targeted city rotation with specific markets
- **Flexible**: Easy to add new markets or cities

## 🔧 Configuration

All settings can be modified in:
- `multi_city_schedule_config.json` - Scheduler settings
- `scraper/comprehensive_multi_city_scraper.py` - Market configurations
- `data/cities_es.json` - City data

## 📈 Benefits

1. **Comprehensive Coverage**: All major Spanish cities and markets
2. **Efficient Resource Usage**: Smart scheduling and rotation
3. **Scalable**: Easy to add new markets or cities
4. **Reliable**: Error handling and recovery
5. **Flexible**: Multiple usage patterns supported
6. **Automated**: Set-and-forget scheduling
7. **Data Rich**: City-specific product tracking

## 🚀 Next Steps

The system is ready for production use! You can:
1. Run the scheduler for automated scraping
2. Use specific functions for targeted scraping
3. Add new markets by following the existing patterns
4. Modify city lists or scheduling as needed
5. Monitor results through the database

Happy scraping! 🎉
