"""
Hybrid extractor that combines multiple methods for best results.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import statistics

from .vlm_extractor import VLMExtractor
from .azure_extractor import AzureExtractor
from .traditional_extractor import TraditionalExtractor
from ..base import BaseExtractor
from ..models import ExtractionResult

logger = logging.getLogger(__name__)


class HybridExtractor(BaseExtractor):
    """Hybrid extractor combining multiple extraction methods."""
    
    def __init__(self):
        """Initialize hybrid extractor."""
        super().__init__("Hybrid")
        
        # Initialize all extraction methods
        self.extractors = {}
        
        try:
            self.extractors['vlm'] = VLMExtractor()
        except Exception as e:
            self.logger.warning(f"VLM extractor initialization failed: {e}")
        
        try:
            self.extractors['azure'] = AzureExtractor()
        except Exception as e:
            self.logger.warning(f"Azure extractor initialization failed: {e}")
        
        try:
            self.extractors['traditional'] = TraditionalExtractor()
        except Exception as e:
            self.logger.warning(f"Traditional extractor initialization failed: {e}")
        
        if not self.extractors:
            raise RuntimeError("No extraction methods available")
    
    def extract(self, pdf_path: Path, config) -> List[ExtractionResult]:
        """Extract content using hybrid approach."""
        try:
            # Determine which methods to use based on target type and configuration
            selected_methods = self._select_methods(config)
            
            # Run extractions with selected methods
            all_results = {}
            for method_name in selected_methods:
                if method_name in self.extractors:
                    try:
                        self.logger.info(f"Running {method_name} extraction...")
                        results = self.extractors[method_name].extract(pdf_path, config)
                        all_results[method_name] = results
                        self.logger.info(f"{method_name}: Found {len(results)} elements")
                    except Exception as e:
                        self.logger.error(f"{method_name} extraction failed: {e}")
                        all_results[method_name] = []
            
            # Combine and deduplicate results
            combined_results = self._combine_results(all_results, config)
            
            return combined_results
            
        except Exception as e:
            self.logger.error(f"Hybrid extraction failed: {e}")
            raise
    
    def _select_methods(self, config) -> List[str]:
        """Select extraction methods based on target type and available extractors."""
        target_type = config.target_type.value
        
        # Method selection strategy based on content type
        method_preferences = {
            "figure": ["vlm", "azure", "traditional"],
            "table": ["azure", "traditional", "vlm"],
            "algorithm": ["vlm", "traditional", "azure"],
            "equation": ["vlm", "traditional"],
            "diagram": ["vlm", "traditional"],
            "chart": ["vlm", "azure", "traditional"],
            "custom": ["vlm", "traditional"]
        }
        
        # Get preferred methods for target type
        preferred = method_preferences.get(target_type, ["vlm", "azure", "traditional"])
        
        # Filter by available extractors
        selected = [method for method in preferred if method in self.extractors]
        
        # Ensure at least one method is selected
        if not selected:
            selected = list(self.extractors.keys())[:1]
        
        # Limit methods based on performance requirements
        if config.confidence_threshold > 0.8:
            # High confidence required - use best methods
            selected = selected[:2]
        elif hasattr(config, 'fast_mode') and config.fast_mode:
            # Fast mode - use single best method
            selected = selected[:1]
        
        self.logger.info(f"Selected methods: {selected}")
        return selected
    
    def _combine_results(self, all_results: Dict[str, List[ExtractionResult]], 
                        config) -> List[ExtractionResult]:
        """Combine results from different methods, handling duplicates."""
        
        if not all_results:
            return []
        
        # If only one method was used, return its results
        if len(all_results) == 1:
            return list(all_results.values())[0]
        
        # Group results by similarity (same page + similar bounding box)
        grouped_results = self._group_similar_results(all_results)
        
        # For each group, select best result or create consensus
        final_results = []
        for group in grouped_results:
            best_result = self._select_best_from_group(group, config)
            if best_result:
                final_results.append(best_result)
        
        # Sort by page number and confidence
        final_results.sort(key=lambda x: (x.page_number, -x.confidence))
        
        self.logger.info(f"Combined results: {len(final_results)} final elements")
        return final_results
    
    def _group_similar_results(self, all_results: Dict[str, List[ExtractionResult]]) -> List[List[ExtractionResult]]:
        """Group similar results from different methods."""
        
        all_flat_results = []
        for method, results in all_results.items():
            for result in results:
                result.metadata['source_method'] = method
                all_flat_results.append(result)
        
        # Group by page number first
        page_groups = {}
        for result in all_flat_results:
            page_num = result.page_number
            if page_num not in page_groups:
                page_groups[page_num] = []
            page_groups[page_num].append(result)
        
        # Within each page, group by spatial similarity
        similar_groups = []
        
        for page_num, page_results in page_groups.items():
            remaining_results = page_results[:]
            
            while remaining_results:
                current_result = remaining_results.pop(0)
                current_group = [current_result]
                
                # Find similar results
                to_remove = []
                for other_result in remaining_results:
                    if self._are_results_similar(current_result, other_result):
                        current_group.append(other_result)
                        to_remove.append(other_result)
                
                # Remove similar results from remaining
                for result in to_remove:
                    remaining_results.remove(result)
                
                similar_groups.append(current_group)
        
        return similar_groups
    
    def _are_results_similar(self, result1: ExtractionResult, result2: ExtractionResult) -> bool:
        """Check if two results are similar (likely same element)."""
        
        # Same page
        if result1.page_number != result2.page_number:
            return False
        
        # Similar element type or identifier
        if result1.element_type != result2.element_type:
            return False
        
        # Check bounding box overlap if available
        if result1.bounding_box and result2.bounding_box:
            overlap = self._calculate_bbox_overlap(result1.bounding_box, result2.bounding_box)
            if overlap > 0.5:  # 50% overlap threshold
                return True
        
        # Check caption similarity
        if result1.caption and result2.caption:
            similarity = self._calculate_text_similarity(result1.caption, result2.caption)
            if similarity > 0.7:  # 70% text similarity
                return True
        
        return False
    
    def _calculate_bbox_overlap(self, bbox1: List[float], bbox2: List[float]) -> float:
        """Calculate overlap ratio between two bounding boxes."""
        try:
            x1, y1, x2, y2 = bbox1
            x3, y3, x4, y4 = bbox2
            
            # Calculate intersection
            ix1 = max(x1, x3)
            iy1 = max(y1, y3)
            ix2 = min(x2, x4)
            iy2 = min(y2, y4)
            
            if ix2 <= ix1 or iy2 <= iy1:
                return 0.0
            
            intersection_area = (ix2 - ix1) * (iy2 - iy1)
            
            # Calculate union
            area1 = (x2 - x1) * (y2 - y1)
            area2 = (x4 - x3) * (y4 - y3)
            union_area = area1 + area2 - intersection_area
            
            return intersection_area / union_area if union_area > 0 else 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        try:
            from difflib import SequenceMatcher
            return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        except Exception:
            return 0.0
    
    def _select_best_from_group(self, group: List[ExtractionResult], config) -> Optional[ExtractionResult]:
        """Select the best result from a group of similar results."""
        
        if not group:
            return None
        
        if len(group) == 1:
            return group[0]
        
        # Method priority scores
        method_scores = {
            'vlm': 3.0,
            'azure': 2.0,
            'traditional': 1.0
        }
        
        # Calculate composite scores
        best_result = None
        best_score = -1
        
        for result in group:
            # Base score from confidence
            score = result.confidence
            
            # Method bonus
            source_method = result.metadata.get('source_method', 'unknown')
            method_bonus = method_scores.get(source_method, 0)
            score += method_bonus * 0.1  # Small method bonus
            
            # Caption bonus (having caption is good)
            if result.caption:
                score += 0.05
            
            # Image path bonus (successful extraction)
            if result.image_path:
                score += 0.05
            
            if score > best_score:
                best_score = score
                best_result = result
        
        # Create consensus result if multiple high-scoring results
        if len([r for r in group if r.confidence > 0.8]) > 1:
            best_result = self._create_consensus_result(group, best_result)
        
        return best_result
    
    def _create_consensus_result(self, group: List[ExtractionResult], base_result: ExtractionResult) -> ExtractionResult:
        """Create a consensus result from multiple similar results."""
        
        # Use base result as template
        consensus_result = ExtractionResult(
            element_id=base_result.element_id,
            element_type=base_result.element_type,
            page_number=base_result.page_number,
            bounding_box=base_result.bounding_box,
            image_path=base_result.image_path,
            caption=base_result.caption,
            confidence=0.0,  # Will be calculated
            extraction_method="hybrid_consensus",
            metadata=base_result.metadata.copy()
        )
        
        # Calculate consensus confidence (average of top results)
        confidences = [r.confidence for r in group]
        consensus_result.confidence = statistics.mean(confidences)
        
        # Add consensus metadata
        consensus_result.metadata.update({
            'consensus_methods': [r.metadata.get('source_method', 'unknown') for r in group],
            'individual_confidences': confidences,
            'consensus_size': len(group)
        })
        
        # Use longest/best caption
        captions = [r.caption for r in group if r.caption]
        if captions:
            consensus_result.caption = max(captions, key=len)
        
        return consensus_result