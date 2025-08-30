#!/usr/bin/env python3
"""
Prometheus Configuration Management

Professional configuration handling with environment variables and validation.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

# Load environment variables from .env file if it exists
load_dotenv()


class PrometheusConfig(BaseModel):
    """Configuration settings for Prometheus MCP server."""

    # Logging configuration
    log_level: str = Field(
        default=os.getenv("PROMETHEUS_LOG_LEVEL", "INFO"),
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    log_format: str = Field(
        default=os.getenv("PROMETHEUS_LOG_FORMAT", "json"),
        description="Log format (json, text)"
    )

    # Processing limits
    max_file_size_mb: int = Field(
        default=int(os.getenv("PROMETHEUS_MAX_FILE_SIZE_MB", "500")),
        description="Maximum PDF file size in MB"
    )
    max_pages_per_chunk: int = Field(
        default=int(os.getenv("PROMETHEUS_MAX_PAGES_PER_CHUNK", "200")),
        description="Maximum pages per chunk"
    )
    max_token_limit: int = Field(
        default=int(os.getenv("PROMETHEUS_MAX_TOKEN_LIMIT", "32000")),
        description="Maximum tokens per text chunk"
    )

    # Performance settings
    enable_memory_optimization: bool = Field(
        default=os.getenv("PROMETHEUS_MEMORY_OPT", "true").lower() == "true",
        description="Enable memory optimization for large files"
    )
    chunk_processing_timeout: int = Field(
        default=int(os.getenv("PROMETHEUS_TIMEOUT", "300")),
        description="Processing timeout in seconds"
    )

    # Output settings
    default_output_dir: str | None = Field(
        default=os.getenv("PROMETHEUS_OUTPUT_DIR"),
        description="Default output directory for generated files"
    )
    clean_temp_files: bool = Field(
        default=os.getenv("PROMETHEUS_CLEAN_TEMP", "true").lower() == "true",
        description="Automatically clean temporary files"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        valid_formats = {"json", "text"}
        if v.lower() not in valid_formats:
            raise ValueError(f"Invalid log format: {v}. Must be one of {valid_formats}")
        return v.lower()

    @field_validator("default_output_dir")
    @classmethod
    def validate_output_dir(cls, v: str | None) -> str | None:
        if v is not None:
            path = Path(v)
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    raise ValueError(f"Cannot create output directory {v}: {e}")
        return v


# Global configuration instance
config = PrometheusConfig()
