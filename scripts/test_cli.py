#!/usr/bin/env python3
"""
Prometheus Test CLI

Standalone CLI for testing PDF processing functionality before MCP integration.
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Import our utility functions directly
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from prometheus.pdf_utils import (
    get_pdf_info,
    split_pdf,
    extract_text_from_pdf,
    extract_pdf_range,
)

console = Console()
app = typer.Typer(
    name="prometheus-cli",
    help="Test CLI for Prometheus PDF liberation tools",
    rich_markup_mode="rich"
)


@app.command()
def info(
    pdf_path: str = typer.Argument(..., help="Path to PDF file"),
):
    """Get information about a PDF file."""
    
    async def run_info():
        result = await get_pdf_info(pdf_path)
        
        if result["status"] == "error":
            console.print(f"[red]Error:[/red] {result['error']}")
            return
        
        # Display PDF info in a nice table
        info_data = result["pdf_info"]
        estimates = result["processing_estimates"]
        
        table = Table(title="PDF Information")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("File", Path(pdf_path).name)
        table.add_row("Total Pages", str(info_data["total_pages"]))
        table.add_row("File Size", f"{info_data['file_size_mb']} MB")
        table.add_row("Has Bookmarks", "Yes" if info_data["has_bookmarks"] else "No")
        
        if info_data["title"]:
            table.add_row("Title", info_data["title"])
        if info_data["creator"]:
            table.add_row("Creator", info_data["creator"])
            
        console.print(table)
        
        # Estimates
        est_table = Table(title="Processing Estimates")
        est_table.add_column("Chunk Size", style="cyan")
        est_table.add_column("Chunks", style="white")
        
        for chunk_size, count in estimates["estimated_chunks"].items():
            est_table.add_row(chunk_size.replace("_", " "), str(count))
            
        est_table.add_row(
            "[bold]Recommended[/bold]", 
            f"[green]{estimates['recommended_chunk_size']} pages[/green]"
        )
        
        console.print(est_table)
    
    asyncio.run(run_info())


@app.command()
def split(
    pdf_path: str = typer.Argument(..., help="Path to PDF file"),
    pages_per_chunk: int = typer.Option(20, "--pages", "-p", help="Pages per chunk"),
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory"),
    prefix: str = typer.Option("chunk", "--prefix", help="Filename prefix"),
):
    """Split PDF into smaller chunks."""
    
    async def run_split():
        with console.status("[green]Splitting PDF...") as status:
            result = await split_pdf(
                pdf_path=pdf_path,
                pages_per_chunk=pages_per_chunk,
                output_dir=output_dir,
                prefix=prefix
            )
        
        if result["status"] == "error":
            console.print(f"[red]Error:[/red] {result['error']}")
            return
        
        # Success message
        panel = Panel(
            f"[green]✓[/green] {result['message']}\n\n"
            f"[cyan]Source:[/cyan] {Path(result['source_pdf']).name}\n"
            f"[cyan]Output:[/cyan] {result['output_directory']}\n"
            f"[cyan]Chunks:[/cyan] {result['chunks_created']}",
            title="Split Complete",
            border_style="green"
        )
        console.print(panel)
        
        # Show chunk details
        if result.get("chunks"):
            table = Table(title="Created Chunks")
            table.add_column("Chunk", style="cyan")
            table.add_column("Pages", style="white")
            table.add_column("File", style="yellow")
            
            for chunk in result["chunks"][:10]:  # Show first 10
                table.add_row(
                    str(chunk["chunk_id"]),
                    chunk["pages"],
                    Path(chunk["file_path"]).name
                )
            
            if len(result["chunks"]) > 10:
                table.add_row("...", "...", f"and {len(result['chunks']) - 10} more")
            
            console.print(table)
    
    asyncio.run(run_split())


@app.command()
def extract(
    pdf_path: str = typer.Argument(..., help="Path to PDF file"),
    max_tokens: int = typer.Option(8000, "--tokens", "-t", help="Max tokens per chunk"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Save to JSON file"),
    clean: bool = typer.Option(True, "--clean/--raw", help="Clean extracted text"),
    page_numbers: bool = typer.Option(True, "--page-numbers/--no-page-numbers", help="Include page numbers"),
):
    """Extract text from PDF in token-aware chunks."""
    
    async def run_extract():
        with console.status("[green]Extracting text...") as status:
            result = await extract_text_from_pdf(
                pdf_path=pdf_path,
                max_tokens_per_chunk=max_tokens,
                include_page_numbers=page_numbers,
                clean_text=clean
            )
        
        if result["status"] == "error":
            console.print(f"[red]Error:[/red] {result['error']}")
            return
        
        # Summary
        panel = Panel(
            f"[green]✓[/green] Text extracted successfully\n\n"
            f"[cyan]Source:[/cyan] {result['source_pdf']}\n"
            f"[cyan]Pages:[/cyan] {result['total_pages']}\n"
            f"[cyan]Chunks:[/cyan] {result['chunks_created']}\n"
            f"[cyan]Total Tokens:[/cyan] {result['total_tokens']:,}\n"
            f"[cyan]Avg Tokens/Chunk:[/cyan] {result['avg_tokens_per_chunk']:,}",
            title="Text Extraction Complete",
            border_style="green"
        )
        console.print(panel)
        
        # Show chunk summary
        if result.get("chunks"):
            table = Table(title="Text Chunks")
            table.add_column("Chunk", style="cyan")
            table.add_column("Pages", style="white")
            table.add_column("Tokens", style="yellow")
            table.add_column("Preview", style="dim")
            
            for chunk in result["chunks"][:5]:  # Show first 5
                preview = chunk["text"][:100] + "..." if len(chunk["text"]) > 100 else chunk["text"]
                table.add_row(
                    str(chunk["chunk_id"]),
                    chunk["page_range"],
                    f"{chunk['token_count']:,}",
                    preview.replace('\n', ' ')
                )
            
            if len(result["chunks"]) > 5:
                table.add_row("...", "...", "...", f"and {len(result['chunks']) - 5} more chunks")
            
            console.print(table)
        
        # Save to file if requested
        if output_file:
            output_path = Path(output_file)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            console.print(f"[green]Saved to:[/green] {output_path}")
    
    asyncio.run(run_extract())


@app.command()
def extract_range(
    pdf_path: str = typer.Argument(..., help="Path to PDF file"),
    start_page: int = typer.Argument(..., help="Start page (1-indexed)"),
    end_page: int = typer.Argument(..., help="End page (1-indexed)"),
    output_path: Optional[str] = typer.Option(None, "--output", "-o", help="Output PDF path"),
):
    """Extract specific page range as new PDF."""
    
    async def run_extract_range():
        with console.status(f"[green]Extracting pages {start_page}-{end_page}..."):
            result = await extract_pdf_range(
                pdf_path=pdf_path,
                start_page=start_page,
                end_page=end_page,
                output_path=output_path
            )
        
        if result["status"] == "error":
            console.print(f"[red]Error:[/red] {result['error']}")
            return
        
        panel = Panel(
            f"[green]✓[/green] Pages extracted successfully\n\n"
            f"[cyan]Source:[/cyan] {Path(result['source_pdf']).name}\n"
            f"[cyan]Pages:[/cyan] {result['extracted_pages']} ({result['page_count']} pages)\n"
            f"[cyan]Output:[/cyan] {result['output_file']}",
            title="Page Extraction Complete",
            border_style="green"
        )
        console.print(panel)
    
    asyncio.run(run_extract_range())


@app.command()
def demo(
    pdf_path: Optional[str] = typer.Argument(None, help="Path to PDF file (optional)"),
):
    """Run a quick demo of all tools."""
    
    if not pdf_path:
        # Look for a PDF in common locations
        common_paths = [
            "/Users/terry/Downloads/Trends_Artificial_Intelligence.pdf",
            "/Users/terry/ideaverse-zero-2/*.pdf",
        ]
        
        for pattern in common_paths:
            from glob import glob
            matches = glob(pattern)
            if matches:
                pdf_path = matches[0]
                break
        
        if not pdf_path:
            console.print("[red]No PDF found. Please specify a path.[/red]")
            console.print("Usage: python test_cli.py demo /path/to/file.pdf")
            return
    
    console.print(f"[cyan]Running demo with:[/cyan] {Path(pdf_path).name}")
    console.print()
    
    async def run_demo():
        # Run info command
        console.rule("PDF Information")
        info_result = await get_pdf_info(pdf_path)
        # Display basic info
        if info_result["status"] == "success":
            console.print(f"Pages: {info_result['pdf_info']['total_pages']}")
            console.print(f"Size: {info_result['pdf_info']['file_size_mb']} MB")
        
        console.print()
        
        # Run a small split test
        console.rule("Split Test (5 pages per chunk)")
        split_result = await split_pdf(pdf_path, pages_per_chunk=5)
        if split_result["status"] == "success":
            console.print(f"Created {split_result['chunks_created']} chunks")
        
        console.print()
        
        # Extract a small sample
        console.rule("Text Extraction Test")
        extract_result = await extract_text_from_pdf(pdf_path, max_tokens_per_chunk=2000)
        if extract_result["status"] == "success":
            console.print(f"Extracted {extract_result['total_tokens']:,} total tokens")
    
    asyncio.run(run_demo())


if __name__ == "__main__":
    app()