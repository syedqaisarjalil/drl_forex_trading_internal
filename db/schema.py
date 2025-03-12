"""
Database schema utilities for the Forex AI Trading system.
"""
import sqlalchemy
from sqlalchemy import Table, Column, DateTime, Float, MetaData, Index

def create_price_table(engine, pair_name, timeframe="1m"):
    """
    Create a new price table for a currency pair.
    
    Args:
        engine: SQLAlchemy engine
        pair_name: Currency pair name (e.g., 'EURUSD')
        timeframe: Timeframe (e.g., '1m', '5m', '1h')
    """
    metadata = MetaData(schema='price_data')
    
    # Convert pair name to lowercase for table naming
    table_name = f"{pair_name.lower()}_{timeframe}"
    
    # Check if table already exists
    insp = sqlalchemy.inspect(engine)
    if insp.has_table(table_name, schema='price_data'):
        # Table exists, get it from metadata
        metadata.reflect(bind=engine, schema='price_data', only=[table_name])
        return metadata.tables[f'price_data.{table_name}']
    
    # Create table
    table = Table(
        table_name, 
        metadata,
        Column('timestamp', DateTime, primary_key=True),
        Column('open', Float, nullable=False),
        Column('high', Float, nullable=False),
        Column('low', Float, nullable=False),
        Column('close', Float, nullable=False),
        Column('volume', Float, nullable=False),
        Index(f'ix_{table_name}_timestamp', 'timestamp')
    )
    
    # Create table in the database
    metadata.create_all(engine)
    
    return table