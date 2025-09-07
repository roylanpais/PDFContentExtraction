"""
Azure AI Document Intelligence extractor implementation.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image

from ..base import BaseExtractor
from ..models import ExtractionResult

logger = logging.getLogger(__name__)


class AzureExtractor(BaseExtractor):
    """Extractor using Azure AI Document Intelligence."""
    
    def __init__(self):
        """Initialize Azure extractor."""
        super().__init__("Azure")
        
        # Initialize Azure client
        self.endpoint = os.getenv("AZURE_DOC_INTELLIGENCE_ENDPOINT")
        self.key = os.getenv("AZURE_DOC_INTELLIGENCE_KEY")
        
        if not self.endpoint or not self.key:
            raise ValueError("Azure credentials not found in environment variables")
        
        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
            
            self.client = DocumentIntelligenceClient(
                endpoint=self.endpoint, 
                credential=AzureKeyCredential(self.key)
            )
            
        except ImportError:
            raise ImportError("Azure AI Document Intelligence SDK not installed. "
                            "Install with: pip install azure-ai-documentintelligence")
    
    def extract(self, pdf_path: Path, config) -> List[ExtractionResult]:
        """Extract content using Azure Document Intelligence."""
        try:
            # Analyze document
            analysis_result = self._analyze_document(pdf_path, config)
            
            # Parse results based on target type
            results = self._parse_azure_results(analysis_result, config)
            
            # Extract images if needed
            if config.output_dir:
                results = self._extract_images(pdf_path, results, config)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Azure extraction failed: {e}")
            raise
    
    def _analyze_document(self, pdf_path: Path, config) -> Any:
        """Analyze document using Azure AI."""
        try:
            from azure.ai.documentintelligence import AnalyzeDocumentRequest
            from azure.ai.documentintelligence.models import DocumentAnalysisFeature
            
            # Prepare request
            with open(pdf_path, "rb") as file:
                document_content = file.read()
            
            # Configure analysis features
            features = []
            if "layout" in config.azure_features:
                features.append(DocumentAnalysisFeature.OCR_HIGH_RESOLUTION)
            if "figures" in config.azure_features:
                features.append(DocumentAnalysisFeature.QUERY_FIELDS)
            
            # Set up query fields for specific content types
            query_fields = self._get_query_fields(config)
            
            # Analyze document
            request = AnalyzeDocumentRequest(bytes_source=document_content)
            
            poller = self.client.begin_analyze_document(
                model_id=config.azure_model,
                analyze_request=request,
                features=features if features else None,
                query_fields=query_fields if query_fields else None
            )
            
            result = poller.result()
            return result
            
        except Exception as e:
            self.logger.error(f"Azure document analysis failed: {e}")
            raise
    
    def _get_query_fields(self, config) -> Optional[List[str]]:
        """Get query fields based on target type."""
        query_fields_map = {
            "figure": ["Figure", "Fig", "Image", "Diagram"],
            "table": ["Table", "Tab"],
            "algorithm": ["Algorithm", "Procedure", "Method"],
            "equation": ["Equation", "Formula"]
        }
        
        if config.target_identifier:
            return [config.target_identifier]
        
        return query_fields_map.get(config.target_type.value, [])
    
    def _parse_azure_results(self, analysis_result, config) -> List[ExtractionResult]:
        """Parse Azure analysis results into extraction results."""
        results = []
        
        try:
            # Parse different types of content
            if hasattr(analysis_result, 'pages'):
                for page_num, page in enumerate(analysis_result.pages, 1):
                    # Skip pages not in requested range
                    if config.pages and page_num not in config.pages:
                        continue
                    
                    page_results = self._parse_page_content(page, page_num, config)
                    results.extend(page_results)
            
            # Parse figures from layout analysis
            if hasattr(analysis_result, 'figures'):
                for figure in analysis_result.figures:
                    result = self._create_figure_result(figure, config)
                    if result:
                        results.append(result)
            
            # Parse tables
            if hasattr(analysis_result, 'tables'):
                for table in analysis_result.tables:
                    result = self._create_table_result(table, config)
                    if result:
                        results.append(result)
            
            # Parse query field results
            if hasattr(analysis_result, 'documents') and analysis_result.documents:
                for doc in analysis_result.documents:
                    if hasattr(doc, 'fields') and doc.fields:
                        doc_results = self._parse_query_fields(doc.fields, config)
                        results.extend(doc_results)
        
        except Exception as e:
            self.logger.error(f"Failed to parse Azure results: {e}")
        
        return results
    
    def _parse_page_content(self, page, page_num: int, config) -> List[ExtractionResult]:
        """Parse content from a single page."""
        results = []
        
        try:
            # Look for text patterns that match target type
            if hasattr(page, 'lines'):
                text_blocks = self._group_lines_into_blocks(page.lines)
                
                for block in text_blocks:
                    if self._matches_target_pattern(block['text'], config):
                        result = ExtractionResult(
                            element_id=f"{config.target_type.value}_{page_num}_{len(results)}",
                            element_type=config.target_type.value,
                            page_number=page_num,
                            bounding_box=block['bbox'],
                            caption=block['text'],
                            confidence=block.get('confidence', 0.8),
                            extraction_method="azure_layout",
                            metadata={
                                'azure_model': config.azure_model,
                                'detection_method': 'text_pattern'
                            }
                        )
                        results.append(result)
        
        except Exception as e:
            self.logger.error(f"Page parsing failed: {e}")
        
        return results
    
    def _group_lines_into_blocks(self, lines) -> List[Dict[str, Any]]:
        """Group text lines into coherent blocks."""
        blocks = []
        
        try:
            current_block = {
                'text': '',
                'bbox': None,
                'confidence': 0.0,
                'line_count': 0
            }
            
            for line in lines:
                if hasattr(line, 'content') and hasattr(line, 'polygon'):
                    # Simple grouping - in practice, you'd use more sophisticated algorithms
                    if current_block['text']:
                        current_block['text'] += ' ' + line.content
                    else:
                        current_block['text'] = line.content
                    
                    # Update bounding box
                    line_bbox = self._polygon_to_bbox(line.polygon)
                    if current_block['bbox']:
                        current_block['bbox'] = self._merge_bboxes(
                            current_block['bbox'], line_bbox
                        )
                    else:
                        current_block['bbox'] = line_bbox
                    
                    current_block['line_count'] += 1
                    
                    # Start new block if line break detected
                    if line.content.strip().endswith('.') or line.content.strip().endswith(':'):
                        if current_block['text'].strip():
                            blocks.append(current_block.copy())
                        current_block = {
                            'text': '', 'bbox': None, 'confidence': 0.0, 'line_count': 0
                        }
            
            # Add final block
            if current_block['text'].strip():
                blocks.append(current_block)
        
        except Exception as e:
            self.logger.error(f"Line grouping failed: {e}")
        
        return blocks
    
    def _polygon_to_bbox(self, polygon) -> List[float]:
        """Convert polygon coordinates to bounding box."""
        try:
            x_coords = [point.x for point in polygon]
            y_coords = [point.y for point in polygon]
            
            return [
                min(x_coords),  # x1
                min(y_coords),  # y1
                max(x_coords),  # x2
                max(y_coords)   # y2
            ]
        except:
            return [0, 0, 0, 0]
    
    def _merge_bboxes(self, bbox1: List[float], bbox2: List[float]) -> List[float]:
        """Merge two bounding boxes."""
        return [
            min(bbox1[0], bbox2[0]),  # x1
            min(bbox1[1], bbox2[1]),  # y1
            max(bbox1[2], bbox2[2]),  # x2
            max(bbox1[3], bbox2[3])   # y2
        ]
    
    def _matches_target_pattern(self, text: str, config) -> bool:
        """Check if text matches target extraction pattern."""
        import re
        
        # Specific identifier match
        if config.target_identifier:
            return config.target_identifier.lower() in text.lower()
        
        # Pattern matching by type
        patterns = {
            "figure": [r'figure\s+\d+', r'fig\.?\s*\d+', r'image\s+\d+'],
            "table": [r'table\s+\d+', r'tab\.?\s*\d+'],
            "algorithm": [r'algorithm\s+\d+', r'procedure\s+\w+', r'method\s+\d+'],
            "equation": [r'equation\s+\d+', r'formula\s+\d+', r'\(\d+\)']
        }
        
        target_patterns = patterns.get(config.target_type.value, [])
        
        for pattern in target_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Custom patterns
        for pattern in config.custom_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _create_figure_result(self, figure, config) -> Optional[ExtractionResult]:
        """Create extraction result from Azure figure detection."""
        try:
            # Extract figure information
            figure_id = getattr(figure, 'id', f"figure_{id(figure)}")
            
            # Get bounding box
            bbox = None
            if hasattr(figure, 'bounding_regions') and figure.bounding_regions:
                region = figure.bounding_regions[0]
                bbox = self._polygon_to_bbox(region.polygon)
                page_num = region.page_number
            else:
                page_num = 1
            
            # Get caption
            caption = getattr(figure, 'caption', {}).get('content', '') if hasattr(figure, 'caption') else ''
            
            return ExtractionResult(
                element_id=figure_id,
                element_type="figure",
                page_number=page_num,
                bounding_box=bbox,
                caption=caption,
                confidence=0.9,  # Azure figures have high confidence
                extraction_method="azure_figure_detection",
                metadata={
                    'azure_model': config.azure_model,
                    'detection_method': 'figure_analysis'
                }
            )
            
        except Exception as e:
            self.logger.error(f"Figure result creation failed: {e}")
            return None
    
    def _create_table_result(self, table, config) -> Optional[ExtractionResult]:
        """Create extraction result from Azure table detection."""
        try:
            table_id = f"table_{table.row_count}x{table.column_count}"
            
            # Get bounding box
            bbox = None
            page_num = 1
            if hasattr(table, 'bounding_regions') and table.bounding_regions:
                region = table.bounding_regions[0]
                bbox = self._polygon_to_bbox(region.polygon)
                page_num = region.page_number
            
            # Extract table caption (look for nearby text)
            caption = f"Table with {table.row_count} rows and {table.column_count} columns"
            
            return ExtractionResult(
                element_id=table_id,
                element_type="table",
                page_number=page_num,
                bounding_box=bbox,
                caption=caption,
                confidence=0.85,
                extraction_method="azure_table_detection",
                metadata={
                    'azure_model': config.azure_model,
                    'row_count': table.row_count,
                    'column_count': table.column_count,
                    'detection_method': 'table_analysis'
                }
            )
            
        except Exception as e:
            self.logger.error(f"Table result creation failed: {e}")
            return None
    
    def _parse_query_fields(self, fields: Dict[str, Any], config) -> List[ExtractionResult]:
        """Parse results from query field analysis."""
        results = []
        
        try:
            for field_name, field_value in fields.items():
                if hasattr(field_value, 'content') and field_value.content:
                    # Check if this field matches our target
                    if self._matches_target_pattern(field_value.content, config):
                        # Get bounding box
                        bbox = None
                        page_num = 1
                        if hasattr(field_value, 'bounding_regions') and field_value.bounding_regions:
                            region = field_value.bounding_regions[0]
                            bbox = self._polygon_to_bbox(region.polygon)
                            page_num = region.page_number
                        
                        result = ExtractionResult(
                            element_id=f"query_{field_name}_{len(results)}",
                            element_type=config.target_type.value,
                            page_number=page_num,
                            bounding_box=bbox,
                            caption=field_value.content,
                            confidence=getattr(field_value, 'confidence', 0.8),
                            extraction_method="azure_query_fields",
                            metadata={
                                'azure_model': config.azure_model,
                                'field_name': field_name,
                                'detection_method': 'query_field'
                            }
                        )
                        results.append(result)
        
        except Exception as e:
            self.logger.error(f"Query fields parsing failed: {e}")
        
        return results
    
    def _extract_images(self, pdf_path: Path, results: List[ExtractionResult], 
                       config) -> List[ExtractionResult]:
        """Extract image regions from PDF for results with bounding boxes."""
        try:
            # Convert PDF to images for extraction
            images = self.preprocess_pdf(pdf_path, config)
            
            output_dir = Path(config.output_dir) / "extracted_images"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            for result in results:
                if result.bounding_box and result.page_number <= len(images):
                    page_image = images[result.page_number - 1]
                    
                    # Extract region
                    cropped_image = self.extract_bounding_box(page_image, result.bounding_box)
                    
                    # Save image
                    filename = f"{result.element_id}.{config.output_format}"
                    image_path = output_dir / filename
                    
                    if self.save_image(cropped_image, image_path, config.output_format):
                        result.image_path = str(image_path)
        
        except Exception as e:
            self.logger.error(f"Image extraction failed: {e}")
        
        return results