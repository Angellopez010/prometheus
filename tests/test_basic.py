"""
Basic tests for Prometheus PDF processing tools.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from prometheus.server import count_tokens, clean_extracted_text


def test_count_tokens():
    """Test token counting functionality."""
    # Simple text
    assert count_tokens("hello world") > 0
    
    # Empty text
    assert count_tokens("") == 0
    
    # Longer text should have more tokens
    short_text = "hello"
    long_text = "hello " * 100
    assert count_tokens(long_text) > count_tokens(short_text)


def test_clean_extracted_text():
    """Test text cleaning functionality."""
    # Test excessive whitespace removal
    messy_text = "line 1\n\n\n\nline 2\n   \nline 3"
    cleaned = clean_extracted_text(messy_text)
    
    # Should not have triple newlines
    assert "\n\n\n" not in cleaned
    
    # Test multiple spaces
    spaced_text = "word1    word2      word3"
    cleaned_spaced = clean_extracted_text(spaced_text)
    assert "  " not in cleaned_spaced
    
    # Test standalone numbers (page artifacts)
    numbered_text = "Some text\n42\nMore text"
    cleaned_numbered = clean_extracted_text(numbered_text)
    assert "\n42\n" not in cleaned_numbered


@pytest.mark.asyncio
async def test_prometheus_info_missing_file():
    """Test info tool with non-existent file."""
    from prometheus.server import prometheus_info
    
    result = await prometheus_info("/nonexistent/file.pdf")
    assert result["status"] == "error"
    assert "Failed to read PDF" in result["error"]


def test_validation_models():
    """Test Pydantic models validation."""
    from prometheus.server import SplitOptions, ExtractionOptions
    
    # Test valid SplitOptions
    options = SplitOptions(pages_per_chunk=20)
    assert options.pages_per_chunk == 20
    
    # Test invalid pages_per_chunk (too high)
    with pytest.raises(ValueError):
        SplitOptions(pages_per_chunk=500)
    
    # Test invalid pages_per_chunk (too low)
    with pytest.raises(ValueError):
        SplitOptions(pages_per_chunk=0)
    
    # Test valid ExtractionOptions
    extract_opts = ExtractionOptions(max_tokens_per_chunk=4000)
    assert extract_opts.max_tokens_per_chunk == 4000
    
    # Test invalid token limit (too high)
    with pytest.raises(ValueError):
        ExtractionOptions(max_tokens_per_chunk=50000)


# Integration test that requires actual PDF
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_workflow_with_sample_pdf():
    """Integration test with a real PDF file (if available)."""
    from prometheus.server import prometheus_info, prometheus_split
    
    # Look for Meeker PDF in common location
    sample_pdf = "/Users/terry/Downloads/Trends_Artificial_Intelligence.pdf"
    
    if not Path(sample_pdf).exists():
        pytest.skip("Sample PDF not available for integration test")
    
    # Test info extraction
    info_result = await prometheus_info(sample_pdf)
    assert info_result["status"] == "success"
    assert info_result["pdf_info"]["total_pages"] > 0
    
    # Test small split operation
    with tempfile.TemporaryDirectory() as temp_dir:
        split_result = await prometheus_split(
            pdf_path=sample_pdf,
            pages_per_chunk=5,
            output_dir=temp_dir,
            prefix="test"
        )
        
        if split_result["status"] == "success":
            assert split_result["chunks_created"] > 0
            # Check that files were actually created
            output_dir = Path(temp_dir)
            pdf_files = list(output_dir.glob("*.pdf"))
            assert len(pdf_files) > 0


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])