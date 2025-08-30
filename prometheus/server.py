#!/usr/bin/env python3
"""
Prometheus MCP Server - PDF Liberation Tools

FastMCP server providing PDF manipulation tools for splitting large documents
into digestible chunks that Claude can process effectively.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Union

import typer
from fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator
from rich.console import Console

from .pdf_utils import (
    get_pdf_info,
    split_pdf,
    extract_text_from_pdf,
    extract_pdf_range,
    count_tokens,
    clean_extracted_text,
)

console = Console()
app = FastMCP("prometheus")


class PDFInfo(BaseModel):
    """Metadata about a PDF file."""
    total_pages: int
    file_size_mb: float
    has_bookmarks: bool
    title: Optional[str] = None
    creator: Optional[str] = None


class SplitOptions(BaseModel):
    """Options for PDF splitting operations."""
    pages_per_chunk: int = Field(default=20, gt=0, le=200, description="Pages per chunk")
    output_dir: Optional[str] = Field(default=None, description="Output directory path")
    preserve_bookmarks: bool = Field(default=True, description="Keep PDF bookmarks")
    prefix: str = Field(default="chunk", description="Filename prefix for chunks")
    
    @field_validator("output_dir")
    @classmethod
    def validate_output_dir(cls, v):
        if v is not None:
            path = Path(v)
            if not path.parent.exists():
                raise ValueError(f"Parent directory does not exist: {path.parent}")
        return v


class ExtractionOptions(BaseModel):
    """Options for text extraction."""
    max_tokens_per_chunk: int = Field(default=8000, gt=100, le=32000)
    include_page_numbers: bool = Field(default=True)
    clean_text: bool = Field(default=True, description="Remove extra whitespace")
    preserve_formatting: bool = Field(default=False, description="Keep original formatting")


# Utility functions are now imported from pdf_utils module


@app.tool()
async def prometheus_info(pdf_path: str) -> Dict:
    """Get metadata and basic information about a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary containing PDF metadata and analysis
    """
    return await get_pdf_info(pdf_path)


@app.tool()
async def prometheus_split(
    pdf_path: str,
    pages_per_chunk: int = 20,
    output_dir: Optional[str] = None,
    prefix: str = "chunk"
) -> Dict:
    """Split a PDF into smaller PDF files preserving all visual content.
    
    Like Prometheus stealing fire from the gods, this liberates knowledge
    trapped in massive PDFs by breaking them into digestible portions.
    
    Args:
        pdf_path: Path to the source PDF file
        pages_per_chunk: Number of pages per chunk (1-200)
        output_dir: Output directory (defaults to same dir as source)
        prefix: Filename prefix for chunks
        
    Returns:
        Dictionary with splitting results and file paths
    """
    # Validate options first
    try:
        options = SplitOptions(
            pages_per_chunk=pages_per_chunk,
            output_dir=output_dir,
            prefix=prefix
        )
    except Exception as e:
        return {"status": "error", "error": f"Invalid options: {str(e)}"}
    
    return await split_pdf(pdf_path, pages_per_chunk, output_dir, prefix)


@app.tool()
async def prometheus_extract_text(
    pdf_path: str,
    max_tokens_per_chunk: int = 8000,
    include_page_numbers: bool = True,
    clean_text: bool = True
) -> Dict:
    """Extract text from PDF in token-aware chunks for LLM consumption.
    
    Intelligently extracts and chunks text while respecting token limits,
    making large documents accessible to language models.
    
    Args:
        pdf_path: Path to the PDF file
        max_tokens_per_chunk: Maximum tokens per text chunk
        include_page_numbers: Include page markers in text
        clean_text: Clean extracted text for better readability
        
    Returns:
        Dictionary with extracted text chunks and metadata
    """
    # Validate options first
    try:
        options = ExtractionOptions(
            max_tokens_per_chunk=max_tokens_per_chunk,
            include_page_numbers=include_page_numbers,
            clean_text=clean_text
        )
    except Exception as e:
        return {"status": "error", "error": f"Invalid options: {str(e)}"}
    
    return await extract_text_from_pdf(
        pdf_path, max_tokens_per_chunk, include_page_numbers, clean_text
    )


@app.tool()
async def prometheus_extract_range(
    pdf_path: str,
    start_page: int,
    end_page: int,
    output_path: Optional[str] = None
) -> Dict:
    """Extract a specific page range as a new PDF file.
    
    Surgical extraction of specific pages for targeted analysis.
    
    Args:
        pdf_path: Path to the source PDF
        start_page: Starting page number (1-indexed)
        end_page: Ending page number (1-indexed, inclusive)
        output_path: Output file path (optional)
        
    Returns:
        Dictionary with extraction results
    """
    return await extract_pdf_range(pdf_path, start_page, end_page, output_path)


def main():
    """Entry point for the Prometheus MCP server."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--version":
        from prometheus import __version__
        print(f"Prometheus v{__version__}")
        return
    
    # Run the FastMCP server
    app.run()


if __name__ == "__main__":
    main()