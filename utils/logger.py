"""
Recepta - Logging Utility
Centralized logging with rotation and structured output.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config.settings import LOGS_DIR, DEBUG, LOG_LEVEL


def setup_logger(name: str = "recepta") -> logging.Logger:
    """
    Create and configure a logger instance.

    Args:
        name: Logger name (usually __name__ from the calling module)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    # Set level from config
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    # ─── Console Handler (stdout) ──────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    # ─── File Handler (rotating) ───────────────────────────────────────────
    log_file = LOGS_DIR / f"{name}.log"
    file_handler = RotatingFileHandler(
        log_file,
        max_bytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
    )
    file_handler.setLevel(level)
    file_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    # ─── Error File Handler (separate for errors) ─────────────────────────
    error_log_file = LOGS_DIR / f"{name}_error.log"
    error_handler = RotatingFileHandler(
        error_log_file,
        max_bytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_fmt)
    logger.addHandler(error_handler)

    return logger


def get_logger(name: str = "recepta") -> logging.Logger:
    """
    Get a logger instance (convenience function).

    Usage:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Pipeline started")
    """
    return setup_logger(name)
