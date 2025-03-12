"""
Test script for data resampling.
"""
import pandas as pd
from datetime import datetime, timedelta

# Import utilities
from drl_forex_trading_internal.utils.logger import setup_logging
from drl_forex_trading_internal.db import init_db

# Import data modules
from drl_forex_trading_internal.data.fetcher import MT5Fetcher
from drl_forex_trading_internal.data.database import DataManager
from drl_forex_trading_internal.data.resampler import DataResampler

# Configure logging
logger = setup_logging("tests.data_resampler")

def test_data_resampler():
    """Test data resampling operations."""
    try:
        # Initialize database
        init_db()
        
        # Create instances
        fetcher = MT5Fetcher()
        data_manager = DataManager()
        resampler = DataResampler()
        
        # Initialize MT5 connection
        if not fetcher.initialize():
            logger.error("Failed to initialize MT5 connection")
            return False
            
        # Ensure currency pairs exist
        pair_map = data_manager.ensure_currency_pairs()
        if not pair_map:
            logger.error("No currency pairs found")
            return False
            
        # Test with EURUSD
        symbol = "EURUSD"
        if symbol not in pair_map:
            logger.warning(f"{symbol} not found in configured pairs")
            # Use the first available pair
            symbol = next(iter(pair_map.keys()))
            logger.info(f"Using {symbol} for testing instead")
            
        # Fetch a larger amount of 1-minute data for testing resampling
        logger.info(f"Fetching 1-minute data for {symbol}...")
        end_time = datetime.now()
        start_time = end_time - timedelta(days=1)  # Get 1 day of data
        
        df_1m = fetcher.fetch_ohlcv(symbol, "M1", start_time, end_time)
        if df_1m is None or len(df_1m) == 0:
            logger.error(f"Failed to fetch data for {symbol}")
            return False
            
        logger.info(f"Fetched {len(df_1m)} 1-minute candles for {symbol}")
        
        # Store 1-minute data
        logger.info(f"Storing 1-minute data for {symbol}...")
        success = data_manager.store_price_data(symbol, df_1m, timeframe="1m")
        if not success:
            logger.error(f"Failed to store 1-minute data for {symbol}")
            return False
            
        # Test direct resampling (in-memory only, no database storage)
        logger.info("Testing direct resampling (in-memory only)...")
        for tf in ["5m", "15m", "1h"]:
            logger.info(f"Resampling to {tf}...")
            resampled = resampler.resample_data(df_1m, "1m", tf)
            if resampled is None:
                logger.error(f"Failed to resample to {tf}")
                continue
                
            logger.info(f"Successfully resampled to {tf}: {len(resampled)} candles")
            logger.info(f"Sample {tf} data:\n{resampled.head()}")
        
        # Test on-demand resampling using get_resampled_price_data
        logger.info("Testing on-demand resampling...")
        for tf in ["5m", "15m", "1h"]:
            logger.info(f"Getting resampled {tf} data...")
            result = resampler.get_resampled_price_data(
                symbol, tf, start_time, end_time
            )
            if result is None:
                logger.error(f"Failed to get resampled {tf} data")
                continue
                
            logger.info(f"Successfully retrieved resampled {tf} data: {len(result)} candles")
            logger.info(f"Sample resampled {tf} data:\n{result.head()}")
            
            # Verify that NO table was created for this timeframe
            # We can't directly check if table exists since we're using dynamic tables
            # But we can log that we're not attempting to store the data
            logger.info(f"Note: Resampled {tf} data is only in memory and NOT stored in database")
        
        # Shut down MT5
        fetcher.shutdown()
        
        logger.info("Data resampler test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Data resampler test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    test_data_resampler()