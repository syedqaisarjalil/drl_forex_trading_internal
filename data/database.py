"""
Database operations for the forex data module.
Handles storing and retrieving OHLCV data.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union, Tuple
import sqlalchemy
from sqlalchemy import and_, or_, func, desc, asc, Table, Column, DateTime, Float, MetaData, Index
from sqlalchemy.sql import select, exists

from drl_forex_trading_internal.utils.logger import get_logger
from drl_forex_trading_internal.utils.config import load_config
from drl_forex_trading_internal.db import get_session, get_engine, CurrencyPair
from drl_forex_trading_internal.db.schema import create_price_table

# Create logger
logger = get_logger("data.database")

class DataManager:
    """
    Class to manage data storage and retrieval from the database.
    """
    
    def __init__(self):
        """Initialize the data manager."""
        self.config = load_config()
        self.data_config = self.config["data"]
        self.engine = get_engine()
        self.metadata = MetaData(schema='price_data')
        self.metadata.reflect(bind=self.engine)
        self.tables = {}  # Cache for table objects
        
    def ensure_currency_pairs(self) -> Dict[str, int]:
        """
        Ensure all configured currency pairs exist in the database.
        
        Returns:
            Dictionary mapping currency pair names to their IDs
        """
        pair_map = {}
        session = get_session()
        
        try:
            # Get all pairs from config
            config_pairs = self.data_config["currency_pairs"]
            
            for pair_config in config_pairs:
                pair_name = pair_config["name"]
                
                # Check if pair exists
                pair = session.query(CurrencyPair).filter_by(name=pair_name).first()
                
                if pair is None:
                    # Create new pair
                    pair = CurrencyPair(
                        name=pair_name,
                        description=pair_config.get("description", ""),
                        pip_value=pair_config.get("pip_value", 0.0001),
                        spread_avg=pair_config.get("spread_avg", 0)
                    )
                    session.add(pair)
                    session.commit()
                    logger.info(f"Created new currency pair: {pair_name}")
                else:
                    # Update existing pair if needed
                    updated = False
                    
                    if pair.description != pair_config.get("description", ""):
                        pair.description = pair_config.get("description", "")
                        updated = True
                        
                    if pair.pip_value != pair_config.get("pip_value", 0.0001):
                        pair.pip_value = pair_config.get("pip_value", 0.0001)
                        updated = True
                        
                    if pair.spread_avg != pair_config.get("spread_avg", 0):
                        pair.spread_avg = pair_config.get("spread_avg", 0)
                        updated = True
                        
                    if updated:
                        session.commit()
                        logger.info(f"Updated currency pair: {pair_name}")
                
                # Ensure price table exists for this pair
                table_name = f"{pair_name.lower()}_1m"
                if table_name not in self.metadata.tables:
                    self._ensure_price_table(pair_name)
                
                # Add to map
                pair_map[pair_name] = pair.id
            
            return pair_map
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error ensuring currency pairs: {e}", exc_info=True)
            return {}
            
        finally:
            session.close()
    
    def _ensure_price_table(self, pair_name: str, timeframe: str = "1m") -> Table:
        """
        Ensure a price table exists for a currency pair.
        
        Args:
            pair_name: Currency pair name
            timeframe: Timeframe string
            
        Returns:
            SQLAlchemy Table object
        """
        table_name = f"{pair_name.lower()}_{timeframe}"
        schema_table_name = f"price_data.{table_name}"
        
        # Check if table is already in our cache
        if table_name in self.tables:
            return self.tables[table_name]
        
        # Check if table exists in database
        insp = sqlalchemy.inspect(self.engine)
        if insp.has_table(table_name, schema='price_data'):
            # Table exists, get it from metadata
            table = Table(table_name, self.metadata, autoload_with=self.engine, schema='price_data')
            self.tables[table_name] = table
            return table
        
        # Table doesn't exist, create it
        logger.info(f"Creating price table for {pair_name} with timeframe {timeframe}")
        table = create_price_table(self.engine, pair_name, timeframe)
        self.tables[table_name] = table
        return table
    
    def store_price_data(self, pair_name: str, data: pd.DataFrame, timeframe: str = "1m") -> bool:
        """
        Store price data for a currency pair.
        
        Args:
            pair_name: Currency pair name
            data: DataFrame with OHLCV data
            timeframe: Timeframe string
            
        Returns:
            bool: True if successful, False otherwise
        """
        if data is None or len(data) == 0:
            logger.warning(f"No data to store for {pair_name}")
            return False
        
        try:
            # Get the price table for this pair
            table = self._ensure_price_table(pair_name, timeframe)
            
            # Reset index if time is the index
            if data.index.name == 'time':
                data = data.reset_index()
                
            # Ensure 'time' column exists
            if 'time' not in data.columns:
                logger.error(f"DataFrame does not have a 'time' column")
                return False
                
            # Get existing timestamps to avoid conflicts with primary key
            existing_times = set()
            
            # Check for existing timestamps in the table
            with self.engine.connect() as conn:
                min_time = data['time'].min()
                max_time = data['time'].max()
                
                # Use modern SQLAlchemy 2.0 style query
                query = select(table.c.timestamp).where(
                    and_(
                        table.c.timestamp >= min_time,
                        table.c.timestamp <= max_time
                    )
                )
                
                result = conn.execute(query)
                existing_times = {row[0] for row in result}
            
            # Count initial records
            initial_count = len(data)
            
            # Filter out existing timestamps
            if existing_times:
                data = data[~data['time'].isin(existing_times)]
                
            # Check if we have any new data
            if len(data) == 0:
                logger.info(f"No new data to store for {pair_name}")
                return True
                
            logger.info(f"Storing {len(data)} new records out of {initial_count} for {pair_name}")
                
            # Convert DataFrame to list of dictionaries for insertion
            records = []
            for _, row in data.iterrows():
                records.append({
                    'timestamp': row['time'],
                   'open': round(float(row['open']), 6),
                    'high': round(float(row['high']), 6),
                    'low': round(float(row['low']), 6),
                    'close': round(float(row['close']), 6),
                    'volume': float(row['volume'])
                })
                
            # Store in database
            with self.engine.begin() as conn:  # Use transaction
                conn.execute(table.insert(), records)
            
            logger.info(f"Successfully stored {len(records)} records for {pair_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing price data for {pair_name}: {e}", exc_info=True)
            return False
    
    def get_price_data(
        self,
        pair_name: str,
        timeframe: str = "1m",
        start_date: Optional[Union[datetime, str]] = None,
        end_date: Optional[Union[datetime, str]] = None,
        limit: Optional[int] = None
    ) -> Optional[pd.DataFrame]:
        """
        Get price data for a currency pair from the database.
        
        Args:
            pair_name: Currency pair name
            timeframe: Timeframe string
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            limit: Maximum number of records to retrieve
            
        Returns:
            DataFrame with OHLCV data or None if error or no data
        """
        try:
            # Get the price table for this pair
            table = self._ensure_price_table(pair_name, timeframe)
                
            # Process dates
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
                
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
                
            # Build query
            query = select(table)
            
            if start_date:
                query = query.where(table.c.timestamp >= start_date)
                
            if end_date:
                query = query.where(table.c.timestamp <= end_date)
                
            # Order by timestamp
            query = query.order_by(table.c.timestamp)
            
            # Apply limit if specified
            if limit:
                query = query.limit(limit)
                
            # Execute query
            with self.engine.connect() as conn:
                result = conn.execute(query)
                rows = result.fetchall()
            
            if not rows:
                logger.warning(f"No data found for {pair_name} in specified date range")
                return None
                
            # Convert to DataFrame
            df = pd.DataFrame(rows, columns=result.keys())
            df = df.rename(columns={'timestamp': 'time'})
            df.set_index('time', inplace=True)
            
            logger.info(f"Retrieved {len(df)} records for {pair_name}")
            return df
            
        except Exception as e:
            logger.error(f"Error retrieving price data for {pair_name}: {e}", exc_info=True)
            return None
    
    def find_data_gaps(self, pair_name: str, timeframe: str = "1m") -> List[Tuple[datetime, datetime]]:
        """
        Find gaps in the price data for a currency pair.
        
        Args:
            pair_name: Currency pair name
            timeframe: Timeframe string
            
        Returns:
            List of (start_date, end_date) tuples representing gaps
        """
        try:
            # Get the price table for this pair
            table = self._ensure_price_table(pair_name, timeframe)
            
            # Get all timestamps for the pair
            query = select(table.c.timestamp).order_by(table.c.timestamp)
            
            with self.engine.connect() as conn:
                result = conn.execute(query)
                timestamps = [row[0] for row in result]
            
            if not timestamps:
                logger.warning(f"No data found for {pair_name}")
                return []
                
            # Calculate expected time delta based on timeframe
            if timeframe == "1m":
                expected_delta = timedelta(minutes=1)
            elif timeframe == "5m":
                expected_delta = timedelta(minutes=5)
            elif timeframe == "15m":
                expected_delta = timedelta(minutes=15)
            elif timeframe == "30m":
                expected_delta = timedelta(minutes=30)
            elif timeframe == "1h":
                expected_delta = timedelta(hours=1)
            elif timeframe == "4h":
                expected_delta = timedelta(hours=4)
            elif timeframe == "1d":
                expected_delta = timedelta(days=1)
            else:
                logger.error(f"Unsupported timeframe for gap detection: {timeframe}")
                return []
                
            # Find gaps
            gaps = []
            for i in range(1, len(timestamps)):
                current = timestamps[i]
                previous = timestamps[i-1]
                actual_delta = current - previous
                
                # Calculate expected number of intervals
                expected_intervals = int(actual_delta.total_seconds() / expected_delta.total_seconds())
                
                # Check if there's a gap (more than one expected interval)
                if expected_intervals > 1:
                    # Check if gap is during weekend (for forex)
                    gap_start = previous
                    gap_end = current
                    
                    # Skip gaps during weekends for forex markets
                    if not self._is_weekend_gap(gap_start, gap_end):
                        gaps.append((gap_start, gap_end))
                        
            logger.info(f"Found {len(gaps)} data gaps for {pair_name} at {timeframe}")
            return gaps
            
        except Exception as e:
            logger.error(f"Error finding data gaps for {pair_name}: {e}", exc_info=True)
            return []
    
    def _is_weekend_gap(self, start: datetime, end: datetime) -> bool:
        """
        Check if a gap is during the weekend (for forex markets).
        
        Args:
            start: Gap start time
            end: Gap end time
            
        Returns:
            True if the gap is during the weekend, False otherwise
        """
        # Check if forex markets are closed on weekends according to config
        if not self.config["calendar"].get("weekend_trading", False):
            # If end time is Monday and start time is Friday, might be weekend
            if end.weekday() == 0 and start.weekday() == 4:
                # Check if gap starts on Friday after market close
                friday_close = self._get_market_close_time(4)  # 4 = Friday
                
                # Check if gap ends on Monday after market open
                monday_open = self._get_market_open_time(0)    # 0 = Monday
                
                if start.hour >= friday_close and end.hour <= monday_open:
                    return True
                    
        return False
    
    def _get_market_close_time(self, day: int) -> int:
        """
        Get market close time for a specific day from config.
        
        Args:
            day: Day of week (0 = Monday, 6 = Sunday)
            
        Returns:
            Hour of market close (default 22 for forex)
        """
        market_hours = self.config["calendar"].get("forex_market_open", [])
        for hours in market_hours:
            if hours.get("day") == day:
                time_str = hours.get("time", "22:00")
                return int(time_str.split(":")[0])
                
        return 22  # Default close at 22:00
    
    def _get_market_open_time(self, day: int) -> int:
        """
        Get market open time for a specific day from config.
        
        Args:
            day: Day of week (0 = Monday, 6 = Sunday)
            
        Returns:
            Hour of market open (default 0 for forex)
        """
        market_hours = self.config["calendar"].get("forex_market_open", [])
        for hours in market_hours:
            if hours.get("day") == day:
                time_str = hours.get("time", "00:00")
                return int(time_str.split(":")[0])
                
        return 0  # Default open at 00:00
    
    def get_data_coverage(self, pair_name: str, timeframe: str = "1m") -> Dict:
        """
        Get data coverage information for a currency pair.
        
        Args:
            pair_name: Currency pair name
            timeframe: Timeframe string
            
        Returns:
            Dictionary with coverage information
        """
        try:
            # Get the price table for this pair
            table = self._ensure_price_table(pair_name, timeframe)
            
            # Get min and max timestamps and count
            with self.engine.connect() as conn:
                min_time = conn.execute(select(func.min(table.c.timestamp))).scalar()
                max_time = conn.execute(select(func.max(table.c.timestamp))).scalar()
                count = conn.execute(select(func.count(table.c.timestamp))).scalar()
            
            # Calculate expected count based on timeframe
            if min_time and max_time:
                # Calculate time delta in minutes
                if timeframe == "1m":
                    minutes = int((max_time - min_time).total_seconds() / 60)
                    expected_count = minutes
                elif timeframe == "5m":
                    minutes = int((max_time - min_time).total_seconds() / 60)
                    expected_count = minutes / 5
                elif timeframe == "15m":
                    minutes = int((max_time - min_time).total_seconds() / 60)
                    expected_count = minutes / 15
                elif timeframe == "30m":
                    minutes = int((max_time - min_time).total_seconds() / 60)
                    expected_count = minutes / 30
                elif timeframe == "1h":
                    minutes = int((max_time - min_time).total_seconds() / 60)
                    expected_count = minutes / 60
                elif timeframe == "4h":
                    minutes = int((max_time - min_time).total_seconds() / 60)
                    expected_count = minutes / 240
                elif timeframe == "1d":
                    minutes = int((max_time - min_time).total_seconds() / 60)
                    expected_count = minutes / 1440
                else:
                    expected_count = 0
                
                # Adjust for weekends if forex
                if not self.config["calendar"].get("weekend_trading", False):
                    # Rough adjustment: subtract 48 hours for each weekend
                    days = (max_time - min_time).days
                    weekends = days // 7
                    
                    if timeframe == "1m":
                        weekend_minutes = weekends * 48 * 60
                        expected_count -= weekend_minutes
                    elif timeframe == "5m":
                        weekend_minutes = weekends * 48 * 12
                        expected_count -= weekend_minutes
                    elif timeframe == "15m":
                        weekend_minutes = weekends * 48 * 4
                        expected_count -= weekend_minutes
                    elif timeframe == "30m":
                        weekend_minutes = weekends * 48 * 2
                        expected_count -= weekend_minutes
                    elif timeframe == "1h":
                        weekend_minutes = weekends * 48
                        expected_count -= weekend_minutes
                    elif timeframe == "4h":
                        weekend_minutes = weekends * 12
                        expected_count -= weekend_minutes
                    elif timeframe == "1d":
                        weekend_minutes = weekends * 2
                        expected_count -= weekend_minutes
                
                # Calculate coverage percentage
                expected_count = max(0, expected_count)
                coverage = (count / expected_count) * 100 if expected_count > 0 else 0
            else:
                coverage = 0
                expected_count = 0
                
            return {
                "pair": pair_name,
                "timeframe": timeframe,
                "start_date": min_time,
                "end_date": max_time,
                "record_count": count,
                "expected_count": int(expected_count),
                "coverage_percent": round(coverage, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting data coverage for {pair_name}: {e}", exc_info=True)
            return {}