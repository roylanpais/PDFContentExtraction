#!/usr/bin/env python3
"""
PDF Visual Content Extractor - Command Line Interface

Extract figures, tables, algorithms, and other visual content from PDF documents.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

import click
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from pdf_extractor import (
    PDFExtractor, 
    ExtractionConfig, 
    ExtractionMethod, 
    TargetType,
    extract_figure,
    extract_algorithm,
    extract_all_figures
)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--debug', is_flag=True, help='Enable debug logging')
def cli(verbose, debug):
    """PDF Visual Content Extractor - Extract figures, tables, and algorithms from PDFs."""
    level = logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING)
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True, path_type=Path))
@click.option('--target', '-t', required=True, 
              help='Target content to extract (figure, table, algorithm, etc.)')
@click.option('--identifier', '-i', 
              help='Specific identifier to extract (e.g., "Figure 1", "Algorithm 2")')
@click.option('--method', '-m', 
              type=click.Choice(['vlm', 'azure', 'traditional', 'hybrid']),
              default='hybrid',
              help='Extraction method to use')
@click.option('--model', 
              default='gpt-4-vision',
              help='VLM model to use (for VLM method)')
@click.option('--pages', '-p',
              help='Pages to process (e.g., "1,3,5" or "1-5")')
@click.option('--output-dir', '-o',
              type=click.Path(path_type=Path),
              default='./output',
              help='Output directory for extracted content')
@click.option('--output-format', '-f',
              type=click.Choice(['png', 'jpg', 'pdf']),
              default='png',
              help='Output image format')
@click.option('--confidence', '-c',
              type=float,
              default=0.7,
              help='Confidence threshold (0.0-1.0)')
@click.option('--include-captions/--no-captions',
              default=True,
              help='Include captions in extraction')
@click.option('--parallel/--sequential',
              default=False,
              help='Enable parallel processing')
@click.option('--custom-patterns',
              help='Custom regex patterns for extraction (comma-separated)')
def extract(pdf_path, target, identifier, method, model, pages, output_dir, 
           output_format, confidence, include_captions, parallel, custom_patterns):
    """Extract visual content from a PDF document."""
    
    try:
        # Parse pages
        page_list = None
        if pages:
            page_list = parse_page_range(pages)
        
        # Parse custom patterns
        patterns = []
        if custom_patterns:
            patterns = [p.strip() for p in custom_patterns.split(',')]
        
        # Create configuration
        config = ExtractionConfig(
            target_type=TargetType(target.lower()),
            target_identifier=identifier,
            extraction_method=ExtractionMethod(method),
            vlm_model=model,
            pages=page_list,
            output_dir=str(output_dir),
            output_format=output_format,
            confidence_threshold=confidence,
            include_captions=include_captions,
            parallel_processing=parallel,
            custom_patterns=patterns
        )
        
        # Create extractor and extract
        extractor = PDFExtractor(config)
        results = extractor.extract(pdf_path, config)
        
        # Print results summary
        click.echo(f"\nExtraction completed!")
        click.echo(f"Found {len(results)} elements:")
        
        for result in results:
            click.echo(f"  - {result.element_id} (page {result.page_number}, "
                      f"confidence: {result.confidence:.2f})")
            if result.caption:
                click.echo(f"    Caption: {result.caption[:100]}...")
        
        if results:
            click.echo(f"\nResults saved to: {output_dir}")
        else:
            click.echo("No matching content found. Try adjusting the confidence threshold or method.")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True, path_type=Path))
@click.argument('figure_id', type=str)
@click.option('--method', '-m',
              type=click.Choice(['vlm', 'azure', 'traditional', 'hybrid']),
              default='hybrid',
              help='Extraction method to use')
@click.option('--output-dir', '-o',
              type=click.Path(path_type=Path),
              default='./output',
              help='Output directory')
def figure(pdf_path, figure_id, method, output_dir):
    """Quick extraction of a specific figure."""
    
    try:
        results = extract_figure(pdf_path, figure_id, method, str(output_dir))
        
        if results:
            click.echo(f"Successfully extracted {figure_id}")
            for result in results:
                click.echo(f"  Saved: {result.image_path}")
        else:
            click.echo(f"Figure '{figure_id}' not found")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True, path_type=Path))
@click.option('--pages', '-p',
              help='Pages to search (e.g., "3-5")')
@click.option('--method', '-m',
              type=click.Choice(['vlm', 'azure', 'traditional', 'hybrid']),
              default='vlm',
              help='Extraction method to use')
@click.option('--output-dir', '-o',
              type=click.Path(path_type=Path),
              default='./output',
              help='Output directory')
def algorithm(pdf_path, pages, method, output_dir):
    """Extract algorithms from PDF."""
    
    try:
        page_list = None
        if pages:
            page_list = parse_page_range(pages)
        
        results = extract_algorithm(pdf_path, page_list, method, str(output_dir))
        
        if results:
            click.echo(f"Found {len(results)} algorithms:")
            for result in results:
                click.echo(f"  - {result.element_id} (page {result.page_number})")
        else:
            click.echo("No algorithms found")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True, path_type=Path))
@click.option('--method', '-m',
              type=click.Choice(['vlm', 'azure', 'traditional', 'hybrid']),
              default='hybrid',
              help='Extraction method to use')
@click.option('--output-dir', '-o',
              type=click.Path(path_type=Path),
              default='./output',
              help='Output directory')
def figures(pdf_path, method, output_dir):
    """Extract all figures from PDF."""
    
    try:
        results = extract_all_figures(pdf_path, method, str(output_dir))
        
        if results:
            click.echo(f"Extracted {len(results)} figures:")
            for result in results:
                click.echo(f"  - {result.element_id} (page {result.page_number})")
        else:
            click.echo("No figures found")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input_dir', type=click.Path(exists=True, path_type=Path))
@click.option('--target', '-t', required=True,
              help='Target content type to extract')
@click.option('--method', '-m',
              type=click.Choice(['vlm', 'azure', 'traditional', 'hybrid']),
              default='hybrid',
              help='Extraction method to use')
@click.option('--output-dir', '-o',
              type=click.Path(path_type=Path),
              default='./batch_output',
              help='Output directory for batch results')
@click.option('--parallel/--sequential',
              default=True,
              help='Enable parallel processing')
@click.option('--max-workers',
              type=int,
              default=4,
              help='Maximum number of parallel workers')
def batch(input_dir, target, method, output_dir, parallel, max_workers):
    """Process multiple PDF files in batch."""
    
    try:
        # Find all PDF files
        pdf_files = list(input_dir.glob("*.pdf"))
        
        if not pdf_files:
            click.echo(f"No PDF files found in {input_dir}")
            return
        
        click.echo(f"Found {len(pdf_files)} PDF files to process")
        
        # Create configuration
        config = ExtractionConfig(
            target_type=TargetType(target.lower()),
            extraction_method=ExtractionMethod(method),
            output_dir=str(output_dir),
            parallel_processing=parallel,
            max_workers=max_workers
        )
        
        # Process files
        extractor = PDFExtractor(config)
        batch_results = extractor.extract_batch(pdf_files, config)
        
        # Summary
        total_extracted = sum(len(results) for results in batch_results.values())
        successful_files = len([r for r in batch_results.values() if r])
        
        click.echo(f"\nBatch processing completed:")
        click.echo(f"  Processed: {len(pdf_files)} files")
        click.echo(f"  Successful: {successful_files} files")
        click.echo(f"  Total extracted elements: {total_extracted}")
        
        # Save batch summary
        summary_path = output_dir / "batch_summary.json"
        summary = {
            "total_files": len(pdf_files),
            "successful_files": successful_files,
            "total_extracted": total_extracted,
            "results": {str(k): [r.to_dict() for r in v] for k, v in batch_results.items()}
        }
        
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        click.echo(f"Summary saved to: {summary_path}")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--check-gpu', is_flag=True, help='Check GPU availability')
@click.option('--check-azure', is_flag=True, help='Check Azure credentials')
@click.option('--check-openai', is_flag=True, help='Check OpenAI credentials')
@click.option('--check-models', is_flag=True, help='Check model availability')
def setup(check_gpu, check_azure, check_openai, check_models):
    """Check system setup and dependencies."""
    
    click.echo("PDF Visual Content Extractor - System Check\n")
    
    # Check basic dependencies
    try:
        import torch
        click.echo(f"✓ PyTorch: {torch.__version__}")
        
        if check_gpu:
            if torch.cuda.is_available():
                click.echo(f"✓ CUDA: {torch.version.cuda}")
                click.echo(f"✓ GPU: {torch.cuda.get_device_name(0)}")
            else:
                click.echo("⚠ CUDA: Not available (CPU mode only)")
    except ImportError:
        click.echo("✗ PyTorch: Not installed")
    
    try:
        import cv2
        click.echo(f"✓ OpenCV: {cv2.__version__}")
    except ImportError:
        click.echo("✗ OpenCV: Not installed")
    
    try:
        from pdf2image import convert_from_path
        click.echo("✓ pdf2image: Available")
    except ImportError:
        click.echo("✗ pdf2image: Not installed")
    
    # Check Azure
    if check_azure:
        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            endpoint = os.getenv("AZURE_DOC_INTELLIGENCE_ENDPOINT")
            key = os.getenv("AZURE_DOC_INTELLIGENCE_KEY")
            
            if endpoint and key:
                click.echo("✓ Azure AI Document Intelligence: Configured")
            else:
                click.echo("⚠ Azure AI Document Intelligence: Not configured")
        except ImportError:
            click.echo("✗ Azure AI Document Intelligence: SDK not installed")
    
    # Check OpenAI
    if check_openai:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            click.echo("✓ OpenAI API: Configured")
        else:
            click.echo("⚠ OpenAI API: Not configured")
    
    # Check models
    if check_models:
        click.echo("\nAvailable extraction models:")
        click.echo("  VLM Models:")
        click.echo("    - gpt-4-vision (requires OpenAI API)")
        click.echo("    - claude-vision (requires Anthropic API)")
        click.echo("    - gemini-vision (requires Google API)")
        click.echo("    - llava (open-source, requires GPU)")
        click.echo("    - blip2 (open-source, requires GPU)")
        click.echo("  Azure Models:")
        click.echo("    - prebuilt-layout")
        click.echo("    - prebuilt-document")


def parse_page_range(page_range: str) -> List[int]:
    """Parse page range string to list of page numbers."""
    pages = []
    for part in page_range.split(','):
        if '-' in part:
            start, end = map(int, part.split('-'))
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part))
    return sorted(list(set(pages)))


if __name__ == '__main__':
    cli()