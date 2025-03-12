"""
MT5 data fetcher module for the Forex AI Trading system.
Responsible for retrieving historical price data from MetaTrader 5.
"""
import datetime
from typing import List, Dict, Optional, Union, Tuple
import pandas as pd
import numpy as np
import MetaTrader5 as mt5
from pathlib import Path

from drl_forex_trading_internal.utils.logger import get_logger
from drl_forex_trading_internal.utils.config import load_config

# Create logger
logger = get_logger("data.fetcher")

# MT5 timeframe mapping
TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1
}

class MT5Fetcher:
    """
    Class to fetch historical price data from MetaTrader 5.
    """
    
    def __init__(self):
        """Initialize the MT5 fetcher."""
        self.config = load_config()
        self.mt5_config = self.config["mt5"]
        self.data_config = self.config["data"]
        self.is_initialized = False
        
    def initialize(self) -> bool:
        """
        Initialize connection to MetaTrader 5.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if self.is_initialized:
            return True
            
        # Check if MT5 is already initialized
        if not mt5.terminal_info():
            # Initialize MT5 connection
            init_result = mt5.initialize(
                login=self.mt5_config["login"],
                password=self.mt5_config["password"],
                server=self.mt5_config["server"],
                timeout=self.mt5_config["timeout"]
            )
            
            if not init_result:
                error = mt5.last_error()
                logger.error(f"Failed to initialize MT5: {error}")
                return False
                
            logger.info(f"MT5 initialized successfully. Connected to {self.mt5_config['server']}")
        else:
            logger.info("MT5 already initialized")
            
        self.is_initialized = True
        return True
    
    def shutdown(self):
        """Shutdown MT5 connection."""
        if self.is_initialized:
            mt5.shutdown()
            self.is_initialized = False
            logger.info("MT5 connection closed")
    
    def check_symbol_available(self, symbol: str) -> bool:
        """
        Check if a symbol is available in MT5.
        
        Args:
            symbol: Symbol name (e.g., "EURUSD")
            
        Returns:
            bool: True if symbol is available, False otherwise
        """
        if not self.is_initialized and not self.initialize():
            return False
            
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.warning(f"Symbol {symbol} not found in MT5")
            return False
            
        if not symbol_info.visible:
            logger.info(f"Symbol {symbol} is not visible, attempting to make it visible")
            mt5.symbol_select(symbol, True)
            
        return True
    
    def fetch_ohlcv(
        self, 
        symbol: str, 
        timeframe: str = "M1", 
        start_date: Optional[Union[datetime.datetime, str]] = None,
        end_date: Optional[Union[datetime.datetime, str]] = None,
        count: Optional[int] = None
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical OHLCV data for a symbol.
        
        Args:
            symbol: Symbol name (e.g., "EURUSD")
            timeframe: Timeframe string (e.g., "M1", "H1")
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            count: Number of candles to retrieve (used if start_date is None)
            
        Returns:
            pandas.DataFrame with OHLCV data or None if error
        """
        if not self.is_initialized and not self.initialize():
            return None
            
        # Check symbol availability
        if not self.check_symbol_available(symbol):
            return None
            
        # Convert timeframe string to MT5 constant
        if timeframe not in TIMEFRAME_MAP:
            logger.error(f"Invalid timeframe: {timeframe}. Valid options: {list(TIMEFRAME_MAP.keys())}")
            return None
            
        mt5_timeframe = TIMEFRAME_MAP[timeframe]
        
        # Process dates
        if start_date is None:
            if count is None:
                # Default to the starting date in config if none provided
                start_date_str = self.data_config["start_date"]
                start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
            else:
                # If count is provided but no dates, get the most recent data
                rate_args = {
                    "symbol": symbol,
                    "timeframe": mt5_timeframe,
                    "count": count
                }
        else:
            # Convert string date to datetime if needed
            if isinstance(start_date, str):
                start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                
            if end_date is None:
                end_date = datetime.datetime.now()
            elif isinstance(end_date, str):
                end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
                
            rate_args = {
                "symbol": symbol,
                "timeframe": mt5_timeframe,
                "from_date": start_date,
                "to_date": end_date
            }
        
        # Handle max candles per request
        max_candles = self.data_config["update"]["max_candles_per_request"]
        
        if "count" in rate_args and rate_args["count"] > max_candles:
            logger.warning(f"Requested {rate_args['count']} candles, but max is {max_candles}. Using chunked requests.")
            return self._fetch_large_ohlcv(symbol, mt5_timeframe, rate_args["count"])
            
        # Fetch data from MT5
        try:
            logger.info(f"Fetching {symbol} {timeframe} data with args: {rate_args}")
            
            # Choose the appropriate MT5 function based on provided arguments
            if "from_date" in rate_args and "to_date" in rate_args:
                # Date range query
                rates = mt5.copy_rates_range(symbol, mt5_timeframe, 
                                           rate_args["from_date"], 
                                           rate_args["to_date"])
            elif "from_date" in rate_args:
                # From date to now query
                rates = mt5.copy_rates_from(symbol, mt5_timeframe, 
                                          rate_args["from_date"])
            elif "count" in rate_args:
                # Count-based query
                rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 
                                              0, rate_args["count"])
            else:
                logger.error("Invalid arguments for MT5 data request")
                return None
            
            if rates is None or len(rates) == 0:
                logger.warning(f"No data returned for {symbol} {timeframe}")
                return None
                
            # Convert to pandas DataFrame
            df = self._rates_to_dataframe(rates)
            logger.info(f"Retrieved {len(df)} bars for {symbol} {timeframe}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching {symbol} {timeframe} data: {e}", exc_info=True)
            return None
            
    def _fetch_large_ohlcv(self, symbol: str, mt5_timeframe: int, count: int) -> Optional[pd.DataFrame]:
        """
        Fetch large amount of OHLCV data by breaking into chunks.
        
        Args:
            symbol: Symbol name
            mt5_timeframe: MT5 timeframe constant
            count: Total number of candles to retrieve
            
        Returns:
            pandas.DataFrame with OHLCV data or None if error
        """
        max_candles = self.data_config["update"]["max_candles_per_request"]
        chunks = []
        remaining = count
        position = 0
        
        while remaining > 0:
            chunk_size = min(remaining, max_candles)
            logger.info(f"Fetching chunk of {chunk_size} candles from position {position}")
            
            try:
                rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, position, chunk_size)
                if rates is None or len(rates) == 0:
                    break
                    
                chunks.append(self._rates_to_dataframe(rates))
                position += len(rates)
                remaining -= len(rates)
                
                # If we got fewer bars than requested, we've reached the end
                if len(rates) < chunk_size:
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching chunk at position {position}: {e}", exc_info=True)
                break
                
        if not chunks:
            return None
            
        # Combine all chunks and sort by time
        result = pd.concat(chunks).sort_values("time")
        
        # Remove duplicates if any
        result = result.drop_duplicates(subset=["time"])
        
        logger.info(f"Retrieved total of {len(result)} bars for {symbol}")
        return result
        
    def _rates_to_dataframe(self, rates) -> pd.DataFrame:
        """
        Convert MT5 rates to pandas DataFrame with proper columns.
        
        Args:
            rates: MT5 rates array
            
        Returns:
            pandas.DataFrame with formatted OHLCV data
        """
        df = pd.DataFrame(rates)
        
        # Convert time column from Unix timestamp to datetime
        df["time"] = pd.to_datetime(df["time"], unit="s")
        
        # Rename columns to standard OHLCV names and select only needed columns
        df = df[["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]]
        df = df.rename(columns={
            "tick_volume": "volume",
            "real_volume": "real_volume"
        })
        
        # Calculate spread in pips
        # For pairs ending with JPY, a pip is 0.01, for others it's 0.0001
        # This is a simplification and may need adjustment for some exotic pairs
        # df["spread_pips"] = df["spread"] * 0.1
        
        # Set time as index
        df.set_index("time", inplace=True)
        
        return df
        
    def get_available_symbols(self) -> List[str]:
        """
        Get list of all available symbols in MT5.
        
        Returns:
            List of symbol names
        """
        if not self.is_initialized and not self.initialize():
            return []
            
        symbols = mt5.symbols_get()
        if symbols is None:
            logger.warning("Failed to get symbol list from MT5")
            return []
            
        return [symbol.name for symbol in symbols]
        
    def get_trading_hours(self, symbol: str) -> Dict:
        """
        Get trading hours for a symbol.
        
        Args:
            symbol: Symbol name
            
        Returns:
            Dictionary with trading hours information or empty dict if error
        """
        if not self.is_initialized and not self.initialize():
            return {}
            
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.warning(f"Symbol {symbol} not found in MT5")
            return {}
        
        # MT5 Python API structure is different than expected
        # Let's extract what we can from the symbol info
        try:
            # Get session info from MT5
            sessions_info = {}
            
            # Check if session properties are available
            if hasattr(symbol_info, 'session_open') and hasattr(symbol_info, 'session_close'):
                # Add basic session info
                sessions_info = {
                    "trade_sessions": "24h" if symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL else "Limited"
                }
            
            timezone = getattr(symbol_info, 'time_zone', 0)
            timezone_name = f"GMT+{timezone//3600}" if timezone >= 0 else f"GMT{timezone//3600}"
            
            return {
                "timezone": timezone_name,
                "sessions": sessions_info,
                "trade_mode": symbol_info.trade_mode,
                "trade_stops_level": symbol_info.trade_stops_level,
                "trade_freeze_level": symbol_info.trade_freeze_level
            }
            
        except Exception as e:
            logger.error(f"Error getting trading hours for {symbol}: {e}", exc_info=True)
            return {}
        
    def _extract_sessions(self, opens, closes, day_index: int) -> List[Dict]:
        """
        Extract session times for a specific day.
        
        Args:
            opens: Array of session open times
            closes: Array of session close times
            day_index: Index of day (0 = Monday, 6 = Sunday)
            
        Returns:
            List of session dictionaries with open and close times
        """
        sessions = []
        
        if not opens or not closes:
            return sessions
            
        for i in range(len(opens) // 2):  # MT5 stores 2 values per day
            open_time = opens[day_index * 2 + i]
            close_time = closes[day_index * 2 + i]
            
            # Skip empty sessions
            if open_time == close_time == 0:
                continue
                
            # Convert from minutes since midnight to HH:MM format
            open_str = f"{open_time // 60:02d}:{open_time % 60:02d}"
            close_str = f"{close_time // 60:02d}:{close_time % 60:02d}"
            
            sessions.append({
                "open": open_str,
                "close": close_str
            })
            
        return sessions