"""
Logging utility for DPA Image Toolkit.

Provides consistent logging interface with levels: info, warning, error, success.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


class ToolkitLogger:
    """Logger for toolkit operations."""

    def __init__(self, name="DPA Image Toolkit", log_file=None):
        """
        Initialize logger.

        Args:
            name (str): Logger name
            log_file (str|Path): Optional path to log file
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Clear existing handlers
        self.logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler (optional)
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def info(self, message):
        """Log info level message."""
        self.logger.info(message)

    def success(self, message):
        """Log success level message (custom level)."""
        self.logger.info(f"✓ {message}")

    def warning(self, message):
        """Log warning level message."""
        self.logger.warning(message)

    def error(self, message):
        """Log error level message."""
        self.logger.error(message)

    def debug(self, message):
        """Log debug level message."""
        self.logger.debug(message)


# Global logger instance
_logger = None


def get_logger(name="DPA Image Toolkit", log_file=None):
    """
    Get or create global logger instance.

    Args:
        name (str): Logger name
        log_file (str|Path): Optional path to log file

    Returns:
        ToolkitLogger: Logger instance
    """
    global _logger
    if _logger is None:
        _logger = ToolkitLogger(name, log_file)
    return _logger


def log_message(message, level="info"):
    """
    Log a message using the global logger.

    Args:
        message (str): Message to log
        level (str): Log level ('info', 'success', 'warning', 'error', 'debug')
    """
    logger = get_logger()
    if level == "info":
        logger.info(message)
    elif level == "success":
        logger.success(message)
    elif level == "warning":
        logger.warning(message)
    elif level == "error":
        logger.error(message)
    elif level == "debug":
        logger.debug(message)
    else:
        logger.info(message)
