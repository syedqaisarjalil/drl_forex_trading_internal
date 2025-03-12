"""
Database connector for the Forex AI Trading system.
Handles connections to PostgreSQL using SQLAlchemy.
"""
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from drl_forex_trading_internal.utils.config import load_config
from drl_forex_trading_internal.utils.logger import get_logger

# Import Base from models
from drl_forex_trading_internal.db.models import Base

# Create logger
logger = get_logger("db.connector")

# Global engine instance
_engine: Optional[Engine] = None
_SessionFactory = None

def get_connection_string() -> str:
    """
    Get the PostgreSQL connection string from config.
    
    Returns:
        PostgreSQL connection string
    """
    config = load_config()
    db_config = config["database"]
    
    return (
        f"postgresql://{db_config['user']}:{db_config['password']}@"
        f"{db_config['host']}:{db_config['port']}/{db_config['name']}"
    )

def get_engine() -> Engine:
    """
    Get SQLAlchemy engine instance.
    Creates a new engine if one doesn't exist.
    
    Returns:
        SQLAlchemy engine instance
    """
    global _engine
    
    if _engine is None:
        config = load_config()
        db_config = config["database"]
        
        conn_str = get_connection_string()
        
        # Create engine with connection pooling
        _engine = create_engine(
            conn_str,
            poolclass=QueuePool,
            pool_size=db_config.get("pool_size", 5),
            max_overflow=db_config.get("max_overflow", 10),
            pool_pre_ping=True,  # Check connection validity before using
            pool_recycle=3600,  # Recycle connections after 1 hour
        )
        
        logger.info(f"Created database engine for {db_config['name']} on {db_config['host']}")
    
    return _engine

def get_session_factory():
    """
    Get a session factory for creating database sessions.
    
    Returns:
        SQLAlchemy sessionmaker instance
    """
    global _SessionFactory
    
    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = sessionmaker(bind=engine)
        
    return _SessionFactory

def get_session() -> Session:
    """
    Get a new database session.
    
    Returns:
        SQLAlchemy session
    """
    factory = get_session_factory()
    return factory()

def init_db():
    """
    Initialize the database by creating all tables.
    """
    engine = get_engine()
    
    # Create price_data schema if it doesn't exist
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS price_data"))
        conn.commit()
    
    # Create base tables (except for price data tables which are created dynamically)
    Base.metadata.create_all(engine)
    logger.info("Initialized database tables")
    
    return engine

def close_db_connections():
    """
    Close all database connections.
    Call this when shutting down the application.
    """
    global _engine
    
    if _engine is not None:
        _engine.dispose()
        _engine = None
        logger.info("Closed all database connections")