"""
Test script for MT5 data fetcher.
"""
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

# Path hack for direct script execution
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from drl_forex_trading_internal.utils.logger import setup_logging
from drl_forex_trading_internal.data.fetcher import MT5Fetcher

# Configure logging
logger = setup_logging("tests.mt5_fetcher")

def test_mt5_fetcher():
    """Test MT5 data fetcher functionality."""
    try:
        # Create fetcher
        fetcher = MT5Fetcher()
        
        # Initialize MT5 connection
        if not fetcher.initialize():
            logger.error("Failed to initialize MT5 connection")
            return False
        
        # Get available symbols
        symbols = fetcher.get_available_symbols()
        logger.info(f"Found {len(symbols)} symbols in MT5")
        if symbols:
            logger.info(f"Sample symbols: {symbols[:5]}")
        
        # Test fetching EURUSD data
        symbol = "EURUSD"
        if symbol not in symbols:
            logger.warning(f"{symbol} not found in available symbols")
            # Try to find a different currency pair
            forex_pairs = [s for s in symbols if len(s) == 6 and s.isalpha()]
            if forex_pairs:
                symbol = forex_pairs[0]
                logger.info(f"Using {symbol} for testing instead")
            else:
                logger.error("No suitable forex pairs found for testing")
                return False
        
        # Fetch last 100 M1 candles
        logger.info(f"Fetching last 100 M1 candles for {symbol}")
        df_recent = fetcher.fetch_ohlcv(symbol, "M1", count=100)
        if df_recent is None or len(df_recent) == 0:
            logger.error(f"Failed to fetch recent data for {symbol}")
            return False
            
        logger.info(f"Recent data sample:\n{df_recent.head()}")
        
        # Fetch historical data for a specific date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)  # One week of data
        
        logger.info(f"Fetching M15 data for {symbol} from {start_date} to {end_date}")
        df_range = fetcher.fetch_ohlcv(symbol, "M15", start_date, end_date)
        if df_range is None:
            logger.error(f"Failed to fetch date range data for {symbol}")
            return False
            
        logger.info(f"Retrieved {len(df_range)} M15 candles for date range")
        logger.info(f"Date range data sample:\n{df_range.head()}")
        
        # Test getting trading hours
        trading_hours = fetcher.get_trading_hours(symbol)
        logger.info(f"Trading hours for {symbol}: {trading_hours}")
        
        # Shutdown MT5
        fetcher.shutdown()
        
        logger.info("MT5 fetcher test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"MT5 fetcher test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    test_mt5_fetcher()