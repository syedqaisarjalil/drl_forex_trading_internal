"""
Resampler module for the Forex AI Trading system.
Handles resampling of price data from one timeframe to another.
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, List

from drl_forex_trading_internal.utils.logger import get_logger
from drl_forex_trading_internal.utils.config import load_config
from drl_forex_trading_internal.data.database import DataManager

# Create logger
logger = get_logger("data.resampler")

class DataResampler:
    """
    Class to handle resampling of price data.
    """
    
    # Map of timeframe strings to pandas resample rule
    TIMEFRAME_MAP = {
        "1m": "1T",   # 1 minute
        "5m": "5T",   # 5 minutes
        "15m": "15T", # 15 minutes
        "30m": "30T", # 30 minutes
        "1h": "1H",   # 1 hour
        "4h": "4H",   # 4 hours
        "1d": "1D",   # 1 day
    }
    
    def __init__(self):
        """Initialize the resampler."""
        self.config = load_config()
        self.data_manager = DataManager()
    
    def resample_data(
        self,
        data: pd.DataFrame,
        source_timeframe: str,
        target_timeframe: str
    ) -> Optional[pd.DataFrame]:
        """
        Resample data from one timeframe to another.
        
        Args:
            data: DataFrame with OHLCV data
            source_timeframe: Source timeframe string (e.g., "1m")
            target_timeframe: Target timeframe string (e.g., "1h")
            
        Returns:
            Resampled DataFrame or None if error
        """
        if data is None or len(data) == 0:
            logger.warning("No data to resample")
            return None
            
        try:
            # Ensure index is datetime
            if data.index.name != 'time':
                if 'time' in data.columns:
                    data = data.set_index('time')
                else:
                    logger.error("Data does not have a time column or index")
                    return None
            
            # Check timeframes
            if source_timeframe not in self.TIMEFRAME_MAP:
                logger.error(f"Invalid source timeframe: {source_timeframe}")
                return None
                
            if target_timeframe not in self.TIMEFRAME_MAP:
                logger.error(f"Invalid target timeframe: {target_timeframe}")
                return None
                
            # If source and target are the same, just return the data
            if source_timeframe == target_timeframe:
                return data
                
            # Get resample rule
            resample_rule = self.TIMEFRAME_MAP[target_timeframe]
            
            # Resample data
            resampled = data.resample(resample_rule).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })
            
            # Drop rows with NaN values
            resampled = resampled.dropna()
            
            logger.info(f"Resampled data from {source_timeframe} to {target_timeframe}")
            logger.info(f"Original data: {len(data)} rows, Resampled data: {len(resampled)} rows")
            
            return resampled
            
        except Exception as e:
            logger.error(f"Error resampling data: {e}", exc_info=True)
            return None
    
    def get_resampled_price_data(
        self,
        pair_name: str,
        target_timeframe: str,
        start_date: Optional[pd.Timestamp] = None,
        end_date: Optional[pd.Timestamp] = None,
        store_result: bool = False
    ) -> Optional[pd.DataFrame]:
        """
        Get resampled price data for a currency pair.
        
        Args:
            pair_name: Currency pair name
            target_timeframe: Target timeframe string
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            store_result: Whether to store the resampled data
            
        Returns:
            Resampled DataFrame or None if error
        """
        try:
            # Check if the resampled data already exists in the database
            if self.data_manager._ensure_price_table(pair_name, target_timeframe) is not None:
                # Try to get data from the database first
                df = self.data_manager.get_price_data(pair_name, target_timeframe, start_date, end_date)
                if df is not None and not df.empty:
                    logger.info(f"Retrieved resampled {target_timeframe} data for {pair_name} from database")
                    return df
            
            # If we don't have the data in the database, get the 1-minute data and resample it
            m1_data = self.data_manager.get_price_data(pair_name, "1m", start_date, end_date)
            if m1_data is None or m1_data.empty:
                logger.warning(f"No 1-minute data available for {pair_name}")
                return None
                
            # Resample the data
            resampled = self.resample_data(m1_data, "1m", target_timeframe)
            if resampled is None:
                logger.error(f"Failed to resample data for {pair_name}")
                return None
                
            # Store the resampled data if requested
            if store_result:
                self.data_manager.store_price_data(pair_name, resampled, target_timeframe)
                logger.info(f"Stored resampled {target_timeframe} data for {pair_name} in database")
                
            return resampled
            
        except Exception as e:
            logger.error(f"Error getting resampled data for {pair_name}: {e}", exc_info=True)
            return None
    
    def resample_latest_data(
        self,
        pair_name: str,
        target_timeframes: List[str],
        lookback_days: int = 30
    ) -> Dict[str, bool]:
        """
        Resample the latest data for a currency pair to multiple timeframes.
        
        Args:
            pair_name: Currency pair name
            target_timeframes: List of target timeframe strings
            lookback_days: Number of days to look back for data
            
        Returns:
            Dictionary mapping timeframes to success status
        """
        results = {}
        
        try:
            # Calculate the start date
            end_date = pd.Timestamp.now()
            start_date = end_date - pd.Timedelta(days=lookback_days)
            
            # Get the raw 1-minute data
            m1_data = self.data_manager.get_price_data(pair_name, "1m", start_date, end_date)
            if m1_data is None or m1_data.empty:
                logger.warning(f"No 1-minute data available for {pair_name}")
                return {tf: False for tf in target_timeframes}
                
            # Resample to each target timeframe
            for tf in target_timeframes:
                if tf == "1m":
                    # No need to resample 1-minute data
                    results[tf] = True
                    continue
                    
                # Resample and store
                resampled = self.resample_data(m1_data, "1m", tf)
                if resampled is not None:
                    success = self.data_manager.store_price_data(pair_name, resampled, tf)
                    results[tf] = success
                else:
                    results[tf] = False
                    
            logger.info(f"Resampled latest data for {pair_name}: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error resampling latest data for {pair_name}: {e}", exc_info=True)
            return {tf: False for tf in target_timeframes}