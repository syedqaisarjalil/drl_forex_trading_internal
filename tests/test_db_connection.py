"""
Test script for database connection and initialization.
"""
# With D:\work in PYTHONPATH, we can import directly using the package name
from drl_forex_trading_internal.utils.logger import setup_logging
from drl_forex_trading_internal.db import init_db, get_session
from drl_forex_trading_internal.db import CurrencyPair

# Configure logging
logger = setup_logging("tests.db_connection")

def test_db_connection():
    """Test database connection and schema initialization."""
    try:
        # Initialize the database (create tables)
        init_db()
        
        logger.info("Database tables created successfully!")
        
        # Test connection by adding a currency pair
        session = get_session()
        
        # Check if EURUSD already exists
        existing_pair = session.query(CurrencyPair).filter_by(name="EURUSD").first()
        
        if existing_pair:
            logger.info(f"Currency pair already exists: {existing_pair}")
        else:
            # Create a new currency pair
            eurusd = CurrencyPair(
                name="EURUSD",
                description="Euro vs US Dollar",
                pip_value=0.0001,
                spread_avg=1.5
            )
            
            # Add to database
            session.add(eurusd)
            session.commit()
            
            logger.info(f"Added new currency pair: {eurusd}")
        
        # List all currency pairs
        pairs = session.query(CurrencyPair).all()
        logger.info("All currency pairs in database:")
        for pair in pairs:
            logger.info(f"- {pair.name}: {pair.description}")
        
        session.close()
        
        logger.info("Database connection test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Database connection test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    test_db_connection()