"""
Logging Configuration for AURA Research Agent
Provides structured logging for debugging and monitoring
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# Create logs directory
LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure structured logging for the application.

    Args:
        level: Logging level (default: INFO)
    """
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # File handler (daily log files)
    log_file = LOGS_DIR / f"aura_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Create named loggers for different modules
    loggers = {
        'aura.research': logging.getLogger('aura.research'),
        'aura.agents': logging.getLogger('aura.agents'),
        'aura.database': logging.getLogger('aura.database'),
        'aura.api': logging.getLogger('aura.api')
    }

    # Set levels for all loggers
    for name, logger in loggers.items():
        logger.setLevel(level)

    logging.info("Logging initialized")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: Logger name (e.g., 'aura.research')

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
