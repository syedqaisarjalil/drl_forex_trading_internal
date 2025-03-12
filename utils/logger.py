"""
Centralized logging configuration for the Forex AI Trading system.
"""
import os
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

from drl_forex_trading_internal.utils.config import load_config, get_absolute_path

def setup_logging(module_name: str = None) -> logging.Logger:
    """
    Set up logging for a module with proper formatting and handlers.
    
    Args:
        module_name: Name of the module requesting a logger
        
    Returns:
        Configured logger instance
    """
    # Load configuration
    config = load_config()
    
    # Create logs directory if it doesn't exist
    logs_dir = get_absolute_path(config["paths"]["logs"])
    os.makedirs(logs_dir, exist_ok=True)
    
    # Get logger
    logger_name = module_name if module_name else "forex_ai"
    logger = logging.getLogger(logger_name)
    
    # Only configure handlers if they haven't been set up yet
    if not logger.handlers:
        # Set log level (default to INFO if not specified)
        log_level_name = os.environ.get("FOREX_AI_LOG_LEVEL", "INFO")
        log_level = getattr(logging, log_level_name, logging.INFO)
        logger.setLevel(log_level)
        
        # Create formatters
        fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        date_fmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(fmt=fmt, datefmt=date_fmt)
        
        # Create file handler for the module
        today = datetime.now().strftime("%Y-%m-%d")
        if module_name:
            log_file = logs_dir / f"{module_name}_{today}.log"
        else:
            log_file = logs_dir / f"forex_ai_{today}.log"
            
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=10,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        logger.info(f"Logging initialized for {logger_name}")
    
    return logger

def get_logger(module_name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Args:
        module_name: Name of the module requesting a logger
        
    Returns:
        Logger instance
    """
    return setup_logging(module_name)