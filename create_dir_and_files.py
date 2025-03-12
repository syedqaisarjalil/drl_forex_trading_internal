#!/usr/bin/env python3
import os
import sys
from pathlib import Path

def create_directory(path):
    """Create a directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")
    else:
        print(f"Directory already exists: {path}")

def create_file(path, content=""):
    """Create a file with optional content if it doesn't exist."""
    if not os.path.exists(path):
        with open(path, 'w') as f:
            f.write(content)
        print(f"Created file: {path}")
    else:
        print(f"File already exists: {path}")

def init_file_content(module_name):
    """Generate content for __init__.py files."""
    return f"""# {module_name} package

"""

def setup_project_structure(base_dir):
    """Create the Forex AI Trading project structure."""
    # Create base directory
    create_directory(base_dir)
    
    # Configuration files
    config_dir = os.path.join(base_dir, "config")
    create_directory(config_dir)
    create_file(os.path.join(config_dir, "main.yml"), "# Core settings (pairs, timeframes, paths)\n")
    create_file(os.path.join(config_dir, "models.yml"), "# Model hyperparameters\n")
    create_file(os.path.join(config_dir, "strategies.yml"), "# Strategy definitions\n")
    
    # Data module
    data_dir = os.path.join(base_dir, "data")
    create_directory(data_dir)
    create_file(os.path.join(data_dir, "fetcher.py"), "# MT5 data acquisition\n")
    create_file(os.path.join(data_dir, "database.py"), "# Database operations\n")
    create_file(os.path.join(data_dir, "resampler.py"), "# Timeframe conversion\n")
    create_file(os.path.join(data_dir, "updater.py"), "# Scheduled data updates\n")
    create_file(os.path.join(data_dir, "__init__.py"), init_file_content("Data"))
    
    # Models module
    models_dir = os.path.join(base_dir, "models")
    create_directory(models_dir)
    create_file(os.path.join(models_dir, "drl.py"), "# DRL implementation (Stable Baselines3)\n")
    create_file(os.path.join(models_dir, "features.py"), "# Feature engineering with LSTM\n")
    create_file(os.path.join(models_dir, "training.py"), "# Model training pipeline\n")
    create_file(os.path.join(models_dir, "registry.py"), "# Model storage and retrieval\n")
    create_file(os.path.join(models_dir, "__init__.py"), init_file_content("Models"))
    
    # Indicators module
    indicators_dir = os.path.join(base_dir, "indicators")
    create_directory(indicators_dir)
    create_file(os.path.join(indicators_dir, "base.py"), "# Base indicator class\n")
    create_file(os.path.join(indicators_dir, "standard.py"), "# Standard indicators (RSI, MACD, etc.)\n")
    create_file(os.path.join(indicators_dir, "registry.py"), "# Indicator registration\n")
    create_file(os.path.join(indicators_dir, "__init__.py"), init_file_content("Indicators"))
    
    # Strategies module
    strategies_dir = os.path.join(base_dir, "strategies")
    create_directory(strategies_dir)
    create_file(os.path.join(strategies_dir, "manager.py"), "# Strategy loading and management\n")
    create_file(os.path.join(strategies_dir, "evaluator.py"), "# Strategy evaluation logic\n")
    create_file(os.path.join(strategies_dir, "factory.py"), "# Strategy creation helpers\n")
    create_file(os.path.join(strategies_dir, "__init__.py"), init_file_content("Strategies"))
    
    # Backtesting module
    backtesting_dir = os.path.join(base_dir, "backtesting")
    create_directory(backtesting_dir)
    create_file(os.path.join(backtesting_dir, "engine.py"), "# Backtesting simulation\n")
    create_file(os.path.join(backtesting_dir, "metrics.py"), "# Performance metrics\n")
    create_file(os.path.join(backtesting_dir, "visualization.py"), "# Results visualization\n")
    create_file(os.path.join(backtesting_dir, "__init__.py"), init_file_content("Backtesting"))
    
    # Trading module
    trading_dir = os.path.join(base_dir, "trading")
    create_directory(trading_dir)
    create_file(os.path.join(trading_dir, "bridge.py"), "# ZeroMQ communication\n")
    create_file(os.path.join(trading_dir, "risk.py"), "# Risk management\n")
    create_file(os.path.join(trading_dir, "execution.py"), "# Trade execution logic\n")
    create_file(os.path.join(trading_dir, "monitor.py"), "# Trade monitoring\n")
    create_file(os.path.join(trading_dir, "__init__.py"), init_file_content("Trading"))
    
    # MT5 module
    mt5_dir = os.path.join(base_dir, "mt5")
    create_directory(mt5_dir)
    create_file(os.path.join(mt5_dir, "ForexAI_EA.mq5"), "// MT5 Expert Advisor\n")
    create_file(os.path.join(mt5_dir, "ZMQ_Bridge.mqh"), "// ZeroMQ implementation\n")
    create_file(os.path.join(mt5_dir, "Utilities.mqh"), "// Common MT5 utilities\n")
    
    # Database module
    db_dir = os.path.join(base_dir, "db")
    create_directory(db_dir)
    create_file(os.path.join(db_dir, "connector.py"), "# Database connection handling\n")
    create_file(os.path.join(db_dir, "schema.py"), "# Database schema definition\n")
    db_migrations_dir = os.path.join(db_dir, "migrations")
    create_directory(db_migrations_dir)
    create_file(os.path.join(db_dir, "__init__.py"), init_file_content("Database"))
    
    # Utilities module
    utils_dir = os.path.join(base_dir, "utils")
    create_directory(utils_dir)
    create_file(os.path.join(utils_dir, "logger.py"), "# Logging utilities\n")
    create_file(os.path.join(utils_dir, "config.py"), "# Configuration utilities\n")
    create_file(os.path.join(utils_dir, "datetime.py"), "# Date/time handling\n")
    create_file(os.path.join(utils_dir, "math.py"), "# Common math operations\n")
    create_file(os.path.join(utils_dir, "testing.py"), "# Testing utilities\n")
    create_file(os.path.join(utils_dir, "__init__.py"), init_file_content("Utilities"))
    
    # Scripts
    scripts_dir = os.path.join(base_dir, "scripts")
    create_directory(scripts_dir)
    create_file(os.path.join(scripts_dir, "install.py"), "# Installation script\n")
    create_file(os.path.join(scripts_dir, "data_updater.py"), "# Script for scheduled data updates\n")
    create_file(os.path.join(scripts_dir, "backtest.py"), "# CLI for backtesting\n")
    create_file(os.path.join(scripts_dir, "train_model.py"), "# CLI for model training\n")
    
    # Tests
    tests_dir = os.path.join(base_dir, "tests")
    create_directory(tests_dir)
    create_directory(os.path.join(tests_dir, "data"))
    create_directory(os.path.join(tests_dir, "models"))
    create_directory(os.path.join(tests_dir, "indicators"))
    create_directory(os.path.join(tests_dir, "strategies"))
    create_file(os.path.join(tests_dir, "__init__.py"), init_file_content("Tests"))
    
    # Documentation
    docs_dir = os.path.join(base_dir, "docs")
    create_directory(docs_dir)
    create_file(os.path.join(docs_dir, "setup.md"), "# Setup Instructions\n")
    create_file(os.path.join(docs_dir, "usage.md"), "# Usage Guide\n")
    create_file(os.path.join(docs_dir, "api.md"), "# API Documentation\n")
    create_file(os.path.join(docs_dir, "examples.md"), "# Usage Examples\n")
    
    # Root files
    create_file(os.path.join(base_dir, ".gitignore"), """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/

# IDE files
.idea/
.vscode/
*.swp
*.swo

# Project specific
*.log
.env
models/trained/
data/raw/
""")
    
    create_file(os.path.join(base_dir, "requirements.txt"), """# Core dependencies
numpy>=1.20.0
pandas>=1.3.0
matplotlib>=3.4.0
seaborn>=0.11.0
scikit-learn>=0.24.0

# Deep Learning
torch>=1.9.0
stable-baselines3>=1.0

# MetaTrader connection
pyzmq>=22.0.0

# Database
psycopg2-binary>=2.9.0
sqlalchemy>=1.4.0

# Utilities
pyyaml>=6.0
python-dotenv>=0.19.0
click>=8.0.0
tqdm>=4.62.0
""")
    
    create_file(os.path.join(base_dir, "setup.py"), """from setuptools import setup, find_packages

setup(
    name="drl_forex_trading_internal",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.20.0",
        "pandas>=1.3.0",
        "matplotlib>=3.4.0",
        "seaborn>=0.11.0",
        "scikit-learn>=0.24.0",
        "torch>=1.9.0",
        "stable-baselines3>=1.0",
        "pyzmq>=22.0.0",
        "psycopg2-binary>=2.9.0",
        "sqlalchemy>=1.4.0",
        "pyyaml>=6.0",
        "python-dotenv>=0.19.0",
        "click>=8.0.0",
        "tqdm>=4.62.0",
    ],
    author="AI Forex Trading Developer",
    author_email="developer@example.com",
    description="AI-powered Forex Trading System for MT5",
    keywords="forex, trading, ai, reinforcement learning",
    python_requires=">=3.8",
)
""")
    
    create_file(os.path.join(base_dir, "README.md"), """# AI Forex Trading Bot

## Project Overview
This project involves developing a modular, scalable AI-powered Forex trading system for MetaTrader 5 (MT5). The system combines Deep Reinforcement Learning (DRL) with technical indicators to make trading decisions, execute trades, and manage risk.

## Key Components
- **Communication System**: ZeroMQ bridge between Python and MT5
- **Data Management**: PostgreSQL storage with efficient resampling
- **AI Model Framework**: DRL using Stable Baselines3 with LSTM
- **Technical Indicators**: RSI, MACD, Bollinger Bands, etc.
- **Strategy System**: Combining AI models with technical indicators
- **Backtesting Engine**: Vectorized backtesting with realistic modeling
- **Trading Execution**: Risk management and trade monitoring

## Getting Started
See the documentation in the docs/ folder for setup and usage instructions.

## License
[Your License Here]
""")
    
    print("\nProject structure created successfully!")
    print(f"Project directory: {os.path.abspath(base_dir)}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        project_dir = sys.argv[1]
    else:
        project_dir = "drl_forex_trading_internal_internal"
    project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    
    setup_project_structure(project_dir)