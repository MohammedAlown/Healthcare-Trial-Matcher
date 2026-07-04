"""
logger.py - Centralized Logging

Sets up a logger that prints formatted messages to the console.
Every module imports this instead of using print() directly,
so we get timestamps, log levels, and consistent formatting.
"""

import logging
import sys


def setup_logger(name: str = "healthcare_matcher") -> logging.Logger:
    """
    Create and configure a logger.

    Args:
        name: Logger name (appears in log output)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only add handler if none exist (prevents duplicate logs)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # Console handler — prints to terminal
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)

        # Format: timestamp | level | module | message
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


# Global logger instance
logger = setup_logger()
