"""
Traditional computer vision and OCR-based extractor.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any
import cv2
import numpy as np
from PIL import Image

from ..base import BaseExtractor, LayoutAnalyzer, TextExtractor, CaptionMatcher
from ..models import ExtractionResult

logger = logging.getLogger(__name__)


class TraditionalExtractor(BaseExtractor):
    """Traditional CV + OCR based extractor."""
    
    def __init__(self):
        """Initialize traditional extractor."""
        super().__init__("Traditional")
        
        # Initialize components
        self.layout_analyzer = LayoutAnalyzer()
        self.text_extractor = TextExtractor("tesseract")
        self.caption_matcher = CaptionMatcher()
    
    def extract(self, pdf_path: Path, config) -> List[ExtractionResult]:
        """Extract content using traditional CV + OCR methods."""
        try:
            # Convert PDF to images
            images = self.preprocess_pdf(pdf_path, config)
            
            results = []
            
            for page_num, image in enumerate(images, 1):
                # Skip pages not in requested range
                if config.pages and page_num not in config.pages:
                    continue
                
                # Analyze page layout
                layout = self.layout_analyzer.analyze_page(image, page_num)
                
                # Extract text from all regions
                self._extract_text_from_layout(layout, image)
                
                # Get elements based on target type
                elements = self._filter_elements_by_type(layout, config)
                
                # Create results
                for element in elements:
                    result = self._create_result_from_element(
                        element, page_num, image, config
                    )
                    if result and result.confidence >= config.confidence_threshold:
                        results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Traditional extraction failed: {e}")
            raise
    
    def _extract_text_from_layout(self, layout, image):
        """Extract text from all layout elements."""
        for text_block in layout.text_blocks:
            if 'bbox' in text_block and 'text' not in text_block:
                text = self.text_extractor.extract_text_from_region(
                    image, text_block['bbox']
                )
                text_block['text'] = text
    
    def _filter_elements_by_type(self, layout, config) -> List[Dict[str, Any]]:
        """Filter elements based on target type and identifier."""
        target_type = config.target_type.value
        
        # Get elements of target type
        if target_type == "figure":
            elements = layout.figures
        elif target_type == "table":
            elements = layout.tables
        elif target_type == "equation":
            elements = layout.equations
        else:
            # For other types, search in text blocks
            elements = self._find_elements_in_text(layout.text_blocks, config)
        
        # Filter by identifier if specified
        if config.target_identifier:
            elements = [
                elem for elem in elements
                if self._matches_identifier(elem, config.target_identifier)
            ]
        
        return elements
    
    def _find_elements_in_text(self, text_blocks: List[Dict[str, Any]], config) -> List[Dict[str, Any]]:
        """Find elements of specific types in text blocks."""
        import re
        
        patterns = {
            "algorithm": [
                r"Algorithm\s+\d+",
                r"Procedure\s+\w+",
                r"Method\s+\d+"
            ],
            "custom": config.custom_patterns
        }
        
        target_patterns = patterns.get(config.target_type.value, [])
        found_elements = []
        
        for block in text_blocks:
            if 'text' in block:
                for pattern in target_patterns:
                    if re.search(pattern, block['text'], re.IGNORECASE):
                        found_elements.append(block)
                        break
        
        return found_elements
    
    def _matches_identifier(self, element: Dict[str, Any], identifier: str) -> bool:
        """Check if element matches specific identifier."""
        element_text = element.get('text', '')
        return identifier.lower() in element_text.lower()
    
    def _create_result_from_element(self, element: Dict[str, Any], 
                                   page_num: int, image: Image.Image, 
                                   config) -> ExtractionResult:
        """Create extraction result from element."""
        try:
            # Extract image region
            extracted_image_path = None
            if 'bbox' in element:
                cropped_image = self.extract_bounding_box(image, element['bbox'])
                
                # Save cropped image
                output_dir = Path(config.output_dir) / "extracted_images"
                output_dir.mkdir(parents=True, exist_ok=True)
                
                filename = f"{element['id']}_page_{page_num}.{config.output_format}"
                image_path = output_dir / filename
                
                if self.save_image(cropped_image, image_path, config.output_format):
                    extracted_image_path = str(image_path)
            
            # Get caption
            caption = element.get('text', '') or element.get('caption', '')
            
            return ExtractionResult(
                element_id=element['id'],
                element_type=config.target_type.value,
                page_number=page_num,
                bounding_box=element.get('bbox'),
                image_path=extracted_image_path,
                caption=caption,
                confidence=element.get('confidence', 0.8),
                extraction_method="traditional_cv_ocr",
                metadata={
                    'detection_method': 'computer_vision',
                    'ocr_engine': 'tesseract',
                    'area': element.get('area', 0)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create result from element: {e}")
            return None