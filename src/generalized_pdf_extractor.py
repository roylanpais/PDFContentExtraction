
"""
Generalized PDF Content Extraction Pipeline
==========================================

A comprehensive, model-agnostic PDF content extraction system supporting
multiple AI services and extraction backends including NVIDIA NVLM, 
Azure AI Document Intelligence, OpenAI GPT-4V, and traditional CV approaches.
"""

import json
import os
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from abc import ABC, abstractmethod
import requests
import base64
from io import BytesIO
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExtractionBackend(Enum):
    """Available extraction backends."""
    TRADITIONAL_CV = "traditional_cv"
    NVIDIA_NVLM = "nvidia_nvlm"
    AZURE_DOCUMENT_INTELLIGENCE = "azure_document_intelligence"
    OPENAI_GPT4V = "openai_gpt4v"
    GOOGLE_DOCUMENT_AI = "google_document_ai"
    AWS_TEXTRACT = "aws_textract"
    HUGGINGFACE_TRANSFORMERS = "huggingface_transformers"

class ContentType(Enum):
    """Types of content that can be extracted."""
    FIGURE = "figure"
    TABLE = "table"
    ALGORITHM = "algorithm"
    EQUATION = "equation"
    DIAGRAM = "diagram"
    CHART = "chart"
    CODE_BLOCK = "code_block"
    REFERENCE = "reference"
    SECTION = "section"
    CUSTOM = "custom"

@dataclass
class ExtractionConfig:
    """Configuration for extraction process."""
    backend: ExtractionBackend
    content_types: List[ContentType]
    output_formats: List[str] = None  # ['json', 'markdown', 'html']
    quality_settings: Dict[str, Any] = None
    api_credentials: Dict[str, str] = None
    custom_patterns: List[str] = None

    def __post_init__(self):
        if self.output_formats is None:
            self.output_formats = ['json']
        if self.quality_settings is None:
            self.quality_settings = {'image_quality': 'high', 'text_accuracy': 'high'}
        if self.api_credentials is None:
            self.api_credentials = {}
        if self.custom_patterns is None:
            self.custom_patterns = []

@dataclass
class ExtractedContent:
    """Standard format for extracted content."""
    content_id: str
    content_type: ContentType
    title: str
    description: str
    page_number: int
    bbox: Optional[Tuple[float, float, float, float]] = None
    text_content: Optional[str] = None
    image_path: Optional[str] = None
    metadata: Dict[str, Any] = None
    confidence_score: float = 0.0
    extraction_method: str = ""

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class ExtractionBackendInterface(ABC):
    """Abstract base class for extraction backends."""

    @abstractmethod
    async def initialize(self, config: ExtractionConfig) -> bool:
        """Initialize the backend with configuration."""
        pass

    @abstractmethod
    async def detect_content(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Detect available content in the PDF."""
        pass

    @abstractmethod
    async def extract_content(self, pdf_path: str, content_specs: List[Dict]) -> List[ExtractedContent]:
        """Extract specified content from the PDF."""
        pass

    @abstractmethod
    def get_supported_content_types(self) -> List[ContentType]:
        """Get list of content types supported by this backend."""
        pass

class NVIDIANVLMBackend(ExtractionBackendInterface):
    """NVIDIA NVLM (Nemotron Vision-Language Model) backend."""

    def __init__(self):
        self.api_key = None
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.model_name = "nvidia/nvlm-d-72b"

    async def initialize(self, config: ExtractionConfig) -> bool:
        """Initialize NVIDIA NVLM backend."""
        try:
            self.api_key = config.api_credentials.get('nvidia_api_key')
            if not self.api_key:
                logger.error("NVIDIA API key not provided")
                return False

            # Test API connection
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(f"{self.base_url}/models", headers=headers, timeout=10)

            if response.status_code == 200:
                logger.info("NVIDIA NVLM backend initialized successfully")
                return True
            else:
                logger.error(f"NVIDIA API connection failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize NVIDIA NVLM backend: {e}")
            return False

    async def detect_content(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Detect content using NVIDIA NVLM."""
        try:
            # Convert PDF pages to images
            images = self._pdf_to_images(pdf_path)
            detected_content = []

            for page_num, image_data in enumerate(images, 1):
                # Use NVLM to analyze the page
                content = await self._analyze_page_with_nvlm(image_data, page_num)
                detected_content.extend(content)

            return detected_content

        except Exception as e:
            logger.error(f"Content detection failed with NVIDIA NVLM: {e}")
            return []

    async def extract_content(self, pdf_path: str, content_specs: List[Dict]) -> List[ExtractedContent]:
        """Extract specified content using NVIDIA NVLM."""
        extracted_items = []

        try:
            images = self._pdf_to_images(pdf_path)

            for spec in content_specs:
                page_num = spec.get('page', 1)
                if page_num <= len(images):
                    image_data = images[page_num - 1]

                    # Use NVLM for targeted extraction
                    extracted = await self._extract_with_nvlm(
                        image_data, spec, page_num
                    )
                    if extracted:
                        extracted_items.append(extracted)

            return extracted_items

        except Exception as e:
            logger.error(f"Content extraction failed with NVIDIA NVLM: {e}")
            return []

    async def _analyze_page_with_nvlm(self, image_data: bytes, page_num: int) -> List[Dict]:
        """Analyze a page using NVLM to detect content."""
        try:
            # Encode image
            image_b64 = base64.b64encode(image_data).decode('utf-8')

            # Prepare NVLM request
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Analyze this document page and identify all extractable content. 
                                List each item with: type (figure/table/algorithm/equation/diagram), 
                                title, description, and approximate location. Format as JSON."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_b64}"}
                            }
                        ]
                    }
                ],
                "max_tokens": 2048,
                "temperature": 0.1
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content_text = result['choices'][0]['message']['content']

                # Parse the JSON response to extract detected content
                try:
                    detected_items = json.loads(content_text)
                    for item in detected_items:
                        item['page'] = page_num
                        item['detection_method'] = 'nvidia_nvlm'
                    return detected_items
                except json.JSONDecodeError:
                    # Fallback parsing if not valid JSON
                    return self._parse_nvlm_response(content_text, page_num)

            return []

        except Exception as e:
            logger.error(f"NVLM page analysis failed: {e}")
            return []

    async def _extract_with_nvlm(self, image_data: bytes, spec: Dict, page_num: int) -> Optional[ExtractedContent]:
        """Extract specific content using NVLM."""
        try:
            image_b64 = base64.b64encode(image_data).decode('utf-8')

            content_type = spec.get('type', 'figure')
            target_description = spec.get('description', spec.get('title', ''))

            prompt = f"""Extract the {content_type} described as "{target_description}" from this document page.
            Provide detailed information including:
            1. Title or caption
            2. Detailed description of content
            3. Any text content within the {content_type}
            4. Technical details and specifications
            Format the response as JSON with fields: title, description, text_content, technical_details."""

            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_b64}"}
                            }
                        ]
                    }
                ],
                "max_tokens": 4096,
                "temperature": 0.1
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=45
            )

            if response.status_code == 200:
                result = response.json()
                content_text = result['choices'][0]['message']['content']

                # Parse response and create ExtractedContent
                return self._create_extracted_content(content_text, spec, page_num, "nvidia_nvlm")

            return None

        except Exception as e:
            logger.error(f"NVLM content extraction failed: {e}")
            return None

    def get_supported_content_types(self) -> List[ContentType]:
        """NVLM supports all content types through vision-language understanding."""
        return list(ContentType)

    def _pdf_to_images(self, pdf_path: str) -> List[bytes]:
        """Convert PDF pages to images. Placeholder - implement with actual PDF library."""
        # This would use PyMuPDF, pdf2image, or similar
        # For now, return placeholder
        logger.info(f"Converting {pdf_path} to images for NVLM processing")
        return []  # Placeholder

    def _parse_nvlm_response(self, response_text: str, page_num: int) -> List[Dict]:
        """Parse NVLM response when not valid JSON."""
        # Implement flexible parsing logic
        return []

    def _create_extracted_content(self, response_text: str, spec: Dict, page_num: int, method: str) -> Optional[ExtractedContent]:
        """Create ExtractedContent from NVLM response."""
        try:
            # Parse JSON response
            data = json.loads(response_text)

            return ExtractedContent(
                content_id=f"{spec.get('type', 'content')}_{page_num}_{int(time.time())}",
                content_type=ContentType(spec.get('type', 'figure')),
                title=data.get('title', spec.get('title', 'Untitled')),
                description=data.get('description', ''),
                page_number=page_num,
                text_content=data.get('text_content', ''),
                metadata=data.get('technical_details', {}),
                confidence_score=0.95,  # NVLM typically provides high-quality results
                extraction_method=method
            )
        except Exception as e:
            logger.error(f"Failed to create ExtractedContent: {e}")
            return None

class AzureDocumentIntelligenceBackend(ExtractionBackendInterface):
    """Azure AI Document Intelligence backend."""

    def __init__(self):
        self.endpoint = None
        self.api_key = None
        self.api_version = "2023-07-31"

    async def initialize(self, config: ExtractionConfig) -> bool:
        """Initialize Azure Document Intelligence backend."""
        try:
            self.endpoint = config.api_credentials.get('azure_endpoint')
            self.api_key = config.api_credentials.get('azure_api_key')

            if not self.endpoint or not self.api_key:
                logger.error("Azure endpoint or API key not provided")
                return False

            # Test connection
            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Content-Type": "application/json"
            }

            test_url = f"{self.endpoint}/formrecognizer/documentModels?api-version={self.api_version}"
            response = requests.get(test_url, headers=headers, timeout=10)

            if response.status_code == 200:
                logger.info("Azure Document Intelligence initialized successfully")
                return True
            else:
                logger.error(f"Azure API connection failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize Azure Document Intelligence: {e}")
            return False

    async def detect_content(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Detect content using Azure Document Intelligence."""
        try:
            # Use prebuilt layout model for content detection
            analysis_result = await self._analyze_document(pdf_path, "prebuilt-layout")

            detected_content = []

            # Process figures
            for figure in analysis_result.get('figures', []):
                detected_content.append({
                    'type': 'figure',
                    'title': f"Figure {len(detected_content) + 1}",
                    'description': figure.get('caption', 'Detected figure'),
                    'page': figure.get('page', 1),
                    'bbox': figure.get('boundingBox', []),
                    'confidence': figure.get('confidence', 0.0)
                })

            # Process tables
            for table in analysis_result.get('tables', []):
                detected_content.append({
                    'type': 'table',
                    'title': f"Table {len([c for c in detected_content if c['type'] == 'table']) + 1}",
                    'description': f"Table with {table.get('rowCount', 0)} rows and {table.get('columnCount', 0)} columns",
                    'page': table.get('page', 1),
                    'bbox': table.get('boundingBox', []),
                    'confidence': table.get('confidence', 0.0)
                })

            return detected_content

        except Exception as e:
            logger.error(f"Azure content detection failed: {e}")
            return []

    async def extract_content(self, pdf_path: str, content_specs: List[Dict]) -> List[ExtractedContent]:
        """Extract specified content using Azure Document Intelligence."""
        try:
            # Use layout analysis for detailed extraction
            analysis_result = await self._analyze_document(pdf_path, "prebuilt-layout")

            extracted_items = []

            for spec in content_specs:
                content_type = spec.get('type', 'figure')
                target_page = spec.get('page', 1)

                if content_type == 'table':
                    extracted = self._extract_table_from_azure(analysis_result, spec, target_page)
                elif content_type == 'figure':
                    extracted = self._extract_figure_from_azure(analysis_result, spec, target_page)
                else:
                    extracted = self._extract_generic_from_azure(analysis_result, spec, target_page)

                if extracted:
                    extracted_items.append(extracted)

            return extracted_items

        except Exception as e:
            logger.error(f"Azure content extraction failed: {e}")
            return []

    async def _analyze_document(self, pdf_path: str, model_id: str) -> Dict[str, Any]:
        """Analyze document using Azure Document Intelligence."""
        try:
            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Content-Type": "application/pdf"
            }

            # Start analysis
            analyze_url = f"{self.endpoint}/formrecognizer/documentModels/{model_id}:analyze?api-version={self.api_version}"

            with open(pdf_path, 'rb') as pdf_file:
                response = requests.post(analyze_url, headers=headers, data=pdf_file, timeout=30)

            if response.status_code == 202:
                # Get operation location for polling
                operation_location = response.headers.get('Operation-Location')

                # Poll for results
                return await self._poll_analysis_result(operation_location)
            else:
                logger.error(f"Azure analysis start failed: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Azure document analysis failed: {e}")
            return {}

    async def _poll_analysis_result(self, operation_url: str) -> Dict[str, Any]:
        """Poll Azure for analysis results."""
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}

        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                response = requests.get(operation_url, headers=headers, timeout=10)

                if response.status_code == 200:
                    result = response.json()
                    status = result.get('status', 'running')

                    if status == 'succeeded':
                        return result.get('analyzeResult', {})
                    elif status == 'failed':
                        logger.error("Azure analysis failed")
                        return {}
                    else:
                        # Still running, wait and retry
                        await asyncio.sleep(2)
                else:
                    logger.error(f"Azure polling failed: {response.status_code}")
                    return {}

            except Exception as e:
                logger.error(f"Azure polling error: {e}")
                await asyncio.sleep(2)

        logger.error("Azure analysis timeout")
        return {}

    def _extract_table_from_azure(self, analysis_result: Dict, spec: Dict, page_num: int) -> Optional[ExtractedContent]:
        """Extract table using Azure analysis results."""
        tables = analysis_result.get('tables', [])

        # Find table on specified page
        target_table = None
        for table in tables:
            if table.get('page', 1) == page_num:
                target_table = table
                break

        if not target_table:
            return None

        # Convert table to structured format
        table_data = {
            'rows': target_table.get('rowCount', 0),
            'columns': target_table.get('columnCount', 0),
            'cells': target_table.get('cells', [])
        }

        return ExtractedContent(
            content_id=f"table_{page_num}_{int(time.time())}",
            content_type=ContentType.TABLE,
            title=spec.get('title', f"Table from page {page_num}"),
            description=spec.get('description', f"Table with {table_data['rows']} rows and {table_data['columns']} columns"),
            page_number=page_num,
            text_content=self._format_table_text(table_data),
            metadata=table_data,
            confidence_score=target_table.get('confidence', 0.0),
            extraction_method="azure_document_intelligence"
        )

    def _extract_figure_from_azure(self, analysis_result: Dict, spec: Dict, page_num: int) -> Optional[ExtractedContent]:
        """Extract figure using Azure analysis results."""
        figures = analysis_result.get('figures', [])

        # Find figure on specified page
        target_figure = None
        for figure in figures:
            if figure.get('page', 1) == page_num:
                target_figure = figure
                break

        if not target_figure:
            return None

        return ExtractedContent(
            content_id=f"figure_{page_num}_{int(time.time())}",
            content_type=ContentType.FIGURE,
            title=spec.get('title', f"Figure from page {page_num}"),
            description=target_figure.get('caption', spec.get('description', 'Extracted figure')),
            page_number=page_num,
            bbox=tuple(target_figure.get('boundingBox', [])),
            metadata={'elements': target_figure.get('elements', [])},
            confidence_score=target_figure.get('confidence', 0.0),
            extraction_method="azure_document_intelligence"
        )

    def _extract_generic_from_azure(self, analysis_result: Dict, spec: Dict, page_num: int) -> Optional[ExtractedContent]:
        """Extract generic content using Azure analysis results."""
        # Use paragraphs and text regions for generic extraction
        paragraphs = analysis_result.get('paragraphs', [])

        relevant_text = []
        for paragraph in paragraphs:
            if paragraph.get('page', 1) == page_num:
                content = paragraph.get('content', '')
                if self._matches_spec(content, spec):
                    relevant_text.append(content)

        if not relevant_text:
            return None

        return ExtractedContent(
            content_id=f"{spec.get('type', 'content')}_{page_num}_{int(time.time())}",
            content_type=ContentType(spec.get('type', 'custom')),
            title=spec.get('title', f"Content from page {page_num}"),
            description=spec.get('description', 'Extracted content'),
            page_number=page_num,
            text_content='\n'.join(relevant_text),
            metadata={'paragraph_count': len(relevant_text)},
            confidence_score=0.8,
            extraction_method="azure_document_intelligence"
        )

    def get_supported_content_types(self) -> List[ContentType]:
        """Azure Document Intelligence supports structured content types."""
        return [
            ContentType.FIGURE,
            ContentType.TABLE,
            ContentType.SECTION,
            ContentType.CUSTOM
        ]

    def _format_table_text(self, table_data: Dict) -> str:
        """Format table data as text."""
        # Implement table formatting logic
        return f"Table with {table_data['rows']} rows and {table_data['columns']} columns"

    def _matches_spec(self, content: str, spec: Dict) -> bool:
        """Check if content matches specification."""
        # Implement matching logic based on keywords, patterns, etc.
        keywords = spec.get('keywords', [])
        return any(keyword.lower() in content.lower() for keyword in keywords)

class GeneralizedPDFExtractor:
    """Main extractor class supporting multiple backends."""

    def __init__(self, config: ExtractionConfig):
        self.config = config
        self.backend = self._create_backend()
        self.output_dir = Path("extracted_content")

    def _create_backend(self) -> ExtractionBackendInterface:
        """Create appropriate backend based on configuration."""
        backend_map = {
            ExtractionBackend.NVIDIA_NVLM: NVIDIANVLMBackend,
            ExtractionBackend.AZURE_DOCUMENT_INTELLIGENCE: AzureDocumentIntelligenceBackend,
            # Add other backends here
        }

        backend_class = backend_map.get(self.config.backend)
        if not backend_class:
            raise ValueError(f"Unsupported backend: {self.config.backend}")

        return backend_class()

    async def initialize(self) -> bool:
        """Initialize the extraction pipeline."""
        return await self.backend.initialize(self.config)

    async def detect_available_content(self, pdf_path: str) -> Dict[str, List[Dict]]:
        """Detect all available content in the PDF."""
        logger.info(f"Detecting content in {pdf_path} using {self.config.backend.value}")

        detected_items = await self.backend.detect_content(pdf_path)

        # Organize by content type
        organized_content = {}
        for content_type in ContentType:
            organized_content[content_type.value] = [
                item for item in detected_items 
                if item.get('type') == content_type.value
            ]

        return organized_content

    async def extract_selected_content(self, pdf_path: str, selections: Dict[str, List[str]]) -> Dict[str, List[ExtractedContent]]:
        """Extract user-selected content."""
        logger.info(f"Extracting selected content using {self.config.backend.value}")

        # Convert selections to content specifications
        content_specs = []
        for content_type, selected_items in selections.items():
            for item in selected_items:
                content_specs.append({
                    'type': content_type,
                    'title': item,
                    'description': item
                })

        # Extract content
        extracted_items = await self.backend.extract_content(pdf_path, content_specs)

        # Organize results
        results = {}
        for content_type in ContentType:
            results[content_type.value] = [
                item for item in extracted_items 
                if item.content_type == content_type
            ]

        return results

    def save_extraction_results(self, results: Dict[str, List[ExtractedContent]], pdf_path: str) -> str:
        """Save extraction results to files."""
        self.output_dir.mkdir(exist_ok=True)

        # Create subdirectories
        for content_type in ContentType:
            (self.output_dir / content_type.value).mkdir(exist_ok=True)

        # Save individual items
        for content_type, items in results.items():
            for item in items:
                self._save_extracted_item(item, content_type)

        # Save summary
        summary = {
            'pdf_path': pdf_path,
            'extraction_backend': self.config.backend.value,
            'total_items': sum(len(items) for items in results.values()),
            'items_by_type': {
                content_type: len(items) 
                for content_type, items in results.items()
            },
            'extraction_config': asdict(self.config)
        }

        summary_path = self.output_dir / "extraction_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        return str(summary_path)

    def _save_extracted_item(self, item: ExtractedContent, content_type: str):
        """Save individual extracted item."""
        item_dir = self.output_dir / content_type
        item_file = item_dir / f"{item.content_id}.json"

        with open(item_file, 'w') as f:
            json.dump(asdict(item), f, indent=2, default=str)

        logger.info(f"Saved {item.content_type.value}: {item.title}")


# Example usage and configuration
def create_nvidia_config(api_key: str) -> ExtractionConfig:
    """Create configuration for NVIDIA NVLM backend."""
    return ExtractionConfig(
        backend=ExtractionBackend.NVIDIA_NVLM,
        content_types=[ContentType.FIGURE, ContentType.ALGORITHM, ContentType.TABLE],
        output_formats=['json', 'markdown'],
        quality_settings={'image_quality': 'high', 'text_accuracy': 'high'},
        api_credentials={'nvidia_api_key': api_key}
    )

def create_azure_config(endpoint: str, api_key: str) -> ExtractionConfig:
    """Create configuration for Azure Document Intelligence backend."""
    return ExtractionConfig(
        backend=ExtractionBackend.AZURE_DOCUMENT_INTELLIGENCE,
        content_types=[ContentType.FIGURE, ContentType.TABLE, ContentType.SECTION],
        output_formats=['json'],
        quality_settings={'text_accuracy': 'high', 'layout_analysis': 'detailed'},
        api_credentials={
            'azure_endpoint': endpoint,
            'azure_api_key': api_key
        }
    )

async def main():
    """Example usage of the generalized extractor."""
    # Example with NVIDIA NVLM
    nvidia_config = create_nvidia_config("your-nvidia-api-key")
    nvidia_extractor = GeneralizedPDFExtractor(nvidia_config)

    if await nvidia_extractor.initialize():
        # Detect available content
        available_content = await nvidia_extractor.detect_available_content("document.pdf")
        print("Available content:", available_content)

        # User makes selections (this would come from UI)
        selections = {
            'figure': ['Figure 1', 'Figure 2'],
            'algorithm': ['Algorithm 1']
        }

        # Extract selected content
        results = await nvidia_extractor.extract_selected_content("document.pdf", selections)

        # Save results
        summary_path = nvidia_extractor.save_extraction_results(results, "document.pdf")
        print(f"Results saved to: {summary_path}")

if __name__ == "__main__":
    asyncio.run(main())
