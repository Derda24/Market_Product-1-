# Price History Visualization Setup

## 🎯 Overview

This guide will help you set up the price history visualization system for your Barcelona scraper project. The system includes:

- **Price History Table**: Tracks all price changes automatically
- **Interactive Charts**: Visualize price trends over time
- **API Endpoints**: Fetch price history data
- **Demo Page**: Test the visualization

## 📋 Prerequisites

1. **Supabase Database**: Your products table should be set up
2. **Environment Variables**: Supabase credentials configured
3. **Node.js Dependencies**: Chart.js and React Chart.js installed

## 🚀 Setup Steps

### Step 1: Run the Database Migration

1. Go to your [Supabase Dashboard](https://supabase.com/dashboard)
2. Navigate to **SQL Editor**
3. Copy the content from `supabase/migrations/20240802_fix_price_history_table_v2.sql`
4. Paste and run the migration

### Step 2: Configure Environment Variables

Create or update your `.env.local` file:

```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### Step 3: Test the Setup

Run the test script to verify everything is working:

```bash
python test_price_history.py
```

### Step 4: Start the Development Server

```bash
npm run dev
```

### Step 5: Access the Demo

Visit: `http://localhost:3000/price-history-demo`

## 📊 Features

### Price History Chart Component
- **Interactive Line Charts**: Shows price trends over time
- **Price Change Indicators**: Visual indicators for price increases/decreases
- **Detailed Tables**: Recent price changes with timestamps
- **Responsive Design**: Works on desktop and mobile

### API Endpoints
- **GET /api/priceHistory**: Fetches price history for a specific product
- **Automatic Fallback**: Returns current product data if no history exists

### Database Features
- **Automatic Tracking**: Price changes are recorded automatically via triggers
- **Performance Indexes**: Fast queries for price history data
- **Data Integrity**: Prevents duplicate entries and maintains referential integrity

## 🔧 How It Works

### 1. Automatic Price Tracking
When a scraper updates a product price, the `update_price_history()` trigger automatically:
- Records the new price in the `price_history` table
- Maintains a complete audit trail
- Links to the original product

### 2. Visualization
The React component:
- Fetches price history via API
- Creates interactive charts using Chart.js
- Shows price changes and percentages
- Displays detailed tables

### 3. Data Flow
```
Scraper → Updates Product Price → Trigger → Price History Table → API → Chart Component
```

## 🎨 Customization

### Chart Styling
Edit `components/PriceHistoryChart.jsx` to customize:
- Colors and themes
- Chart options and interactions
- Table styling and layout

### API Response
Modify `pages/api/priceHistory.js` to:
- Change data format
- Add filtering options
- Include additional fields

### Database Queries
Update the migration to:
- Add more indexes for performance
- Include additional tracking fields
- Modify trigger behavior

## 🐛 Troubleshooting

### Common Issues

1. **"No price history available"**
   - Run scrapers to generate price changes
   - Check if triggers are properly installed
   - Verify database permissions

2. **"Error fetching price history"**
   - Check Supabase credentials
   - Verify API endpoint is accessible
   - Check browser console for errors

3. **"Chart not rendering"**
   - Ensure Chart.js dependencies are installed
   - Check for JavaScript errors in console
   - Verify data format from API

### Debug Commands

```bash
# Test database connection
python test_price_history.py

# Check API endpoint
curl http://localhost:3000/api/priceHistory?productId=your_product_id

# Verify dependencies
npm list chart.js react-chartjs-2
```

## 📈 Next Steps

1. **Run Scrapers**: Generate price history data
2. **Test Visualization**: Use the demo page
3. **Customize**: Modify charts and styling
4. **Deploy**: Add to your production environment

## 🎯 Benefits

- **Price Transparency**: See how prices change over time
- **Market Analysis**: Identify price trends and patterns
- **User Experience**: Interactive visualizations
- **Data Insights**: Historical price data for decision making

---

**Note**: The Bing API setup is optional. The system works with fallback image sources, but Bing API will provide better product images. 