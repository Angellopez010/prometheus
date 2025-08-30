"""
PDF utility functions for Prometheus.

Professional PDF processing with memory optimization, error handling, and logging.
These functions are used both by the MCP server and the CLI.
"""

import asyncio
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import fitz  # PyMuPDF
import tiktoken

from .config import config
from .logging_setup import get_logger

# Global encoder for token counting
encoder = tiktoken.get_encoding("cl100k_base")
logger = get_logger(__name__)


class PDFError(Exception):
    """Custom exception for PDF processing errors."""
    pass


@contextmanager
def safe_pdf_context(pdf_path: str) -> Iterator[fitz.Document]:
    """Context manager for safe PDF operations with proper cleanup."""
    doc = None
    try:
        # Validate file exists and size
        path = Path(pdf_path)
        if not path.exists():
            raise PDFError(f"PDF file not found: {pdf_path}")

        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > config.max_file_size_mb:
            raise PDFError(f"PDF file too large: {file_size_mb:.1f}MB (max: {config.max_file_size_mb}MB)")

        logger.info("Opening PDF", file_path=pdf_path, size_mb=file_size_mb)

        # Open PDF with error handling
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            if "password" in str(e).lower():
                raise PDFError("PDF is password protected") from e
            elif "corrupt" in str(e).lower():
                raise PDFError("PDF file appears to be corrupted") from e
            else:
                raise PDFError(f"Failed to open PDF: {e!s}") from e

        # Validate PDF has pages
        if len(doc) == 0:
            raise PDFError("PDF has no pages")

        yield doc

    finally:
        if doc:
            doc.close()
            logger.debug("PDF closed successfully")


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken with error handling."""
    try:
        return len(encoder.encode(text))
    except Exception as e:
        logger.warning("Token counting failed", error=str(e))
        # Fallback to rough estimation
        return len(text) // 4


def clean_extracted_text(text: str) -> str:
    """Clean extracted text for better readability with enhanced patterns."""
    if not text:
        return ""

    # Remove excessive whitespace
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)

    # Remove standalone numbers that are likely page artifacts
    text = re.sub(r'\n\d+\n', '\n', text)

    # Remove common PDF artifacts
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)  # Control characters
    text = re.sub(r'\u2022\s*', '• ', text)  # Normalize bullet points

    # Fix common spacing issues
    text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)  # Sentence spacing

    return text.strip()


async def process_with_timeout(coro, timeout_seconds: int | None = None):
    """Execute coroutine with configurable timeout."""
    timeout = timeout_seconds or config.chunk_processing_timeout
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except TimeoutError as e:
        raise PDFError(f"Processing timed out after {timeout} seconds") from e


async def get_pdf_info(pdf_path: str) -> dict:
    """Get metadata and basic information about a PDF file with enhanced analytics."""
    try:
        with safe_pdf_context(pdf_path) as doc:
            path = Path(pdf_path)
            file_size_mb = path.stat().st_size / (1024 * 1024)

            # PDF metadata with null checking
            metadata = doc.metadata or {}
            has_bookmarks = len(doc.get_toc()) > 0
            total_pages = len(doc)

            # Enhanced processing estimates
            estimated_chunks = {
                "5_pages": (total_pages + 4) // 5,
                "10_pages": (total_pages + 9) // 10,
                "20_pages": (total_pages + 19) // 20,
                "50_pages": (total_pages + 49) // 50,
            }

            # Smart recommendations based on file characteristics
            if file_size_mb > 50:  # Large files
                recommended_chunk_size = 10
                complexity = "high"
            elif total_pages > 200:  # Many pages
                recommended_chunk_size = 15
                complexity = "medium"
            elif has_bookmarks:  # Well-structured
                recommended_chunk_size = 25
                complexity = "low"
            else:
                recommended_chunk_size = 20
                complexity = "medium"

            # Sample a few pages to estimate content density
            sample_pages = min(3, total_pages)
            sample_text_length = 0

            for i in range(sample_pages):
                try:
                    page_text = doc[i].get_text()
                    sample_text_length += len(page_text)
                except Exception:
                    continue

            avg_chars_per_page = sample_text_length / sample_pages if sample_pages > 0 else 0
            estimated_tokens = (total_pages * avg_chars_per_page) // 4

            logger.info(
                "PDF analysis complete",
                pages=total_pages,
                size_mb=file_size_mb,
                complexity=complexity,
                estimated_tokens=estimated_tokens
            )

            return {
                "status": "success",
                "pdf_info": {
                    "total_pages": total_pages,
                    "file_size_mb": round(file_size_mb, 2),
                    "has_bookmarks": has_bookmarks,
                    "title": metadata.get("title", "").strip() or None,
                    "creator": metadata.get("creator", "").strip() or None,
                    "subject": metadata.get("subject", "").strip() or None,
                    "creation_date": metadata.get("creationDate", "").strip() or None,
                    "avg_chars_per_page": round(avg_chars_per_page),
                    "estimated_total_tokens": estimated_tokens,
                },
                "processing_estimates": {
                    "estimated_chunks": estimated_chunks,
                    "recommended_chunk_size": recommended_chunk_size,
                    "complexity_level": complexity,
                    "processing_time_estimate_minutes": max(1, total_pages // 50),
                }
            }

    except PDFError:
        # Re-raise our custom errors
        raise
    except Exception as e:
        logger.error("Unexpected error in PDF analysis", error=str(e), pdf_path=pdf_path)
        return {
            "status": "error",
            "error": f"Failed to read PDF: {e!s}"
        }


async def split_pdf(
    pdf_path: str,
    pages_per_chunk: int = 20,
    output_dir: str | None = None,
    prefix: str = "chunk"
) -> dict:
    """Split a PDF into smaller PDF files preserving all visual content."""
    try:
        source_path = Path(pdf_path)
        if not source_path.exists():
            return {"status": "error", "error": f"PDF file not found: {pdf_path}"}

        # Determine output directory
        if output_dir:
            out_dir = Path(output_dir)
        else:
            out_dir = source_path.parent / f"{source_path.stem}_chunks"

        out_dir.mkdir(exist_ok=True)

        # Open source PDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)

        if total_pages == 0:
            doc.close()
            return {"status": "error", "error": "PDF has no pages"}

        chunks_created = []
        chunk_count = 0

        for start_page in range(0, total_pages, pages_per_chunk):
            end_page = min(start_page + pages_per_chunk, total_pages)
            chunk_count += 1

            # Create new PDF for this chunk
            chunk_doc = fitz.open()

            # Copy pages to new PDF
            for page_num in range(start_page, end_page):
                chunk_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

            # Save chunk PDF
            chunk_file = out_dir / f"{prefix}_{chunk_count:02d}_pages_{start_page + 1:03d}-{end_page:03d}.pdf"
            chunk_doc.save(chunk_file)
            chunk_doc.close()

            chunks_created.append({
                "chunk_id": chunk_count,
                "file_path": str(chunk_file),
                "pages": f"{start_page + 1}-{end_page}",
                "page_count": end_page - start_page
            })

        doc.close()

        return {
            "status": "success",
            "message": f"Successfully split PDF into {chunk_count} chunks",
            "source_pdf": str(source_path),
            "output_directory": str(out_dir),
            "chunks_created": len(chunks_created),
            "chunks": chunks_created
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to split PDF: {e!s}"
        }


async def extract_text_from_pdf(
    pdf_path: str,
    max_tokens_per_chunk: int = 8000,
    include_page_numbers: bool = True,
    clean_text: bool = True
) -> dict:
    """Extract text from PDF in token-aware chunks for LLM consumption."""
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)

        chunks = []
        current_chunk = ""
        current_tokens = 0
        chunk_id = 1
        pages_in_chunk = []

        for page_num in range(total_pages):
            page = doc[page_num]

            # Extract text from page
            page_text = page.get_text()

            if clean_text:
                page_text = clean_extracted_text(page_text)

            # Add page marker if requested
            if include_page_numbers:
                page_header = f"\n--- Page {page_num + 1} ---\n"
                page_content = page_header + page_text
            else:
                page_content = page_text

            # Count tokens for this page
            page_tokens = count_tokens(page_content)

            # Check if adding this page would exceed token limit
            if current_tokens + page_tokens > max_tokens_per_chunk and current_chunk:
                # Save current chunk
                chunks.append({
                    "chunk_id": chunk_id,
                    "text": current_chunk.strip(),
                    "token_count": current_tokens,
                    "pages": pages_in_chunk.copy(),
                    "page_range": f"{pages_in_chunk[0]}-{pages_in_chunk[-1]}" if pages_in_chunk else ""
                })

                # Start new chunk
                chunk_id += 1
                current_chunk = page_content
                current_tokens = page_tokens
                pages_in_chunk = [page_num + 1]

            else:
                # Add to current chunk
                current_chunk += page_content
                current_tokens += page_tokens
                pages_in_chunk.append(page_num + 1)

        # Don't forget the last chunk
        if current_chunk:
            chunks.append({
                "chunk_id": chunk_id,
                "text": current_chunk.strip(),
                "token_count": current_tokens,
                "pages": pages_in_chunk.copy(),
                "page_range": f"{pages_in_chunk[0]}-{pages_in_chunk[-1]}" if pages_in_chunk else ""
            })

        doc.close()

        # Calculate statistics
        total_tokens = sum(chunk["token_count"] for chunk in chunks)
        avg_tokens_per_chunk = total_tokens / len(chunks) if chunks else 0

        return {
            "status": "success",
            "source_pdf": str(Path(pdf_path).name),
            "total_pages": total_pages,
            "chunks_created": len(chunks),
            "total_tokens": total_tokens,
            "avg_tokens_per_chunk": round(avg_tokens_per_chunk),
            "max_tokens_per_chunk": max(chunk["token_count"] for chunk in chunks) if chunks else 0,
            "chunks": chunks
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to extract text: {e!s}"
        }


async def extract_pdf_range(
    pdf_path: str,
    start_page: int,
    end_page: int,
    output_path: str | None = None
) -> dict:
    """Extract a specific page range as a new PDF file."""
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)

        # Validate page range
        if start_page < 1 or end_page > total_pages or start_page > end_page:
            doc.close()
            return {
                "status": "error",
                "error": f"Invalid page range {start_page}-{end_page}. PDF has {total_pages} pages."
            }

        # Determine output path
        source_path = Path(pdf_path)
        if not output_path:
            output_path = source_path.parent / f"{source_path.stem}_pages_{start_page}-{end_page}.pdf"
        else:
            output_path = Path(output_path)

        # Create new PDF with specified pages
        new_doc = fitz.open()

        for page_num in range(start_page - 1, end_page):  # Convert to 0-indexed
            new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

        new_doc.save(output_path)
        new_doc.close()
        doc.close()

        return {
            "status": "success",
            "source_pdf": str(source_path),
            "extracted_pages": f"{start_page}-{end_page}",
            "page_count": end_page - start_page + 1,
            "output_file": str(output_path)
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to extract page range: {e!s}"
        }
