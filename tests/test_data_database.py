"""
Test script for data database operations.
"""
import pandas as pd
from datetime import datetime, timedelta

# Import utilities
from drl_forex_trading_internal.utils.logger import setup_logging
from drl_forex_trading_internal.db import init_db

# Import data modules
from drl_forex_trading_internal.data.fetcher import MT5Fetcher
from drl_forex_trading_internal.data.database import DataManager

# Configure logging
logger = setup_logging("tests.data_database")

def test_data_database():
    """Test data database operations."""
    try:
        # Initialize database tables
        init_db()
        
        # Create data manager
        data_manager = DataManager()
        
        # Ensure currency pairs exist in database
        logger.info("Ensuring currency pairs exist in database...")
        pair_map = data_manager.ensure_currency_pairs()
        logger.info(f"Currency pairs in database: {pair_map}")
        
        if not pair_map:
            logger.error("No currency pairs found in configuration")
            return False
            
        # Test with EURUSD
        symbol = "EURUSD"
        if symbol not in pair_map:
            logger.warning(f"{symbol} not found in configured pairs")
            # Use the first available pair
            symbol = next(iter(pair_map.keys()))
            logger.info(f"Using {symbol} for testing instead")
            
        # Fetch data from MT5
        logger.info(f"Fetching data for {symbol} from MT5...")
        fetcher = MT5Fetcher()
        if not fetcher.initialize():
            logger.error("Failed to initialize MT5 connection")
            return False
            
        # Fetch recent data (last 100 candles)
        df = fetcher.fetch_ohlcv(symbol, "M1", count=100)
        if df is None or len(df) == 0:
            logger.error(f"Failed to fetch data for {symbol}")
            return False
            
        logger.info(f"Fetched {len(df)} candles for {symbol}")
        
        # Store data in per-pair database table
        logger.info(f"Storing data for {symbol} in database (individual table)...")
        # Use timeframe "1m" for M1 data
        success = data_manager.store_price_data(symbol, df, timeframe="1m")
        if not success:
            logger.error(f"Failed to store data for {symbol}")
            return False
            
        # Retrieve data from per-pair database table
        logger.info(f"Retrieving data for {symbol} from database...")
        db_df = data_manager.get_price_data(symbol, timeframe="1m", limit=10)
        if db_df is None:
            logger.error(f"Failed to retrieve data for {symbol}")
            return False
            
        logger.info(f"Retrieved {len(db_df)} records for {symbol}")
        logger.info(f"Sample data:\n{db_df.head()}")
        
        # Find data gaps
        logger.info(f"Finding data gaps for {symbol}...")
        gaps = data_manager.find_data_gaps(symbol, timeframe="1m")
        logger.info(f"Found {len(gaps)} gaps for {symbol}")
        
        # Get data coverage
        logger.info(f"Getting data coverage for {symbol}...")
        coverage = data_manager.get_data_coverage(symbol, timeframe="1m")
        logger.info(f"Coverage information: {coverage}")
        
        # Shut down MT5
        fetcher.shutdown()
        
        logger.info("Data database test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Data database test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    test_data_database()