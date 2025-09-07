"""
Data models for the PDF Visual Content Extractor.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
from enum import Enum


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
    
    def save(self, output_path: Path) -> bool:
        """Save extracted content to file."""
        try:
            if self.image_path and Path(self.image_path).exists():
                import shutil
                shutil.copy2(self.image_path, output_path)
                return True
            return False
        except Exception:
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
    max_workers: int = 4
    
    # Custom patterns for specific extraction needs
    custom_patterns: List[str] = field(default_factory=list)
    
    # Azure specific settings
    azure_model: str = "prebuilt-layout"
    azure_features: List[str] = field(default_factory=lambda: ["layout"])
    
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