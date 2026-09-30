"""
Logging utilities for the forensics platform.

Provides application-wide logging with rotation and multiple log levels.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        """Format log record with colors"""
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logging(
    log_dir: Path,
    log_level: str = "INFO",
    max_bytes: int = 100 * 1024 * 1024,  # 100MB
    backup_count: int = 5,
    console_output: bool = True
) -> logging.Logger:
    """
    Setup application logging.

    Args:
        log_dir: Directory for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
        console_output: Whether to output to console

    Returns:
        Configured logger
    """
    # Create log directory
    log_dir.mkdir(parents=True, exist_ok=True)

    # Get root logger
    logger = logging.getLogger("forensics_platform")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # File formatter (detailed)
    file_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console formatter (simpler, colored)
    console_formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )

    # Application log file handler (rotating)
    app_log_file = log_dir / "application.log"
    app_handler = RotatingFileHandler(
        app_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    app_handler.setLevel(logging.DEBUG)
    app_handler.setFormatter(file_formatter)
    logger.addHandler(app_handler)

    # Error log file handler (only errors and above)
    error_log_file = log_dir / "errors.log"
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # Log startup message
    logger.info("=" * 80)
    logger.info(f"Forensics Platform - Logging initialized at {datetime.now().isoformat()}")
    logger.info(f"Log level: {log_level}")
    logger.info(f"Log directory: {log_dir}")
    logger.info("=" * 80)

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (usually __name__). If None, returns root platform logger.

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"forensics_platform.{name}")
    return logging.getLogger("forensics_platform")


class OperationLogger:
    """Logger for specific operations with structured logging"""

    def __init__(self, operation_type: str, operation_id: int):
        """
        Initialize operation logger.

        Args:
            operation_type: Type of operation (e.g., 'carving', 'sanitization')
            operation_id: Operation ID from database
        """
        self.operation_type = operation_type
        self.operation_id = operation_id
        self.logger = get_logger(f"operations.{operation_type}")

    def log(self, level: str, message: str, **kwargs):
        """Log with operation context"""
        context = f"[{self.operation_type}:{self.operation_id}]"
        extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
        full_message = f"{context} {message}"
        if extra_info:
            full_message += f" | {extra_info}"

        log_func = getattr(self.logger, level.lower())
        log_func(full_message)

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self.log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message"""
        self.log("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.log("CRITICAL", message, **kwargs)


def create_operation_log_file(log_dir: Path, operation_id: int, operation_type: str) -> Path:
    """
    Create a dedicated log file for an operation.

    Args:
        log_dir: Base log directory
        operation_id: Operation ID
        operation_type: Type of operation

    Returns:
        Path to operation log file
    """
    operations_log_dir = log_dir / "operations"
    operations_log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = operations_log_dir / f"{operation_type}_{operation_id}_{timestamp}.log"

    # Create empty log file
    log_file.touch()

    return log_file


# Module-level logger initialization flag
_logging_initialized = False


def ensure_logging_initialized():
    """Ensure logging is initialized (called automatically)"""
    global _logging_initialized
    if not _logging_initialized:
        # Use default configuration if not explicitly initialized
        from forensics_platform.core.config import get_config
        config = get_config()
        setup_logging(
            log_dir=config.log_dir,
            log_level=config.log_level
        )
        _logging_initialized = True
