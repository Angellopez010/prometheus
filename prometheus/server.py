#!/usr/bin/env python3
"""
Prometheus MCP Server - PDF Liberation Tools

Professional FastMCP server providing PDF manipulation tools for splitting large documents
into digestible chunks that Claude can process effectively. Features structured logging,
configuration management, and robust error handling.
"""

import sys
from pathlib import Path

from fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator

from .config import config
from .logging_setup import get_logger, setup_logging
from .pdf_utils import (
    PDFError,
    extract_pdf_range,
    extract_text_from_pdf,
    get_pdf_info,
    split_pdf,
)

# Initialize logging before anything else
setup_logging()
logger = get_logger(__name__)

# Create FastMCP app
app = FastMCP("prometheus")


class PDFInfo(BaseModel):
    """Metadata about a PDF file."""
    total_pages: int
    file_size_mb: float
    has_bookmarks: bool
    title: str | None = None
    creator: str | None = None


class SplitOptions(BaseModel):
    """Options for PDF splitting operations with enhanced validation."""
    pages_per_chunk: int = Field(
        default=20,
        gt=0,
        le=config.max_pages_per_chunk,
        description="Pages per chunk"
    )
    output_dir: str | None = Field(default=None, description="Output directory path")
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
    """Options for text extraction with configuration integration."""
    max_tokens_per_chunk: int = Field(
        default=8000,
        gt=100,
        le=config.max_token_limit,
        description="Maximum tokens per text chunk"
    )
    include_page_numbers: bool = Field(default=True)
    clean_text: bool = Field(default=True, description="Remove extra whitespace")
    preserve_formatting: bool = Field(default=False, description="Keep original formatting")


@app.tool()
async def prometheus_info(pdf_path: str) -> dict:
    """Get comprehensive metadata and analysis of a PDF file.

    Analyzes PDF structure, estimates processing complexity, and provides
    intelligent recommendations for optimal chunking strategies.

    Args:
        pdf_path: Path to the PDF file (supports absolute and relative paths)

    Returns:
        Dictionary containing detailed PDF metadata, content analysis, and processing estimates
    """
    try:
        logger.info("PDF info requested", pdf_path=pdf_path)
        result = await get_pdf_info(pdf_path)

        if result["status"] == "success":
            logger.info(
                "PDF analysis successful",
                pages=result["pdf_info"]["total_pages"],
                size_mb=result["pdf_info"]["file_size_mb"]
            )

        return result
    except PDFError as e:
        logger.error("PDF processing error", error=str(e), function="prometheus_info")
        return {"status": "error", "error": str(e)}
    except Exception as e:
        logger.error("Unexpected error", error=str(e), function="prometheus_info")
        return {"status": "error", "error": f"Unexpected error: {e!s}"}


@app.tool()
async def prometheus_split(
    pdf_path: str,
    pages_per_chunk: int = 20,
    output_dir: str | None = None,
    prefix: str = "chunk"
) -> dict:
    """Split a PDF into smaller files while preserving all visual content.

    Like Prometheus stealing fire from the gods, this liberates knowledge
    trapped in massive PDFs by breaking them into digestible portions that
    maintain charts, graphs, and formatting integrity.

    Args:
        pdf_path: Path to the source PDF file
        pages_per_chunk: Number of pages per chunk (1-{config.max_pages_per_chunk})
        output_dir: Output directory (defaults to same dir as source with "_chunks" suffix)
        prefix: Filename prefix for generated chunks

    Returns:
        Dictionary with splitting results, file paths, and processing statistics
    """
    # Validate options with enhanced error messages
    try:
        SplitOptions(
            pages_per_chunk=pages_per_chunk,
            output_dir=output_dir,
            prefix=prefix
        )
    except Exception as e:
        logger.warning("Invalid split options", error=str(e))
        return {"status": "error", "error": f"Invalid options: {e!s}"}

    logger.info(
        "PDF split requested",
        pdf_path=pdf_path,
        pages_per_chunk=pages_per_chunk,
        output_dir=output_dir
    )

    result = await split_pdf(pdf_path, pages_per_chunk, output_dir, prefix)

    if result["status"] == "success":
        logger.info(
            "PDF split successful",
            chunks_created=result["chunks_created"],
            output_dir=result["output_directory"]
        )

    return result


@app.tool()
async def prometheus_extract_text(
    pdf_path: str,
    max_tokens_per_chunk: int = 8000,
    include_page_numbers: bool = True,
    clean_text: bool = True
) -> dict:
    """Extract text from PDF in intelligent, token-aware chunks optimized for LLMs.

    Intelligently extracts and chunks text while respecting token limits and
    preserving document structure. Uses tiktoken for accurate token counting
    and applies advanced text cleaning for optimal AI consumption.

    Args:
        pdf_path: Path to the PDF file
        max_tokens_per_chunk: Maximum tokens per text chunk (100-{config.max_token_limit})
        include_page_numbers: Include page markers for reference tracking
        clean_text: Apply advanced text cleaning for better readability

    Returns:
        Dictionary with extracted text chunks, token statistics, and processing metadata
    """
    # Validate options with detailed error messages
    try:
        ExtractionOptions(
            max_tokens_per_chunk=max_tokens_per_chunk,
            include_page_numbers=include_page_numbers,
            clean_text=clean_text
        )
    except Exception as e:
        logger.warning("Invalid extraction options", error=str(e))
        return {"status": "error", "error": f"Invalid options: {e!s}"}

    logger.info(
        "PDF text extraction requested",
        pdf_path=pdf_path,
        max_tokens=max_tokens_per_chunk,
        clean_text=clean_text
    )

    result = await extract_text_from_pdf(
        pdf_path, max_tokens_per_chunk, include_page_numbers, clean_text
    )

    if result["status"] == "success":
        logger.info(
            "Text extraction successful",
            chunks_created=result["chunks_created"],
            total_tokens=result["total_tokens"]
        )

    return result


@app.tool()
async def prometheus_extract_range(
    pdf_path: str,
    start_page: int,
    end_page: int,
    output_path: str | None = None
) -> dict:
    """Extract a specific page range as a new PDF file with surgical precision.

    Performs targeted extraction of specific pages while maintaining all
    visual elements, formatting, and embedded content. Perfect for isolating
    specific sections, chapters, or appendices.

    Args:
        pdf_path: Path to the source PDF
        start_page: Starting page number (1-indexed)
        end_page: Ending page number (1-indexed, inclusive)
        output_path: Output file path (auto-generated if not provided)

    Returns:
        Dictionary with extraction results and output file information
    """
    logger.info(
        "PDF range extraction requested",
        pdf_path=pdf_path,
        start_page=start_page,
        end_page=end_page
    )

    result = await extract_pdf_range(pdf_path, start_page, end_page, output_path)

    if result["status"] == "success":
        logger.info(
            "Range extraction successful",
            page_range=result["extracted_pages"],
            output_file=result["output_file"]
        )

    return result


def main():
    """Entry point for the Prometheus MCP server with professional startup."""

    # Handle version flag
    if len(sys.argv) > 1 and sys.argv[1] == "--version":
        try:
            from prometheus import __version__
            print(f"Prometheus v{__version__}")
        except ImportError:
            print("Prometheus v0.1.0 (development)")
        return

    # Log startup information
    logger.info(
        "Prometheus MCP Server starting",
        log_level=config.log_level,
        max_file_size_mb=config.max_file_size_mb,
        max_pages_per_chunk=config.max_pages_per_chunk,
        memory_optimization=config.enable_memory_optimization
    )

    try:
        # Run the FastMCP server
        app.run()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error("Server failed to start", error=str(e))
        sys.exit(1)
    finally:
        logger.info("Prometheus MCP Server stopped")


if __name__ == "__main__":
    main()
