"""
Structured JSON Logging Utility
Provides centralized structured logging for the AURA Research Agent
"""

import logging
import sys
import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger
import os


class StructuredLogger:
    """
    Centralized structured logging with JSON output for production observability.
    Includes request tracing, context propagation, and structured fields.
    """

    def __init__(self, name: str, level: str = "INFO"):
        """
        Initialize structured logger.

        Args:
            name: Logger name (usually __name__)
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        self.name = name
        self.request_id = None
        self.context: Dict[str, Any] = {}

        # Remove any existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Create console handler with JSON formatter
        console_handler = logging.StreamHandler(sys.stdout)

        # Custom JSON formatter
        formatter = jsonlogger.JsonFormatter(
            fmt='%(timestamp)s %(level)s %(name)s %(message)s %(request_id)s %(context)s %(extra_fields)s',
            rename_fields={'timestamp': 'timestamp', 'level': 'levelname'},
            static_fields={'service': 'aura_research'}
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def set_request_id(self, request_id: Optional[str] = None) -> str:
        """
        Set or generate request ID for tracing.

        Args:
            request_id: Optional request ID (will generate if None)

        Returns:
            The request ID being used
        """
        if request_id is None:
            request_id = str(uuid.uuid4())
        self.request_id = request_id
        return request_id

    def set_context(self, **kwargs) -> None:
        """
        Set context fields that will be included in all subsequent logs.

        Args:
            **kwargs: Context key-value pairs (e.g., user_id=123, session_id="abc")
        """
        self.context.update(kwargs)

    def clear_context(self) -> None:
        """Clear all context fields."""
        self.context.clear()
        self.request_id = None

    def _add_extra_fields(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Merge extra fields with context and request tracking.

        Args:
            extra: Additional fields to include

        Returns:
            Dictionary with all fields to be logged
        """
        fields = {
            'timestamp': datetime.utcnow().isoformat(),
            'request_id': self.request_id or 'none',
            'context': self.context if self.context else {},
            'extra_fields': extra or {}
        }
        return fields

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log debug message with structured fields."""
        self.logger.debug(message, extra=self._add_extra_fields(extra or kwargs))

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log info message with structured fields."""
        self.logger.info(message, extra=self._add_extra_fields(extra or kwargs))

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log warning message with structured fields."""
        self.logger.warning(message, extra=self._add_extra_fields(extra or kwargs))

    def error(self, message: str, exc_info: bool = False, extra: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log error message with structured fields."""
        self.logger.error(
            message,
            exc_info=exc_info,
            extra=self._add_extra_fields(extra or kwargs)
        )

    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log critical message with structured fields."""
        self.logger.critical(message, extra=self._add_extra_fields(extra or kwargs))

    def exception(self, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log exception with full traceback and structured fields."""
        self.logger.exception(message, extra=self._add_extra_fields(extra or kwargs))


def get_logger(name: str, level: Optional[str] = None) -> StructuredLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)
        level: Optional logging level (defaults to INFO or env var LOG_LEVEL)

    Returns:
        StructuredLogger instance
    """
    if level is None:
        level = os.getenv('LOG_LEVEL', 'INFO')

    return StructuredLogger(name, level=level)
