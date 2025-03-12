"""
Script for scheduled data updates.
This can be called by a task scheduler or cron job.

Usage:
    python -m scripts.data_updater

Environment Variables:
    FOREX_AI_LOG_LEVEL: Set log level (default: INFO)
    FOREX_AI_CONFIG_DIR: Set config directory (optional)
"""
import sys
import argparse
import logging
from datetime import datetime

# Ensure the root directory is in the path
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import Forex AI modules
from drl_forex_trading_internal.utils.logger import setup_logging
from drl_forex_trading_internal.db import init_db
from drl_forex_trading_internal.data.updater import DataUpdater

def run_update(args):
    """Run the data update process."""
    # Configure logging
    logger = setup_logging("scripts.data_updater")
    logger.info(f"Starting data update at {datetime.now()}")
    
    try:
        # Initialize database
        init_db()
        
        # Create and initialize updater
        updater = DataUpdater()
        
        # Run the update
        if args.full:
            # Run a full update with gap filling
            logger.info("Running full update with gap filling...")
            updater.run_scheduled_update()
        else:
            # Run a quick update of just the latest data
            logger.info("Running quick update of latest data only...")
            updater.initialize()
            
            try:
                # Update all pairs but skip gap filling
                results = updater.update_all_pairs(
                    update_latest=True,
                    fill_gaps=False,
                    # update_timeframes=True
                )
                
                # Check results
                if all(results.values()):
                    logger.info("Quick update completed successfully")
                else:
                    failed_pairs = [pair for pair, success in results.items() if not success]
                    logger.warning(f"Quick update failed for some pairs: {failed_pairs}")
            finally:
                # Always shut down MT5
                updater.shutdown()
        
        logger.info(f"Data update completed at {datetime.now()}")
        return 0
        
    except Exception as e:
        logger.error(f"Data update failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run scheduled data updates")
    parser.add_argument(
        "--full", action="store_true",
        help="Run a full update with gap filling (slower but more thorough)"
    )
    
    args = parser.parse_args()
    
    # Run the update
    sys.exit(run_update(args))