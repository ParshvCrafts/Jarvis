"""
Logging configuration for JARVIS.

Uses loguru for structured, colorful logging with rotation and filtering.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from .config import JarvisConfig

# Remove default handler
logger.remove()

# Project root for log files
PROJECT_ROOT = Path(__file__).parent.parent.parent
LOG_DIR = PROJECT_ROOT / "data" / "logs"


def setup_logging(config: JarvisConfig | None = None) -> None:
    """
    Configure logging for JARVIS.
    
    Args:
        config: Optional JARVIS configuration. If not provided, uses defaults.
    """
    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Determine log level
    log_level = "INFO"
    if config:
        log_level = config.general.log_level
        if config.general.debug:
            log_level = "DEBUG"
    
    # Console handler with colors
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # File handler for all logs
    logger.add(
        LOG_DIR / "jarvis_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="00:00",  # Rotate at midnight
        retention="7 days",  # Keep logs for 7 days
        compression="zip",  # Compress old logs
        backtrace=True,
        diagnose=True,
    )
    
    # Separate file for errors only
    logger.add(
        LOG_DIR / "jarvis_errors_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="00:00",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
    )
    
    logger.info("JARVIS logging initialized")


def get_logger(name: str) -> "logger":
    """
    Get a logger instance with a specific name.
    
    Args:
        name: The name for the logger (typically __name__).
        
    Returns:
        A loguru logger instance bound to the given name.
    """
    return logger.bind(name=name)


# Export the main logger
__all__ = ["logger", "setup_logging", "get_logger"]
