"""Logging configuration and utilities."""
from __future__ import annotations

import logging
import logging.config
from pathlib import Path

import yaml


def setup_logging(config_path: str | Path | None = None) -> None:
    """Setup logging configuration from YAML file.
    
    Args:
        config_path: Path to logging config YAML. If None, uses default config.
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "logging.yaml"
    
    config_path = Path(config_path)
    
    # Ensure logs directory exists
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
            logging.config.dictConfig(config)
    else:
        # Fallback to basic config
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
