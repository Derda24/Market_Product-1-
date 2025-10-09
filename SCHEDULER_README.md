# Automated Scraper Scheduler

This scheduler automatically runs all your scrapers at scheduled intervals, so you don't have to manually start them.

## How It Works

The scheduler runs in the background and automatically executes your scrapers at these times:
- **Daily at 2:00 AM**: Runs all scrapers to collect fresh daily data
- **Weekly on Sunday at 3:00 AM**: Runs all scrapers for comprehensive weekly data

## Setup

1. **Install the required dependency:**
   ```bash
   pip install schedule
   ```

2. **Start the scheduler:**
   - **Windows**: Double-click `start_scheduler.bat`
   - **Command line**: `python scheduler.py`

## What Happens When It Runs

1. **Sequential Execution**: Runs each scraper one by one (not all at once)
2. **Error Handling**: If one scraper fails, others continue running
3. **Logging**: All activity is logged to `scheduler.log`
4. **Timeout Protection**: Each scraper has a 30-minute timeout
5. **Rate Limiting**: 2-minute pause between scrapers to be respectful

## Available Scrapers

The scheduler will run these scrapers:
- Aldi
- Alcampo
- Bonarea
- Bonpreu
- Caprabo
- Carrefour
- Condisline
- Consum
- Dia
- El Corte Inglés
- Eroski
- Lidl
- Mercadona

## Monitoring

- **Logs**: Check `scheduler.log` for detailed activity
- **Console**: See real-time status in the terminal
- **Database**: Check your Supabase database for new products

## Customization

You can modify the schedule in `scheduler.py`:

```python
# Change daily time
schedule.every().day.at("14:00").do(run_daily_scraping)  # 2 PM instead of 2 AM

# Add more frequent runs
schedule.every(6).hours.do(run_all_scrapers)  # Every 6 hours

# Remove weekly run
# schedule.every().sunday.at("03:00").do(run_weekly_scraping)  # Comment out
```

## Testing

To test the scheduler with just a few scrapers, uncomment this line in `scheduler.py`:
```python
schedule.every(5).minutes.do(run_test_scraping)  # Remove # to enable
```

## Stopping the Scheduler

- Press `Ctrl+C` in the terminal
- Close the terminal window

## Benefits

✅ **Consistent Data Collection**: Never miss a day of scraping
✅ **Time Saving**: No manual intervention needed
✅ **Better Price Tracking**: Regular data for price comparison
✅ **Error Recovery**: Failed scrapers don't stop others
✅ **Logging**: Track what's working and what's not

## Troubleshooting

- **Scraper not found**: Check that all scraper files exist in the `scraper/` folder
- **Timeout errors**: Some websites may be slow, increase timeout in `scheduler.py`
- **Database errors**: Check your Supabase connection and schema
- **Memory issues**: The scheduler uses minimal memory, but monitor system resources

## Next Steps

1. **Test the scheduler**: Run it for a few hours to see how it works
2. **Adjust timing**: Modify the schedule based on your needs
3. **Monitor performance**: Check which scrapers work best
4. **Scale up**: Add more scrapers or increase frequency as needed 