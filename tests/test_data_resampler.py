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
            
        # Test direct resampling
        logger.info("Testing direct resampling...")
        for tf in ["5m", "15m", "1h"]:
            logger.info(f"Resampling to {tf}...")
            resampled = resampler.resample_data(df_1m, "1m", tf)
            if resampled is None:
                logger.error(f"Failed to resample to {tf}")
                continue
                
            logger.info(f"Successfully resampled to {tf}: {len(resampled)} candles")
            logger.info(f"Sample {tf} data:\n{resampled.head()}")
        
        # Test database-based resampling and storage
        logger.info("Testing database resampling with storage...")
        for tf in ["5m", "15m", "1h"]:
            logger.info(f"Getting and storing resampled {tf} data...")
            result = resampler.get_resampled_price_data(
                symbol, tf, start_time, end_time, store_result=True
            )
            if result is None:
                logger.error(f"Failed to get resampled {tf} data")
                continue
                
            logger.info(f"Successfully retrieved and stored {tf} data: {len(result)} candles")
            
            # Verify the data was stored by retrieving it directly
            stored_df = data_manager.get_price_data(symbol, tf, start_time, end_time)
            if stored_df is None or stored_df.empty:
                logger.error(f"Failed to retrieve stored {tf} data")
                continue
                
            logger.info(f"Verified {tf} data storage: {len(stored_df)} candles")
        
        # Test bulk resampling of latest data
        logger.info("Testing bulk resampling of latest data...")
        timeframes = ["5m", "15m", "30m", "1h", "4h"]
        bulk_results = resampler.resample_latest_data(symbol, timeframes, lookback_days=1)
        logger.info(f"Bulk resampling results: {bulk_results}")
        
        # Verify bulk resampling results
        for tf, success in bulk_results.items():
            if not success:
                logger.warning(f"Bulk resampling to {tf} failed")
                continue
                
            stored_df = data_manager.get_price_data(symbol, tf, limit=5)
            if stored_df is None or stored_df.empty:
                logger.error(f"Failed to retrieve bulk resampled {tf} data")
                continue
                
            logger.info(f"Verified bulk resampled {tf} data: {len(stored_df)} candles shown")
            logger.info(f"Sample bulk resampled {tf} data:\n{stored_df}")
        
        # Shut down MT5
        fetcher.shutdown()
        
        logger.info("Data resampler test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Data resampler test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    test_data_resampler()