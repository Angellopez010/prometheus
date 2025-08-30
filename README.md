# Prometheus - PDF Liberation MCP Server

> Like the Titan who stole fire from the gods to give to humanity, this server takes massive, inaccessible PDFs and breaks them into digestible chunks that AI can consume.

## Overview

Prometheus is a FastMCP server that provides PDF processing tools for Claude Code. It intelligently splits large PDF documents into manageable chunks while preserving visual content and respecting token limits, making massive documents accessible to language models.

## Features

### Core Tools

- **`prometheus_info`** - Get comprehensive PDF metadata and processing estimates
- **`prometheus_split`** - Split PDFs into smaller files preserving all visual content
- **`prometheus_extract_text`** - Extract text with intelligent token-aware chunking
- **`prometheus_extract_range`** - Extract specific page ranges as new PDFs

### Key Capabilities

- **Visual Preservation**: Maintains charts, graphs, and formatting when splitting PDFs
- **Token-Aware Processing**: Chunks text based on actual token counts, not arbitrary limits
- **Smart Text Cleaning**: Removes artifacts and excessive whitespace for better readability
- **Flexible Output**: Save to custom directories with customizable naming
- **Progress Tracking**: Rich console output for development and testing

## Modern Python Stack

- **uv** - Lightning-fast package management
- **ruff** - Ultra-fast linting and formatting
- **FastMCP** - Simplified MCP server creation
- **PyMuPDF** - Industrial-strength PDF processing
- **tiktoken** - Accurate token counting for LLMs
- **Rich/Typer** - Beautiful CLI interfaces

## Installation

```bash
cd ~/conductor/prometheus

# Install with uv (recommended)
uv venv
uv pip install -e .

# Or with pip
pip install -e .
```

## Usage

### MCP Server Mode

Configure in your Claude Code MCP settings:

```json
{
  "prometheus": {
    "command": "uv",
    "args": ["run", "prometheus"],
    "env": {
      "PROMETHEUS_LOG_LEVEL": "INFO"
    }
  }
}
```

### Standalone CLI Testing

```bash
# Get PDF information
python scripts/test_cli.py info /path/to/document.pdf

# Split PDF into 20-page chunks
python scripts/test_cli.py split /path/to/document.pdf --pages 20

# Extract text with token awareness
python scripts/test_cli.py extract /path/to/document.pdf --tokens 8000

# Extract specific pages
python scripts/test_cli.py extract-range /path/to/document.pdf 10 20

# Run full demo
python scripts/test_cli.py demo /path/to/document.pdf
```

### Python API Usage

```python
from prometheus.server import (
    prometheus_info,
    prometheus_split, 
    prometheus_extract_text
)

# Get PDF metadata
info = await prometheus_info("/path/to/document.pdf")
print(f"Pages: {info['pdf_info']['total_pages']}")

# Split preserving visuals
result = await prometheus_split(
    pdf_path="/path/to/document.pdf",
    pages_per_chunk=20,
    output_dir="/output/path"
)

# Extract token-aware text chunks
text_result = await prometheus_extract_text(
    pdf_path="/path/to/document.pdf",
    max_tokens_per_chunk=8000,
    clean_text=True
)
```

## Development

### Setup Development Environment

```bash
cd ~/conductor/prometheus
uv venv
uv pip install -e ".[dev]"
```

### Code Quality

```bash
# Format and lint
uv run ruff format .
uv run ruff check .

# Type checking
uv run mypy prometheus/

# Run tests
uv run pytest
uv run pytest -m integration  # Integration tests with real PDFs
```

### Project Structure

```
prometheus/
├── pyproject.toml          # Modern Python configuration
├── prometheus/
│   ├── __init__.py
│   └── server.py           # FastMCP server implementation
├── tests/
│   ├── __init__.py
│   └── test_basic.py       # Unit and integration tests
├── scripts/
│   └── test_cli.py         # Standalone CLI for testing
└── README.md
```

## Architecture

### Why FastMCP + Python?

1. **Mature PDF Libraries**: PyMuPDF handles complex PDFs that JavaScript libraries struggle with
2. **Code Reuse**: Leverages existing PDF processing scripts
3. **FastMCP Simplicity**: ~50 lines vs ~200 lines for equivalent JavaScript
4. **Token Precision**: tiktoken provides accurate token counting for LLMs
5. **Rich Development Experience**: Modern tooling with instant feedback

### Design Philosophy

Following Terry's sustainable systems approach:

- **Minimal Boilerplate**: FastMCP decorators over complex server setup
- **Type Safety**: Pydantic models prevent runtime errors
- **Fast Feedback**: Ruff checks in milliseconds preserve flow state
- **Token Efficiency**: Intelligent chunking maximizes context utilization
- **Visual Preservation**: Maintains document integrity for complex reports

## Common Use Cases

### Banking Document Analysis
```bash
# Split 300-page banking regulation PDF
python scripts/test_cli.py split bank_regulations.pdf --pages 25

# Extract text for AI analysis
python scripts/test_cli.py extract bank_regulations.pdf --tokens 6000
```

### Research Paper Processing
```bash
# Get paper info first
python scripts/test_cli.py info research_paper.pdf

# Extract specific sections
python scripts/test_cli.py extract-range research_paper.pdf 10 25
```

### Large Report Chunking
```bash
# Smart splitting with visual preservation
python scripts/test_cli.py split quarterly_report.pdf --pages 15 --prefix report
```

## Troubleshooting

### Common Issues

1. **"PDF file not found"**
   - Verify file path is absolute
   - Check file permissions

2. **"Failed to read PDF"**
   - PDF may be corrupted or password-protected
   - Try with a different PDF file

3. **Token counting issues**
   - Ensure tiktoken is installed: `uv pip install tiktoken`

### Performance Tips

- Use 10-20 pages per chunk for documents with heavy visuals
- Adjust token limits based on your LLM's context window
- Enable text cleaning for better readability
- Use specific page ranges for targeted analysis

## Contributing

1. Follow the modern Python stack conventions
2. Run `ruff format && ruff check` before committing
3. Add tests for new functionality
4. Update documentation for API changes

## License

MIT License - See LICENSE file for details.