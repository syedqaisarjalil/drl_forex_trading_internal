"""
Configuration utilities for the Forex AI Trading system.
Handles loading from YAML files and environment variables.
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

def get_config_path(config_name: str = "main") -> Path:
    """
    Get the path to a configuration file.
    
    Args:
        config_name: Name of the configuration file without extension
        
    Returns:
        Path to the configuration file
    """
    # First try to find the config file in the drl_forex_trading_internal directory
    current_file_dir = Path(__file__).parent  # utils directory
    module_root = current_file_dir.parent     # drl_forex_trading_internal directory
    config_path = module_root / "config" / f"{config_name}.yml"
    
    if config_path.exists():
        return config_path
    
    # If not found, try at the project root level
    project_root = module_root.parent
    config_path = project_root / "config" / f"{config_name}.yml"
    
    if config_path.exists():
        return config_path
    
    # If still not found, check if there's an environment variable defining the path
    if "FOREX_AI_CONFIG_DIR" in os.environ:
        config_dir = Path(os.environ["FOREX_AI_CONFIG_DIR"])
        config_path = config_dir / f"{config_name}.yml"
        if config_path.exists():
            return config_path
    
    # Default to module config path (even if it doesn't exist)
    return module_root / "config" / f"{config_name}.yml"

def load_config(config_name: str = "main") -> Dict[str, Any]:
    """
    Load configuration from a YAML file with environment variable overrides.
    
    Args:
        config_name: Name of the configuration file without extension
        
    Returns:
        Dictionary containing configuration values
        
    Raises:
        FileNotFoundError: If the configuration file doesn't exist
    """
    config_path = get_config_path(config_name)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, "r") as config_file:
        config = yaml.safe_load(config_file)
    
    # Override with environment variables if available
    _override_with_env_vars(config)
    
    return config

def _override_with_env_vars(config: Dict[str, Any], prefix: str = "FOREX_AI") -> None:
    """
    Override configuration values with environment variables.
    Environment variables should be in the format PREFIX_SECTION_KEY.
    
    Args:
        config: Configuration dictionary to modify
        prefix: Prefix for environment variables
    """
    # Override database credentials with environment variables if available
    db_env_mappings = {
        f"{prefix}_DB_HOST": ("database", "host"),
        f"{prefix}_DB_PORT": ("database", "port"),
        f"{prefix}_DB_NAME": ("database", "name"),
        f"{prefix}_DB_USER": ("database", "user"),
        f"{prefix}_DB_PASSWORD": ("database", "password"),
    }
    
    # Override MT5 credentials with environment variables if available
    mt5_env_mappings = {
        f"{prefix}_MT5_SERVER": ("mt5", "server"),
        f"{prefix}_MT5_LOGIN": ("mt5", "login"),
        f"{prefix}_MT5_PASSWORD": ("mt5", "password"),
    }
    
    # Override paths with environment variables if available
    path_env_mappings = {
        f"{prefix}_PATH_MODELS": ("paths", "models"),
        f"{prefix}_PATH_LOGS": ("paths", "logs"),
        f"{prefix}_PATH_DATA": ("paths", "data"),
    }
    
    # Combine all mappings
    all_mappings = {**db_env_mappings, **mt5_env_mappings, **path_env_mappings}
    
    for env_var, (section, key) in all_mappings.items():
        if env_var in os.environ:
            # Convert numeric values if needed
            value = os.environ[env_var]
            try:
                if value.isdigit():
                    value = int(value)
                elif value.replace(".", "", 1).isdigit():
                    value = float(value)
            except (ValueError, AttributeError):
                pass
            
            # Update config
            if section in config:
                config[section][key] = value

def get_module_root() -> Path:
    """
    Get the module root directory (drl_forex_trading_internal).
    
    Returns:
        Path to the module root directory
    """
    current_file_dir = Path(__file__).parent  # utils directory
    module_root = current_file_dir.parent     # drl_forex_trading_internal directory
    return module_root

def get_project_root() -> Path:
    """
    Get the project root directory.
    
    Returns:
        Path to the project root directory
    """
    # The project root is one level up from the module root
    return get_module_root().parent

def get_absolute_path(relative_path: str) -> Path:
    """
    Convert a relative path from config to an absolute path within the module.
    
    Args:
        relative_path: Relative path from module root
        
    Returns:
        Absolute path
    """
    return get_module_root() / relative_path