"""
Data updater module for the Forex AI Trading system.
Handles scheduled data updates, gap filling, and data integrity checks.
"""
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set, Union
import concurrent.futures

from drl_forex_trading_internal.utils.logger import get_logger
from drl_forex_trading_internal.utils.config import load_config
from drl_forex_trading_internal.data.fetcher import MT5Fetcher
from drl_forex_trading_internal.data.database import DataManager
from drl_forex_trading_internal.data.resampler import DataResampler

# Create logger
logger = get_logger("data.updater")

class DataUpdater:
	"""
	Class to handle data updates and gap filling.
	"""
	
	def __init__(self):
		"""Initialize the data updater."""
		self.config = load_config()
		self.data_config = self.config["data"]
		self.update_config = self.data_config["update"]
		self.fetcher = MT5Fetcher()
		self.data_manager = DataManager()
		self.resampler = DataResampler()
		
	def initialize(self) -> bool:
		"""
		Initialize the updater by connecting to MT5.
		
		Returns:
			bool: True if successful, False otherwise
		"""
		return self.fetcher.initialize()
		
	def shutdown(self):
		"""Shutdown MT5 connection."""
		self.fetcher.shutdown()
	
	def update_latest_data(
		self,
		pair_name: str,
		last_n_candles: int = 1000
	) -> bool:
		"""
		Update the latest data for a currency pair.
		
		Args:
			pair_name: Currency pair name
			last_n_candles: Number of latest candles to fetch
			
		Returns:
			bool: True if successful, False otherwise
		"""
		try:
			# Fetch the latest data from MT5
			logger.info(f"Fetching the latest {last_n_candles} candles for {pair_name}...")
			df = self.fetcher.fetch_ohlcv(pair_name, "M1", count=last_n_candles)
			if df is None or len(df) == 0:
				logger.error(f"Failed to fetch latest data for {pair_name}")
				return False

			current_minute = datetime.utcnow().replace(second=0, microsecond=0)
			logger.info(f"Current minute: {current_minute}")
			if df is not None and not df.empty:
				logger.info(f"Data index range: {df.index.min()} to {df.index.max()}")
				
				# Convert index to same format for comparison
				if df.index.tzinfo is not None:
					current_minute = current_minute.replace(tzinfo=df.index.tzinfo)
				
				# Filter more explicitly
				before_count = len(df)
				df = df[df.index < current_minute]
				after_count = len(df)
				
				if before_count > after_count:
					logger.info(f"Filtered out {before_count - after_count} rows for current minute {current_minute}")
				else:
					logger.info(f"No current minute data found to filter (current: {current_minute})")
				
			# Store the data
			logger.info(f"Storing {len(df)} latest candles for {pair_name}...")
			success = self.data_manager.store_price_data(pair_name, df, timeframe="1m")
			if not success:
				logger.error(f"Failed to store latest data for {pair_name}")
				return False
			
			logger.info(f"Successfully updated latest data for {pair_name}")
			return True
			
		except Exception as e:
			logger.error(f"Error updating latest data for {pair_name}: {e}", exc_info=True)
			return False
	
	def fill_data_gaps(
		self,
		pair_name: str,
		timeframe: str = "1m",
		max_gap_days: int = 30
	) -> bool:
		"""
		Find and fill gaps in the price data for a currency pair.
		
		Args:
			pair_name: Currency pair name
			timeframe: Timeframe string (should always be "1m")
			max_gap_days: Maximum gap size in days to fill
			
		Returns:
			bool: True if successful, False otherwise
		"""
		try:
			# Only fill gaps for 1-minute data
			if timeframe != "1m":
				logger.info(f"Gap filling is only performed for 1-minute data, requested {timeframe}")
				return False
				
			# Find gaps in the data
			logger.info(f"Finding gaps in {timeframe} data for {pair_name}...")
			gaps = self.data_manager.find_data_gaps(pair_name, timeframe)
			
			if not gaps:
				logger.info(f"No gaps found in {timeframe} data for {pair_name}")
				return True
				
			logger.info(f"Found {len(gaps)} gaps in {timeframe} data for {pair_name}")
			
			# Sort gaps by start time (oldest first)
			gaps.sort(key=lambda x: x[0])
			
			# Track filled gaps
			filled_gaps = 0
			max_gap_timedelta = timedelta(days=max_gap_days)
			
			# Process each gap
			for gap_start, gap_end in gaps:
				# Skip gaps that are too large
				gap_size = gap_end - gap_start
				if gap_size > max_gap_timedelta:
					logger.warning(f"Gap too large to fill: {gap_start} to {gap_end} ({gap_size.days} days)")
					continue
					
				# # Skip weekend gaps if forex
				# if self._is_weekend_gap(gap_start, gap_end):
				# 	logger.info(f"Skipping weekend gap: {gap_start} to {gap_end}")
				# 	continue
					
				# Fetch data for the gap
				logger.info(f"Filling gap from {gap_start} to {gap_end}...")
				gap_df = self.fetcher.fetch_ohlcv(pair_name, "M1", gap_start, gap_end)
				
				if gap_df is None or len(gap_df) == 0:
					logger.warning(f"No data available for gap: {gap_start} to {gap_end}")
					continue
					
				# Store the gap data
				success = self.data_manager.store_price_data(pair_name, gap_df, timeframe)
				if success:
					filled_gaps += 1
					logger.info(f"Successfully filled gap from {gap_start} to {gap_end} with {len(gap_df)} candles")
				else:
					logger.error(f"Failed to store gap data from {gap_start} to {gap_end}")
			
			logger.info(f"Gap filling complete. Filled {filled_gaps} out of {len(gaps)} gaps.")
			return True
			
		except Exception as e:
			logger.error(f"Error filling gaps for {pair_name}: {e}", exc_info=True)
			return False
	
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
	
	def update_all_pairs(
		self,
		update_latest: bool = True,
		fill_gaps: bool = True,
		max_workers: int = 4
	) -> Dict[str, bool]:
		"""
		Update all configured currency pairs.
		
		Args:
			update_latest: Whether to update the latest data
			fill_gaps: Whether to fill gaps in historical data
			max_workers: Maximum number of parallel workers
			
		Returns:
			Dictionary mapping pair names to success status
		"""
		results = {}
		
		try:
			# Ensure we have a connection to MT5
			if not self.fetcher.is_initialized and not self.initialize():
				logger.error("Failed to initialize MT5 connection")
				return {}
				
			# Ensure currency pairs exist in the database
			pair_map = self.data_manager.ensure_currency_pairs()
			if not pair_map:
				logger.error("No currency pairs found in configuration")
				return {}
				
			# Update pairs in parallel
			with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
				future_to_pair = {}
				
				for pair_name in pair_map.keys():
					future = executor.submit(
						self._update_single_pair,
						pair_name,
						update_latest,
						fill_gaps
					)
					future_to_pair[future] = pair_name
				
				for future in concurrent.futures.as_completed(future_to_pair):
					pair_name = future_to_pair[future]
					try:
						result = future.result()
						results[pair_name] = result
					except Exception as e:
						logger.error(f"Error updating {pair_name}: {e}", exc_info=True)
						results[pair_name] = False
			
			logger.info(f"Completed update for all pairs: {results}")
			return results
			
		except Exception as e:
			logger.error(f"Error updating all pairs: {e}", exc_info=True)
			return results
		
		finally:
			# Always shut down MT5 when done
			self.shutdown()
	
	def _update_single_pair(
		self,
		pair_name: str,
		update_latest: bool,
		fill_gaps: bool
	) -> bool:
		"""
		Update a single currency pair.
		
		Args:
			pair_name: Currency pair name
			update_latest: Whether to update the latest data
			fill_gaps: Whether to fill gaps in historical data
			
		Returns:
			bool: True if all requested operations succeeded, False otherwise
		"""
		success = True
		
		try:
			logger.info(f"Starting update for {pair_name}...")
			
			# Update latest data if requested
			if update_latest:
				logger.info(f"Updating latest data for {pair_name}...")
				latest_success = self.update_latest_data(
					pair_name,
					last_n_candles=self.update_config.get("max_candles_per_request", 1000)
				)
				success = success and latest_success
			
			# Fill gaps if requested
			if fill_gaps:
				logger.info(f"Filling gaps for {pair_name}...")
				gaps_success = self.fill_data_gaps(
					pair_name,
					timeframe="1m",
					max_gap_days=30
				)
				success = success and gaps_success
			
			logger.info(f"Completed update for {pair_name}: {'Success' if success else 'Failure'}")
			return success
			
		except Exception as e:
			logger.error(f"Error in _update_single_pair for {pair_name}: {e}", exc_info=True)
			return False
	

	"""
Data updater module for the Forex AI Trading system.
Handles scheduled data updates, gap filling, and data integrity checks.
"""
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set, Union
import concurrent.futures

from drl_forex_trading_internal.utils.logger import get_logger
from drl_forex_trading_internal.utils.config import load_config
from drl_forex_trading_internal.data.fetcher import MT5Fetcher
from drl_forex_trading_internal.data.database import DataManager
from drl_forex_trading_internal.data.resampler import DataResampler

# Create logger
logger = get_logger("data.updater")

class DataUpdater:
	"""
	Class to handle data updates and gap filling.
	"""
	
	def __init__(self):
		"""Initialize the data updater."""
		self.config = load_config()
		self.data_config = self.config["data"]
		self.update_config = self.data_config["update"]
		self.fetcher = MT5Fetcher()
		self.data_manager = DataManager()
		self.resampler = DataResampler()
		
	def initialize(self) -> bool:
		"""
		Initialize the updater by connecting to MT5.
		
		Returns:
			bool: True if successful, False otherwise
		"""
		return self.fetcher.initialize()
		
	def shutdown(self):
		"""Shutdown MT5 connection."""
		self.fetcher.shutdown()
	
	def update_latest_data(
		self,
		pair_name: str,
		last_n_candles: int = 1000
	) -> bool:
		"""
		Update the latest data for a currency pair.
		
		Args:
			pair_name: Currency pair name
			last_n_candles: Number of latest candles to fetch
			
		Returns:
			bool: True if successful, False otherwise
		"""
		try:
			# Fetch the latest data from MT5
			logger.info(f"Fetching the latest {last_n_candles} candles for {pair_name}...")
			df = self.fetcher.fetch_ohlcv(pair_name, "M1", count=last_n_candles)
			if df is None or len(df) == 0:
				logger.error(f"Failed to fetch latest data for {pair_name}")
				return False
				
			# Store the data
			logger.info(f"Storing {len(df)} latest candles for {pair_name}...")
			success = self.data_manager.store_price_data(pair_name, df, timeframe="1m")
			if not success:
				logger.error(f"Failed to store latest data for {pair_name}")
				return False
			
			logger.info(f"Successfully updated latest data for {pair_name}")
			return True
			
		except Exception as e:
			logger.error(f"Error updating latest data for {pair_name}: {e}", exc_info=True)
			return False
	
	def fill_data_gaps(
		self,
		pair_name: str,
		timeframe: str = "1m",
		max_gap_days: int = 30
	) -> bool:
		"""
		Find and fill gaps in the price data for a currency pair.
		
		Args:
			pair_name: Currency pair name
			timeframe: Timeframe string (should always be "1m")
			max_gap_days: Maximum gap size in days to fill
			
		Returns:
			bool: True if successful, False otherwise
		"""
		try:
			# Only fill gaps for 1-minute data
			if timeframe != "1m":
				logger.info(f"Gap filling is only performed for 1-minute data, requested {timeframe}")
				return False
				
			# Find gaps in the data
			logger.info(f"Finding gaps in {timeframe} data for {pair_name}...")
			gaps = self.data_manager.find_data_gaps(pair_name, timeframe)
			
			if not gaps:
				logger.info(f"No gaps found in {timeframe} data for {pair_name}")
				return True
				
			logger.info(f"Found {len(gaps)} gaps in {timeframe} data for {pair_name}")
			
			# Sort gaps by start time (oldest first)
			gaps.sort(key=lambda x: x[0])
			
			# Track filled gaps
			filled_gaps = 0
			max_gap_timedelta = timedelta(days=max_gap_days)
			
			# Process each gap
			for gap_start, gap_end in gaps:
				# Skip gaps that are too large
				gap_size = gap_end - gap_start
				if gap_size > max_gap_timedelta:
					logger.warning(f"Gap too large to fill: {gap_start} to {gap_end} ({gap_size.days} days)")
					continue
					
				# Skip weekend gaps if forex
				if self._is_weekend_gap(gap_start, gap_end):
					logger.info(f"Skipping weekend gap: {gap_start} to {gap_end}")
					continue
					
				# Fetch data for the gap
				logger.info(f"Filling gap from {gap_start} to {gap_end}...")
				gap_df = self.fetcher.fetch_ohlcv(pair_name, "M1", gap_start, gap_end)
				
				if gap_df is None or len(gap_df) == 0:
					logger.warning(f"No data available for gap: {gap_start} to {gap_end}")
					continue
					
				# Store the gap data
				success = self.data_manager.store_price_data(pair_name, gap_df, timeframe)
				if success:
					filled_gaps += 1
					logger.info(f"Successfully filled gap from {gap_start} to {gap_end} with {len(gap_df)} candles")
				else:
					logger.error(f"Failed to store gap data from {gap_start} to {gap_end}")
			
			logger.info(f"Gap filling complete. Filled {filled_gaps} out of {len(gaps)} gaps.")
			return True
			
		except Exception as e:
			logger.error(f"Error filling gaps for {pair_name}: {e}", exc_info=True)
			return False
	
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
	
	def update_all_pairs(
		self,
		update_latest: bool = True,
		fill_gaps: bool = True,
		max_workers: int = 4
	) -> Dict[str, bool]:
		"""
		Update all configured currency pairs.
		
		Args:
			update_latest: Whether to update the latest data
			fill_gaps: Whether to fill gaps in historical data
			max_workers: Maximum number of parallel workers
			
		Returns:
			Dictionary mapping pair names to success status
		"""
		results = {}
		
		try:
			# Ensure we have a connection to MT5
			if not self.fetcher.is_initialized and not self.initialize():
				logger.error("Failed to initialize MT5 connection")
				return {}
				
			# Ensure currency pairs exist in the database
			pair_map = self.data_manager.ensure_currency_pairs()
			if not pair_map:
				logger.error("No currency pairs found in configuration")
				return {}
				
			# Update pairs in parallel
			with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
				future_to_pair = {}
				
				for pair_name in pair_map.keys():
					future = executor.submit(
						self._update_single_pair,
						pair_name,
						update_latest,
						fill_gaps
					)
					future_to_pair[future] = pair_name
				
				for future in concurrent.futures.as_completed(future_to_pair):
					pair_name = future_to_pair[future]
					try:
						result = future.result()
						results[pair_name] = result
					except Exception as e:
						logger.error(f"Error updating {pair_name}: {e}", exc_info=True)
						results[pair_name] = False
			
			logger.info(f"Completed update for all pairs: {results}")
			return results
			
		except Exception as e:
			logger.error(f"Error updating all pairs: {e}", exc_info=True)
			return results
		
		finally:
			# Always shut down MT5 when done
			self.shutdown()
	
	def _update_single_pair(
		self,
		pair_name: str,
		update_latest: bool,
		fill_gaps: bool
	) -> bool:
		"""
		Update a single currency pair.
		
		Args:
			pair_name: Currency pair name
			update_latest: Whether to update the latest data
			fill_gaps: Whether to fill gaps in historical data
			
		Returns:
			bool: True if all requested operations succeeded, False otherwise
		"""
		success = True
		
		try:
			logger.info(f"Starting update for {pair_name}...")
			
			# Update latest data if requested
			if update_latest:
				logger.info(f"Updating latest data for {pair_name}...")
				latest_success = self.update_latest_data(
					pair_name,
					last_n_candles=self.update_config.get("max_candles_per_request", 1000)
				)
				success = success and latest_success
			
			# Fill gaps if requested
			if fill_gaps:
				logger.info(f"Filling gaps for {pair_name}...")
				gaps_success = self.fill_data_gaps(
					pair_name,
					timeframe="1m",
					max_gap_days=30
				)
				success = success and gaps_success
			
			logger.info(f"Completed update for {pair_name}: {'Success' if success else 'Failure'}")
			return success
			
		except Exception as e:
			logger.error(f"Error in _update_single_pair for {pair_name}: {e}", exc_info=True)
			return False
	
	def run_scheduled_update(self) -> None:
		"""
		Run a scheduled update for all pairs.
		
		This method is designed to be called by a scheduler (e.g., cron job).
		It will update the latest data and fill gaps.
		"""
		logger.info("Starting scheduled data update...")
		
		try:
			# Get update configuration
			update_frequency = self.update_config.get("frequency", 60)  # minutes
			retry_attempts = self.update_config.get("retry_attempts", 3)
			retry_delay = self.update_config.get("retry_delay", 300)  # seconds
			
			# Try to run the update with retries
			for attempt in range(1, retry_attempts + 1):
				try:
					# Run the update
					results = self.update_all_pairs(
						update_latest=True,
						fill_gaps=True
					)
					
					# Check if all updates succeeded
					if all(results.values()):
						logger.info("Scheduled update completed successfully")
						return
					else:
						# Some updates failed
						failed_pairs = [pair for pair, success in results.items() if not success]
						logger.warning(f"Update failed for some pairs: {failed_pairs}")
						
						if attempt < retry_attempts:
							logger.info(f"Retrying in {retry_delay} seconds (attempt {attempt}/{retry_attempts})...")
							time.sleep(retry_delay)
						else:
							logger.error("All retry attempts failed")
					
				except Exception as e:
					logger.error(f"Error in scheduled update (attempt {attempt}/{retry_attempts}): {e}", exc_info=True)
					
					if attempt < retry_attempts:
						logger.info(f"Retrying in {retry_delay} seconds...")
						time.sleep(retry_delay)
					else:
						logger.error("All retry attempts failed")
			
		except Exception as e:
			logger.error(f"Critical error in scheduled update: {e}", exc_info=True)
			