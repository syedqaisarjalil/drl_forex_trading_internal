# Forex AI Trading System: Data Module Documentation

## Overview

The Data Module is responsible for acquiring, storing, and managing Forex market data. It serves as the foundation for the entire trading system by ensuring that accurate and timely data is available for model training, backtesting, and live trading.

The module is designed with these key principles in mind:
- Store only 1-minute (M1) data to optimize storage efficiency
- Perform on-demand resampling for higher timeframes when requested
- Maintain data integrity through gap detection and filling
- Support automated updates via scheduled tasks

## Architecture

The Data Module consists of four main components:

1. **MT5 Fetcher**: Interfaces with MetaTrader 5 to retrieve historical and current market data
2. **Database Manager**: Handles storage and retrieval of price data in a PostgreSQL database
3. **Data Resampler**: Converts 1-minute data to higher timeframes as needed
4. **Data Updater**: Manages scheduled updates and gap filling operations

### Directory Structure

```
drl_forex_trading_internal/data/
├── __init__.py       # Package initialization
├── fetcher.py        # MT5 data acquisition
├── database.py       # Database operations
├── resampler.py      # Timeframe conversion
└── updater.py        # Scheduled data updates
```

## Component Details

### MT5 Fetcher (`fetcher.py`)

The MT5 Fetcher provides a robust interface to the MetaTrader 5 platform for retrieving historical price data.

#### Key Classes and Methods:

- **MT5Fetcher**
  - `initialize()`: Establishes connection to MT5
  - `fetch_ohlcv()`: Retrieves historical OHLCV data for a currency pair
  - `check_symbol_available()`: Verifies if a symbol exists in MT5
  - `get_available_symbols()`: Lists all available symbols
  - `get_trading_hours()`: Retrieves trading session information
  - `shutdown()`: Closes the MT5 connection

#### Usage Example:

```python
from drl_forex_trading_internal.data.fetcher import MT5Fetcher

# Create and initialize fetcher
fetcher = MT5Fetcher()
fetcher.initialize()

# Get 100 recent candles for EURUSD
df = fetcher.fetch_ohlcv("EURUSD", "M1", count=100)

# Get data for a specific date range
from datetime import datetime, timedelta
end_date = datetime.now()
start_date = end_date - timedelta(days=7)
df = fetcher.fetch_ohlcv("EURUSD", "M1", start_date, end_date)

# Always close connection when done
fetcher.shutdown()
```

### Database Manager (`database.py`)

The Database Manager handles all database operations for storing and retrieving price data. It implements a schema-based approach with separate tables for each currency pair.

#### Key Classes and Methods:

- **DataManager**
  - `ensure_currency_pairs()`: Creates or updates currency pair records
  - `store_price_data()`: Stores OHLCV data for a currency pair
  - `get_price_data()`: Retrieves price data from the database
  - `find_data_gaps()`: Identifies gaps in the time series data
  - `get_data_coverage()`: Calculates data completeness metrics

#### Database Schema:

- **currency_pairs**: Information about each currency pair
- **price_data.{pair_name}_1m**: Price data tables for each currency pair (e.g., `price_data.eurusd_1m`)

#### Usage Example:

```python
from drl_forex_trading_internal.data.database import DataManager

# Create data manager
data_manager = DataManager()

# Ensure currency pairs exist in database
pair_map = data_manager.ensure_currency_pairs()

# Store data in database
data_manager.store_price_data("EURUSD", df, timeframe="1m")

# Retrieve data from database
df = data_manager.get_price_data(
    "EURUSD", 
    timeframe="1m", 
    start_date="2023-01-01", 
    end_date="2023-01-31"
)

# Find gaps in data
gaps = data_manager.find_data_gaps("EURUSD", timeframe="1m")

# Get data coverage statistics
coverage = data_manager.get_data_coverage("EURUSD", timeframe="1m")
```

### Data Resampler (`resampler.py`)

The Data Resampler handles conversion of 1-minute data to higher timeframes on demand. It doesn't store resampled data in the database but instead performs conversions in memory when requested.

#### Key Classes and Methods:

- **DataResampler**
  - `resample_data()`: Converts data from one timeframe to another
  - `get_resampled_price_data()`: Retrieves 1m data and resamples it to the requested timeframe

#### Supported Timeframes:

- "1m": 1 minute
- "5m": 5 minutes
- "15m": 15 minutes
- "30m": 30 minutes
- "1h": 1 hour
- "4h": 4 hours
- "1d": 1 day

#### Usage Example:

```python
from drl_forex_trading_internal.data.resampler import DataResampler

# Create resampler
resampler = DataResampler()

# Get data in a different timeframe
df_1h = resampler.get_resampled_price_data(
    "EURUSD",
    target_timeframe="1h", 
    start_date="2023-01-01", 
    end_date="2023-01-31"
)

# Resample data directly (if you already have the data)
from datetime import datetime, timedelta
df_1m = data_manager.get_price_data("EURUSD", "1m")
df_4h = resampler.resample_data(df_1m, "1m", "4h")
```

### Data Updater (`updater.py`)

The Data Updater manages the process of keeping forex data current and complete. It handles fetching the latest data, filling gaps, and can be scheduled to run automatically.

#### Key Classes and Methods:

- **DataUpdater**
  - `update_latest_data()`: Fetches and stores the most recent data
  - `fill_data_gaps()`: Identifies and fills gaps in historical data
  - `update_all_pairs()`: Updates all configured currency pairs
  - `run_scheduled_update()`: Runs a complete update process with retries

#### Usage Example:

```python
from drl_forex_trading_internal.data.updater import DataUpdater

# Create and initialize updater
updater = DataUpdater()
updater.initialize()

try:
    # Update latest data for a specific pair
    updater.update_latest_data("EURUSD", last_n_candles=1000)
    
    # Fill gaps for a specific pair
    updater.fill_data_gaps("EURUSD", max_gap_days=30)
    
    # Update all pairs
    results = updater.update_all_pairs(
        update_latest=True, 
        fill_gaps=True
    )
    
    # Run a complete scheduled update
    updater.run_scheduled_update()
    
finally:
    # Always close the MT5 connection
    updater.shutdown()
```

## Configuration

The Data Module is configured via the `config/main.yml` file, which includes:

### MT5 Connection Settings:
```yaml
mt5:
  server: "MetaQuotes-Demo"
  login: 12345678
  password: "password"
  timeout: 60000
```

### Database Settings:
```yaml
database:
  host: "localhost"
  port: 5432
  name: "forex_ai_trading"
  user: "postgres"
  password: "postgres"
  pool_size: 5
  max_overflow: 10
```

### Data Settings:
```yaml
data:
  start_date: "2020-01-01"
  currency_pairs:
    - name: "EURUSD"
      description: "Euro vs US Dollar"
      pip_value: 0.0001
      spread_avg: 1.5
    # Other pairs...
  timeframes:
    - M1
    - M5
    - M15
    # Other timeframes...
  update:
    frequency: 60
    retry_attempts: 3
    retry_delay: 300
    max_candles_per_request: 1000
```

### Calendar Settings:
```yaml
calendar:
  weekend_trading: false
  forex_market_open:
    - day: 0
      time: "00:00"
    - day: 4
      time: "22:00"
  holidays:
    - "2023-01-01"
    - "2023-12-25"
```

## Scheduling Updates

For automated data updates, you can set up a scheduled task:

### Windows Task Scheduler:
1. Create a new Basic Task
2. Set the trigger (e.g., Daily at 1:00 AM)
3. Action: Start a program
4. Program/script: `python`
5. Arguments: `scripts/data_updater.py --full`
6. Start in: Your project directory

### Linux cron:
Add to crontab (`crontab -e`):
```
0 1 * * * cd /path/to/project && python scripts/data_updater.py --full
```

## Best Practices

1. **Always close MT5 connections**: Use try-finally blocks to ensure proper shutdown
2. **Handle currency pair updates**: Run `ensure_currency_pairs()` before operations
3. **Error handling**: Check return values from operations that might fail
4. **Data verification**: Use `get_data_coverage()` to monitor data completeness
5. **Performance**: For large data operations, consider using the parallel processing in `update_all_pairs()`

## Integrating with Other Modules

When other modules need price data:
1. They should request it by currency pair, timeframe, and date range
2. The Data Module will fetch the raw 1-minute data and resample it as needed
3. The resampled data is returned without being stored in the database

Example of how a model training module might request data:
```python
from drl_forex_trading_internal.data.resampler import DataResampler

def train_model(pair_name, timeframe, start_date, end_date):
    # Get resampled data for training
    resampler = DataResampler()
    training_data = resampler.get_resampled_price_data(
        pair_name, timeframe, start_date, end_date
    )
    
    # Process and use the data
    # ...
```

## Troubleshooting

1. **MT5 Connection Issues**:
   - Verify MT5 is running
   - Check credentials in config
   - Ensure symbol is available in your MT5 account

2. **Database Connection Issues**:
   - Verify PostgreSQL is running
   - Check database credentials
   - Ensure the database exists

3. **Missing Data**:
   - Use `find_data_gaps()` to identify missing periods
   - Use `fill_data_gaps()` to attempt recovery
   - Check MT5 data availability for the period

4. **Performance Issues**:
   - Adjust `max_candles_per_request` for large data fetches
   - Use `max_workers` parameter for parallel updates
   - Consider indexing strategies for your database

---
