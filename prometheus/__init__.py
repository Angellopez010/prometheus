"""
Prometheus - PDF Liberation MCP Server

Like the Titan who stole fire from the gods to give to humanity,
this server takes massive, inaccessible PDFs and breaks them into
digestible chunks that AI can consume.
"""

__version__ = "0.1.0"
__author__ = "Terry"

from .server import app, main

__all__ = ["app", "main"]