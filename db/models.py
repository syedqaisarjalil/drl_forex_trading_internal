"""
All database models for the Forex AI Trading system.
"""
import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, JSON, ForeignKey, UniqueConstraint, Index, MetaData, Table
from sqlalchemy.ext.declarative import declarative_base

# Create base metadata with naming convention
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
metadata = MetaData(naming_convention=naming_convention)
Base = declarative_base(metadata=metadata)

class CurrencyPair(Base):
    """Currency pair information."""
    __tablename__ = 'currency_pairs'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(10), nullable=False, unique=True)
    description = Column(String(100))
    pip_value = Column(Float, nullable=False)
    spread_avg = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, 
                       onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<CurrencyPair(name='{self.name}')>"

class ModelInfo(Base):
    """Information about trained models."""
    __tablename__ = 'model_info'
    __table_args__ = (
        UniqueConstraint('name', 'version', name='uix_model_name_version'),
        {'extend_existing': True}
    )
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # e.g., 'DRL', 'LSTM'
    version = Column(String(20), nullable=False)
    description = Column(String(500))
    file_path = Column(String(255), nullable=False)  # Path to the actual model file
    
    # Training information
    training_start_date = Column(DateTime, nullable=False)
    training_end_date = Column(DateTime, nullable=False)
    currency_pairs = Column(JSON, nullable=False)  # List of currency pairs used for training
    timeframes = Column(JSON, nullable=False)  # List of timeframes used
    features = Column(JSON, nullable=False)  # List of features used for training
    
    # Hyperparameters and configuration
    hyperparameters = Column(JSON, nullable=False)  # Model hyperparameters
    metrics = Column(JSON)  # Performance metrics
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, 
                       onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<ModelInfo(name='{self.name}', version='{self.version}')>"

class Strategy(Base):
    """Trading strategy information."""
    __tablename__ = 'strategies'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500))
    is_active = Column(Boolean, default=False)
    
    # Components and configuration
    model_ids = Column(JSON)  # IDs of models used in this strategy
    indicators = Column(JSON)  # List of indicators with parameters
    rules = Column(JSON)  # Strategy rules
    parameters = Column(JSON)  # Additional strategy parameters
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, 
                       onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<Strategy(name='{self.name}')>"

class Trade(Base):
    """Information about executed trades."""
    __tablename__ = 'trades'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=False)
    currency_pair_id = Column(Integer, ForeignKey('currency_pairs.id'), nullable=False)
    
    # Trade details
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime)
    position_type = Column(String(10), nullable=False)  # 'BUY' or 'SELL'
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    volume = Column(Float, nullable=False)
    
    # Risk management
    stop_loss = Column(Float)
    take_profit = Column(Float)
    
    # Results
    profit_loss = Column(Float)
    profit_loss_pips = Column(Float)
    commission = Column(Float, default=0)
    swap = Column(Float, default=0)
    
    # Additional information
    timeframe = Column(String(10), nullable=False)  # e.g., 'M1', 'H1'
    signals = Column(JSON)  # Signals that triggered this trade
    notes = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, 
                       onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<Trade(id={self.id}, pair='{self.currency_pair_id}')>"