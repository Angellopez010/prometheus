"""
Prometheus - PDF Liberation MCP Server

Like the Titan who stole fire from the gods to give to humanity,
this server takes massive, inaccessible PDFs and breaks them into
digestible chunks that AI can consume.

Professional MCP server with structured logging, configuration management,
and robust error handling for production-grade PDF processing.
"""

__version__ = "0.2.0"  # Bumped for professional improvements
__author__ = "Terry"

from .config import config
from .logging_setup import get_logger, setup_logging
from .pdf_utils import PDFError
from .server import app, main

__all__ = ["PDFError", "app", "config", "get_logger", "main", "setup_logging"]
