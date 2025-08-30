#!/usr/bin/env python3
"""
Prometheus Structured Logging Setup

Professional logging configuration using structlog for better observability.
"""

import logging.config
import sys
from typing import Any

import structlog

from .config import config


def setup_logging() -> None:
    """Configure structured logging for Prometheus."""

    # Configure standard logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "plain": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": (
                    structlog.dev.ConsoleRenderer()
                    if config.log_format == "text"
                    else structlog.processors.JSONRenderer()
                ),
            },
        },
        "handlers": {
            "default": {
                "level": config.log_level,
                "class": "logging.StreamHandler",
                "formatter": "plain",
                "stream": sys.stdout,
            },
        },
        "loggers": {
            "": {
                "handlers": ["default"],
                "level": config.log_level,
                "propagate": True,
            }
        }
    }

    logging.config.dictConfig(logging_config)

    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    # Add correlation ID processor for request tracking
    processors.insert(-1, add_correlation_id)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def add_correlation_id(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Add correlation ID for request tracking."""
    # Simple correlation ID - in production, this might come from request context
    import uuid
    if "correlation_id" not in event_dict:
        event_dict["correlation_id"] = str(uuid.uuid4())[:8]
    return event_dict


def get_logger(name: str = "prometheus") -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)
