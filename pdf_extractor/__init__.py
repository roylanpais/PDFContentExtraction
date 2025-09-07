"""
PDF Visual Content Extractor - Main Module

A comprehensive pipeline for extracting visual content from PDF documents
using various methods including VLMs, Azure AI, and traditional CV approaches.
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
import logging
from enum import Enum
import json
from datetime import datetime

from .extractors import (
    VLMExtractor,
    AzureExtractor,
    TraditionalExtractor,
    HybridExtractor
)
from .models import ExtractionResult, ExtractionConfig
from .utils import setup_logging, validate_config

logger = logging.getLogger(__name__)


class ExtractionMethod(Enum):
    """Available extraction methods."""
    VLM = "vlm"
    AZURE = "azure"
    TRADITIONAL = "traditional"
    HYBRID = "hybrid"


class TargetType(Enum):
    """Types of content that can be extracted."""
    FIGURE = "figure"
    TABLE = "table"
    ALGORITHM = "algorithm"
    EQUATION = "equation"
    DIAGRAM = "diagram"
    CHART = "chart"
    CUSTOM = "custom"


@dataclass
class ExtractionConfig:
    """Configuration for extraction process."""
    target_type: TargetType
    target_identifier: Optional[str] = None
    extraction_method: ExtractionMethod = ExtractionMethod.HYBRID
    pages: Optional[List[int]] = None
    page_range: Optional[str] = None
    
    # VLM Configuration
    vlm_model: str = "gpt-4-vision"
    vlm_temperature: float = 0.1
    vlm_max_tokens: int = 1000
    
    # Output Configuration
    output_format: str = "png"
    output_dir: str = "./output"
    include_captions: bool = True
    include_metadata: bool = True
    save_intermediate: bool = False
    
    # Processing Configuration
    confidence_threshold: float = 0.7
    max_retries: int = 3
    parallel_processing: bool = False
    gpu_enabled: bool = True
    
    # Custom patterns for specific extraction needs
    custom_patterns: List[str] = field(default_factory=list)
    
    # Azure specific settings
    azure_model: str = "prebuilt-layout"
    azure_features: List[str] = field(default_factory=lambda: ["layout", "figures"])
    
    def __post_init__(self):
        """Validate and process configuration after initialization."""
        if isinstance(self.target_type, str):
            self.target_type = TargetType(self.target_type)
        if isinstance(self.extraction_method, str):
            self.extraction_method = ExtractionMethod(self.extraction_method)
        
        # Process page range if provided
        if self.page_range and not self.pages:
            self.pages = self._parse_page_range(self.page_range)
    
    def _parse_page_range(self, page_range: str) -> List[int]:
        """Parse page range string to list of page numbers."""
        pages = []
        for part in page_range.split(','):
            if '-' in part:
                start, end = map(int, part.split('-'))
                pages.extend(range(start, end + 1))
            else:
                pages.append(int(part))
        return sorted(list(set(pages)))


@dataclass
class ExtractionResult:
    """Result of an extraction operation."""
    element_id: str
    element_type: str
    page_number: int
    bounding_box: Optional[List[float]] = None
    image_path: Optional[str] = None
    caption: Optional[str] = None
    confidence: float = 0.0
    extraction_method: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def save(self, output_path: Union[str, Path]) -> bool:
        """Save extracted content to file."""
        try:
            if self.image_path and Path(self.image_path).exists():
                import shutil
                shutil.copy2(self.image_path, output_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to save result: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "element_id": self.element_id,
            "element_type": self.element_type,
            "page_number": self.page_number,
            "bounding_box": self.bounding_box,
            "image_path": self.image_path,
            "caption": self.caption,
            "confidence": self.confidence,
            "extraction_method": self.extraction_method,
            "metadata": self.metadata
        }


class PDFExtractor:
    """Main PDF visual content extractor."""
    
    def __init__(self, config: Optional[ExtractionConfig] = None):
        """Initialize the extractor with configuration."""
        self.config = config or ExtractionConfig()
        setup_logging()
        
        # Initialize extractors
        self.extractors = {
            ExtractionMethod.VLM: VLMExtractor(),
            ExtractionMethod.AZURE: AzureExtractor(),
            ExtractionMethod.TRADITIONAL: TraditionalExtractor(),
            ExtractionMethod.HYBRID: HybridExtractor()
        }
        
        logger.info("PDFExtractor initialized")
    
    def extract(self, 
                pdf_path: Union[str, Path], 
                config: Optional[ExtractionConfig] = None) -> List[ExtractionResult]:
        """
        Extract visual content from PDF.
        
        Args:
            pdf_path: Path to PDF file
            config: Extraction configuration (optional)
            
        Returns:
            List of extraction results
        """
        config = config or self.config
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Validate configuration
        validate_config(config)
        
        logger.info(f"Starting extraction from {pdf_path}")
        logger.info(f"Method: {config.extraction_method.value}")
        logger.info(f"Target: {config.target_type.value}")
        
        try:
            # Get appropriate extractor
            extractor = self.extractors[config.extraction_method]
            
            # Perform extraction
            results = extractor.extract(pdf_path, config)
            
            # Filter by confidence threshold
            filtered_results = [
                result for result in results 
                if result.confidence >= config.confidence_threshold
            ]
            
            logger.info(f"Extracted {len(filtered_results)} elements")
            
            # Save results if output directory specified
            if config.output_dir:
                self._save_results(filtered_results, config)
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            raise
    
    def extract_batch(self,
                     pdf_paths: List[Union[str, Path]],
                     config: Optional[ExtractionConfig] = None) -> Dict[str, List[ExtractionResult]]:
        """
        Extract content from multiple PDFs.
        
        Args:
            pdf_paths: List of PDF file paths
            config: Extraction configuration
            
        Returns:
            Dictionary mapping PDF paths to extraction results
        """
        config = config or self.config
        results = {}
        
        if config.parallel_processing:
            return self._extract_batch_parallel(pdf_paths, config)
        else:
            return self._extract_batch_sequential(pdf_paths, config)
    
    def _extract_batch_sequential(self, pdf_paths, config):
        """Sequential batch processing."""
        results = {}
        for pdf_path in pdf_paths:
            try:
                pdf_results = self.extract(pdf_path, config)
                results[str(pdf_path)] = pdf_results
            except Exception as e:
                logger.error(f"Failed to process {pdf_path}: {e}")
                results[str(pdf_path)] = []
        return results
    
    def _extract_batch_parallel(self, pdf_paths, config):
        """Parallel batch processing."""
        import concurrent.futures
        from multiprocessing import cpu_count
        
        results = {}
        max_workers = min(config.max_workers if hasattr(config, 'max_workers') else 4, 
                         cpu_count())
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(self.extract, pdf_path, config): pdf_path 
                for pdf_path in pdf_paths
            }
            
            for future in concurrent.futures.as_completed(future_to_path):
                pdf_path = future_to_path[future]
                try:
                    pdf_results = future.result()
                    results[str(pdf_path)] = pdf_results
                except Exception as e:
                    logger.error(f"Failed to process {pdf_path}: {e}")
                    results[str(pdf_path)] = []
        
        return results
    
    def _save_results(self, results: List[ExtractionResult], config: ExtractionConfig):
        """Save extraction results to files."""
        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save individual results
        for result in results:
            if result.image_path:
                output_filename = f"{result.element_id}.{config.output_format}"
                output_path = output_dir / output_filename
                result.save(output_path)
        
        # Save metadata if requested
        if config.include_metadata:
            metadata = {
                "extraction_timestamp": datetime.now().isoformat(),
                "config": self._config_to_dict(config),
                "results": [result.to_dict() for result in results]
            }
            
            metadata_path = output_dir / "extraction_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
    
    def _config_to_dict(self, config: ExtractionConfig) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "target_type": config.target_type.value,
            "target_identifier": config.target_identifier,
            "extraction_method": config.extraction_method.value,
            "vlm_model": config.vlm_model,
            "confidence_threshold": config.confidence_threshold,
            "output_format": config.output_format
        }
    
    def register_custom_extractor(self, method: str, extractor):
        """Register a custom extractor."""
        if hasattr(ExtractionMethod, method.upper()):
            custom_method = ExtractionMethod(method)
            self.extractors[custom_method] = extractor
            logger.info(f"Registered custom extractor: {method}")
        else:
            logger.warning(f"Invalid extraction method: {method}")


# Convenience functions for common use cases
def extract_figure(pdf_path: Union[str, Path], 
                  figure_id: str, 
                  method: str = "hybrid",
                  output_dir: str = "./output") -> List[ExtractionResult]:
    """
    Quick function to extract a specific figure.
    
    Args:
        pdf_path: Path to PDF file
        figure_id: Figure identifier (e.g., "Figure 1", "Fig. 2")
        method: Extraction method to use
        output_dir: Output directory for results
        
    Returns:
        List of extraction results
    """
    config = ExtractionConfig(
        target_type=TargetType.FIGURE,
        target_identifier=figure_id,
        extraction_method=ExtractionMethod(method),
        output_dir=output_dir
    )
    
    extractor = PDFExtractor(config)
    return extractor.extract(pdf_path)


def extract_algorithm(pdf_path: Union[str, Path],
                     pages: Optional[List[int]] = None,
                     method: str = "vlm",
                     output_dir: str = "./output") -> List[ExtractionResult]:
    """
    Quick function to extract algorithms from PDF.
    
    Args:
        pdf_path: Path to PDF file
        pages: Specific pages to search (optional)
        method: Extraction method to use
        output_dir: Output directory for results
        
    Returns:
        List of extraction results
    """
    config = ExtractionConfig(
        target_type=TargetType.ALGORITHM,
        extraction_method=ExtractionMethod(method),
        pages=pages,
        output_dir=output_dir
    )
    
    extractor = PDFExtractor(config)
    return extractor.extract(pdf_path)


def extract_all_figures(pdf_path: Union[str, Path],
                       method: str = "hybrid",
                       output_dir: str = "./output") -> List[ExtractionResult]:
    """
    Quick function to extract all figures from PDF.
    
    Args:
        pdf_path: Path to PDF file
        method: Extraction method to use
        output_dir: Output directory for results
        
    Returns:
        List of extraction results
    """
    config = ExtractionConfig(
        target_type=TargetType.FIGURE,
        extraction_method=ExtractionMethod(method),
        output_dir=output_dir
    )
    
    extractor = PDFExtractor(config)
    return extractor.extract(pdf_path)