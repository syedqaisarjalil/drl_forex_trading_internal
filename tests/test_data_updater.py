"""
Test script for data updater.
"""
import time
from datetime import datetime, timedelta

# Import utilities
from drl_forex_trading_internal.utils.logger import setup_logging
from drl_forex_trading_internal.db import init_db

# Import data modules
from drl_forex_trading_internal.data.fetcher import MT5Fetcher
from drl_forex_trading_internal.data.database import DataManager
from drl_forex_trading_internal.data.updater import DataUpdater

# Configure logging
logger = setup_logging("tests.data_updater")

def test_data_updater():
    """Test data updater functionality."""
    try:
        # Initialize database
        init_db()
        
        # Create data manager for checking results
        data_manager = DataManager()
        
        # Create data updater
        updater = DataUpdater()
        
        # Initialize updater (connects to MT5)
        if not updater.initialize():
            logger.error("Failed to initialize updater (MT5 connection)")
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
            
        # Test updating latest data
        logger.info(f"Testing update_latest_data for {symbol}...")
        latest_success = updater.update_latest_data(
            symbol,
            last_n_candles=500  # Smaller number for testing
        )
        
        if not latest_success:
            logger.error(f"Failed to update latest data for {symbol}")
        else:
            logger.info(f"Successfully updated latest data for {symbol}")
            
            # Check the updated data
            df = data_manager.get_price_data(symbol, "1m", limit=5)
            if df is not None:
                logger.info(f"Latest 1-minute data:\n{df}")
            else:
                logger.warning("No 1-minute data found")
        
        # Test gap filling (create a test gap first)
        # This is just for testing - in real usage, gaps would be real missing data
        logger.info(f"Testing gap filling for {symbol}...")
        
        # Get the current data range
        recent_df = data_manager.get_price_data(symbol, "1m", limit=1000)
        if recent_df is not None and not recent_df.empty:
            # Calculate a gap period (1 day ago, 1 hour gap)
            # In a real scenario, gaps would be detected automatically
            gap_end = recent_df.index.min() - timedelta(days=1)
            gap_start = gap_end - timedelta(hours=1)
            
            logger.info(f"Testing gap filling for period: {gap_start} to {gap_end}")
            
            # First check if data exists for this period
            test_df = data_manager.get_price_data(
                symbol, "1m", start_date=gap_start, end_date=gap_end
            )
            
            if test_df is not None and not test_df.empty:
                logger.info(f"Data already exists for test gap period ({len(test_df)} candles)")
            else:
                logger.info("No data found for test gap period - attempting to fill")
                
                # Try to fill the gap
                fill_success = updater.fill_data_gaps(
                    symbol,
                    timeframe="1m",
                    max_gap_days=2  # Small value for testing
                )
                
                if fill_success:
                    # Check if data was filled
                    filled_df = data_manager.get_price_data(
                        symbol, "1m", start_date=gap_start, end_date=gap_end
                    )
                    
                    if filled_df is not None and not filled_df.empty:
                        logger.info(f"Successfully filled gap with {len(filled_df)} candles")
                    else:
                        logger.warning("Gap fill reported success but no data found")
                else:
                    logger.warning("Gap filling returned failure status")
        
        # Test full update for all pairs
        logger.info("Testing update_all_pairs...")
        
        # Only process a few pairs for the test
        test_pairs = list(pair_map.keys())[:2]  # First 2 pairs
        logger.info(f"Testing with pairs: {test_pairs}")
        
        # Override pair_map for testing
        data_manager.data_config["currency_pairs"] = [
            pair for pair in data_manager.data_config["currency_pairs"]
            if pair["name"] in test_pairs
        ]
        
        # Run the update
        all_results = updater.update_all_pairs(
            update_latest=True,
            fill_gaps=True,
            max_workers=2  # Use fewer workers for testing
        )
        
        logger.info(f"Full update results: {all_results}")
        
        # Check the results
        if all(all_results.values()):
            logger.info("All pairs updated successfully")
        else:
            failed_pairs = [pair for pair, success in all_results.items() if not success]
            logger.warning(f"Update failed for some pairs: {failed_pairs}")
        
        # Test scheduled update (just simulate it - don't actually wait)
        logger.info("Testing run_scheduled_update...")
        
        # Mock the update_all_pairs method to avoid duplicate processing
        original_update_all_pairs = updater.update_all_pairs
        try:
            # Replace with a mock that just returns success
            updater.update_all_pairs = lambda **kwargs: {pair: True for pair in test_pairs}
            
            # Run the scheduled update
            updater.run_scheduled_update()
            logger.info("Scheduled update simulation completed")
            
        finally:
            # Restore the original method
            updater.update_all_pairs = original_update_all_pairs
        
        # Test shutdown
        updater.shutdown()
        logger.info("Data updater test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Data updater test failed: {e}", exc_info=True)
        return False
        
    finally:
        # Always try to shutdown MT5 if something goes wrong
        try:
            updater.shutdown()
        except:
            pass

if __name__ == "__main__":
    test_data_updater()