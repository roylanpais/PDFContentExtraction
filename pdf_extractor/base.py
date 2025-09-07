"""
Base classes and interfaces for PDF content extractors.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
import logging
from dataclasses import dataclass
import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Base class for all extraction methods."""
    
    def __init__(self, name: str = "base"):
        """Initialize base extractor."""
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def extract(self, pdf_path: Path, config) -> List['ExtractionResult']:
        """
        Extract content from PDF.
        
        Args:
            pdf_path: Path to PDF file
            config: Extraction configuration
            
        Returns:
            List of extraction results
        """
        pass
    
    def preprocess_pdf(self, pdf_path: Path, config) -> List[Image.Image]:
        """
        Convert PDF to images for processing.
        
        Args:
            pdf_path: Path to PDF file
            config: Extraction configuration
            
        Returns:
            List of PIL Images
        """
        try:
            from pdf2image import convert_from_path
            
            # Convert specific pages or all pages
            if config.pages:
                images = convert_from_path(
                    pdf_path,
                    first_page=min(config.pages),
                    last_page=max(config.pages),
                    dpi=300,
                    thread_count=4
                )
                # Filter to only requested pages
                requested_indices = [p - min(config.pages) for p in config.pages]
                images = [images[i] for i in requested_indices if i < len(images)]
            else:
                images = convert_from_path(pdf_path, dpi=300, thread_count=4)
            
            self.logger.info(f"Converted {len(images)} pages to images")
            return images
            
        except Exception as e:
            self.logger.error(f"Failed to convert PDF to images: {e}")
            raise
    
    def extract_bounding_box(self, image: Image.Image, bbox: List[float]) -> Image.Image:
        """
        Extract region from image using bounding box.
        
        Args:
            image: Source image
            bbox: Bounding box coordinates [x1, y1, x2, y2]
            
        Returns:
            Cropped image
        """
        try:
            x1, y1, x2, y2 = bbox
            cropped = image.crop((x1, y1, x2, y2))
            return cropped
        except Exception as e:
            self.logger.error(f"Failed to extract bounding box: {e}")
            raise
    
    def save_image(self, image: Image.Image, output_path: Path, format: str = "png") -> bool:
        """
        Save image to file.
        
        Args:
            image: Image to save
            output_path: Output file path
            format: Image format
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(output_path, format=format.upper())
            return True
        except Exception as e:
            self.logger.error(f"Failed to save image: {e}")
            return False


@dataclass
class DocumentLayout:
    """Represents the layout structure of a document page."""
    page_number: int
    figures: List[Dict[str, Any]]
    tables: List[Dict[str, Any]]
    text_blocks: List[Dict[str, Any]]
    equations: List[Dict[str, Any]]
    page_width: int
    page_height: int
    
    def get_elements_by_type(self, element_type: str) -> List[Dict[str, Any]]:
        """Get all elements of a specific type."""
        type_map = {
            'figure': self.figures,
            'table': self.tables,
            'text': self.text_blocks,
            'equation': self.equations
        }
        return type_map.get(element_type, [])
    
    def find_element_by_text(self, text_pattern: str, element_type: str = None) -> List[Dict[str, Any]]:
        """Find elements containing specific text pattern."""
        import re
        
        found_elements = []
        search_lists = []
        
        if element_type:
            search_lists = [self.get_elements_by_type(element_type)]
        else:
            search_lists = [self.figures, self.tables, self.text_blocks, self.equations]
        
        for element_list in search_lists:
            for element in element_list:
                if 'text' in element and re.search(text_pattern, element['text'], re.IGNORECASE):
                    found_elements.append(element)
        
        return found_elements


class LayoutAnalyzer:
    """Analyzes document layout to identify different content types."""
    
    def __init__(self):
        """Initialize layout analyzer."""
        self.logger = logging.getLogger(f"{__name__}.LayoutAnalyzer")
    
    def analyze_page(self, image: Image.Image, page_number: int) -> DocumentLayout:
        """
        Analyze page layout and identify content regions.
        
        Args:
            image: Page image
            page_number: Page number
            
        Returns:
            Document layout analysis
        """
        try:
            # Convert PIL to OpenCV format
            opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Analyze layout using multiple methods
            figures = self._detect_figures(opencv_image)
            tables = self._detect_tables(opencv_image)
            text_blocks = self._detect_text_blocks(opencv_image)
            equations = self._detect_equations(opencv_image)
            
            layout = DocumentLayout(
                page_number=page_number,
                figures=figures,
                tables=tables,
                text_blocks=text_blocks,
                equations=equations,
                page_width=image.width,
                page_height=image.height
            )
            
            self.logger.debug(f"Page {page_number}: {len(figures)} figures, {len(tables)} tables, "
                            f"{len(text_blocks)} text blocks, {len(equations)} equations")
            
            return layout
            
        except Exception as e:
            self.logger.error(f"Layout analysis failed: {e}")
            raise
    
    def _detect_figures(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Detect figure regions in the image."""
        figures = []
        
        try:
            # Convert to grayscale for processing
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Use contour detection to find potential figure regions
            _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                # Filter by area (figures are typically larger)
                if area > 10000:  # Minimum area threshold
                    x, y, w, h = cv2.boundingRect(contour)
                    # Additional filters for aspect ratio, etc.
                    if w > 100 and h > 100:  # Minimum size
                        figures.append({
                            'id': f'figure_{i}',
                            'bbox': [x, y, x+w, y+h],
                            'area': area,
                            'type': 'figure',
                            'confidence': 0.8  # Base confidence
                        })
        
        except Exception as e:
            self.logger.error(f"Figure detection failed: {e}")
        
        return figures
    
    def _detect_tables(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Detect table regions in the image."""
        tables = []
        
        try:
            # Use line detection for table identification
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect horizontal lines
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
            horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
            
            # Detect vertical lines
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
            vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel)
            
            # Combine lines to identify table structures
            table_structure = cv2.addWeighted(horizontal_lines, 0.5, vertical_lines, 0.5, 0.0)
            
            # Find contours in the combined structure
            contours, _ = cv2.findContours(table_structure, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if area > 5000:  # Minimum area for tables
                    x, y, w, h = cv2.boundingRect(contour)
                    tables.append({
                        'id': f'table_{i}',
                        'bbox': [x, y, x+w, y+h],
                        'area': area,
                        'type': 'table',
                        'confidence': 0.7
                    })
        
        except Exception as e:
            self.logger.error(f"Table detection failed: {e}")
        
        return tables
    
    def _detect_text_blocks(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Detect text block regions."""
        text_blocks = []
        
        try:
            # Use MSER (Maximally Stable Extremal Regions) for text detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            mser = cv2.MSER_create()
            regions, _ = mser.detectRegions(gray)
            
            # Group nearby regions into text blocks
            for i, region in enumerate(regions):
                if len(region) > 50:  # Minimum number of pixels
                    x, y, w, h = cv2.boundingRect(region)
                    # Filter by aspect ratio and size
                    if w > 50 and h > 20 and w/h > 2:  # Typical text block ratios
                        text_blocks.append({
                            'id': f'text_{i}',
                            'bbox': [x, y, x+w, y+h],
                            'type': 'text',
                            'confidence': 0.6
                        })
        
        except Exception as e:
            self.logger.error(f"Text block detection failed: {e}")
        
        return text_blocks
    
    def _detect_equations(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Detect mathematical equation regions."""
        equations = []
        
        try:
            # Equations often have specific characteristics:
            # - Mathematical symbols
            # - Specific formatting patterns
            # - Different text density
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if 1000 < area < 5000:  # Equations are typically medium-sized
                    x, y, w, h = cv2.boundingRect(contour)
                    # Check aspect ratio typical of equations
                    if 0.2 < h/w < 2:
                        equations.append({
                            'id': f'equation_{i}',
                            'bbox': [x, y, x+w, y+h],
                            'type': 'equation',
                            'confidence': 0.5
                        })
        
        except Exception as e:
            self.logger.error(f"Equation detection failed: {e}")
        
        return equations


class TextExtractor:
    """Extracts text content using OCR and other methods."""
    
    def __init__(self, ocr_engine: str = "tesseract"):
        """Initialize text extractor."""
        self.ocr_engine = ocr_engine
        self.logger = logging.getLogger(f"{__name__}.TextExtractor")
        
        # Initialize OCR engine
        if ocr_engine == "tesseract":
            import pytesseract
            self.ocr = pytesseract
        elif ocr_engine == "easyocr":
            import easyocr
            self.ocr_reader = easyocr.Reader(['en'])
    
    def extract_text_from_region(self, image: Image.Image, bbox: List[float]) -> str:
        """
        Extract text from a specific region of the image.
        
        Args:
            image: Source image
            bbox: Bounding box coordinates
            
        Returns:
            Extracted text
        """
        try:
            # Crop image to region
            cropped = self.extract_bounding_box(image, bbox)
            
            # Extract text using selected OCR engine
            if self.ocr_engine == "tesseract":
                text = self.ocr.image_to_string(cropped)
            elif self.ocr_engine == "easyocr":
                results = self.ocr_reader.readtext(np.array(cropped))
                text = ' '.join([result[1] for result in results])
            else:
                raise ValueError(f"Unsupported OCR engine: {self.ocr_engine}")
            
            return text.strip()
            
        except Exception as e:
            self.logger.error(f"Text extraction failed: {e}")
            return ""
    
    def extract_bounding_box(self, image: Image.Image, bbox: List[float]) -> Image.Image:
        """Extract region from image using bounding box."""
        x1, y1, x2, y2 = bbox
        return image.crop((x1, y1, x2, y2))


class CaptionMatcher:
    """Matches captions with visual elements."""
    
    def __init__(self):
        """Initialize caption matcher."""
        self.logger = logging.getLogger(f"{__name__}.CaptionMatcher")
    
    def find_captions(self, layout: DocumentLayout, element_type: str) -> Dict[str, str]:
        """
        Find captions for elements of a specific type.
        
        Args:
            layout: Document layout analysis
            element_type: Type of element to find captions for
            
        Returns:
            Dictionary mapping element IDs to their captions
        """
        captions = {}
        
        try:
            elements = layout.get_elements_by_type(element_type)
            
            # Look for text blocks that contain caption patterns
            caption_patterns = {
                'figure': [r'Figure\s+\d+', r'Fig\.\s*\d+', r'Fig\s+\d+'],
                'table': [r'Table\s+\d+', r'Tab\.\s*\d+'],
                'equation': [r'Equation\s+\d+', r'Eq\.\s*\d+', r'\(\d+\)']
            }
            
            patterns = caption_patterns.get(element_type, [])
            
            for element in elements:
                caption = self._find_nearest_caption(element, layout.text_blocks, patterns)
                if caption:
                    captions[element['id']] = caption
        
        except Exception as e:
            self.logger.error(f"Caption matching failed: {e}")
        
        return captions
    
    def _find_nearest_caption(self, element: Dict[str, Any], 
                             text_blocks: List[Dict[str, Any]], 
                             patterns: List[str]) -> str:
        """Find the nearest caption text for an element."""
        import re
        
        element_bbox = element['bbox']
        element_center = ((element_bbox[0] + element_bbox[2]) / 2, 
                         (element_bbox[1] + element_bbox[3]) / 2)
        
        best_caption = ""
        min_distance = float('inf')
        
        for text_block in text_blocks:
            if 'text' not in text_block:
                continue
                
            text = text_block.get('text', '')
            
            # Check if text matches caption patterns
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    # Calculate distance from element
                    text_bbox = text_block['bbox']
                    text_center = ((text_bbox[0] + text_bbox[2]) / 2,
                                 (text_bbox[1] + text_bbox[3]) / 2)
                    
                    distance = ((element_center[0] - text_center[0])**2 + 
                              (element_center[1] - text_center[1])**2)**0.5
                    
                    if distance < min_distance:
                        min_distance = distance
                        best_caption = text
        
        return best_caption