from setuptools import setup, find_packages

setup(
    name="forex_ai_trading",
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
