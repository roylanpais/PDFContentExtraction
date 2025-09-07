
"""
Additional Backend Implementations
=================================

Extended backends for OpenAI GPT-4V, Google Document AI, AWS Textract,
and Hugging Face Transformers to complete the generalized extraction system.
"""

import openai
from google.cloud import documentai
import boto3
from transformers import pipeline
import torch
from PIL import Image
import cv2
import numpy as np

class OpenAIGPT4VBackend(ExtractionBackendInterface):
    """OpenAI GPT-4 Vision backend."""

    def __init__(self):
        self.client = None
        self.model = "gpt-4-vision-preview"

    async def initialize(self, config: ExtractionConfig) -> bool:
        """Initialize OpenAI GPT-4V backend."""
        try:
            api_key = config.api_credentials.get('openai_api_key')
            if not api_key:
                logger.error("OpenAI API key not provided")
                return False

            self.client = openai.AsyncOpenAI(api_key=api_key)

            # Test API connection
            try:
                await self.client.models.list()
                logger.info("OpenAI GPT-4V backend initialized successfully")
                return True
            except Exception as e:
                logger.error(f"OpenAI API test failed: {e}")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize OpenAI GPT-4V backend: {e}")
            return False

    async def detect_content(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Detect content using OpenAI GPT-4V."""
        try:
            images = self._pdf_to_images(pdf_path)
            detected_content = []

            for page_num, image_data in enumerate(images, 1):
                content = await self._analyze_page_with_gpt4v(image_data, page_num)
                detected_content.extend(content)

            return detected_content

        except Exception as e:
            logger.error(f"Content detection failed with OpenAI GPT-4V: {e}")
            return []

    async def extract_content(self, pdf_path: str, content_specs: List[Dict]) -> List[ExtractedContent]:
        """Extract specified content using OpenAI GPT-4V."""
        extracted_items = []

        try:
            images = self._pdf_to_images(pdf_path)

            for spec in content_specs:
                page_num = spec.get('page', 1)
                if page_num <= len(images):
                    image_data = images[page_num - 1]

                    extracted = await self._extract_with_gpt4v(image_data, spec, page_num)
                    if extracted:
                        extracted_items.append(extracted)

            return extracted_items

        except Exception as e:
            logger.error(f"Content extraction failed with OpenAI GPT-4V: {e}")
            return []

    async def _analyze_page_with_gpt4v(self, image_data: bytes, page_num: int) -> List[Dict]:
        """Analyze a page using GPT-4V."""
        try:
            # Convert image to base64
            image_b64 = base64.b64encode(image_data).decode('utf-8')

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Analyze this document page and identify all extractable content items. 
                                For each item, provide: type (figure/table/algorithm/equation/diagram), 
                                title, description, and location. Return as JSON array."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_b64}"}
                            }
                        ]
                    }
                ],
                max_tokens=2048,
                temperature=0.1
            )

            content_text = response.choices[0].message.content

            try:
                detected_items = json.loads(content_text)
                for item in detected_items:
                    item['page'] = page_num
                    item['detection_method'] = 'openai_gpt4v'
                return detected_items
            except json.JSONDecodeError:
                return self._parse_gpt4v_response(content_text, page_num)

        except Exception as e:
            logger.error(f"GPT-4V page analysis failed: {e}")
            return []

    async def _extract_with_gpt4v(self, image_data: bytes, spec: Dict, page_num: int) -> Optional[ExtractedContent]:
        """Extract specific content using GPT-4V."""
        try:
            image_b64 = base64.b64encode(image_data).decode('utf-8')

            content_type = spec.get('type', 'figure')
            target_description = spec.get('description', spec.get('title', ''))

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"""Extract and analyze the {content_type} described as "{target_description}" 
                                from this document page. Provide comprehensive details including title, description, 
                                any text content, and technical specifications. Format as JSON."""
                            },
                            {
                                "type": "image_url", 
                                "image_url": {"url": f"data:image/png;base64,{image_b64}"}
                            }
                        ]
                    }
                ],
                max_tokens=4096,
                temperature=0.1
            )

            content_text = response.choices[0].message.content
            return self._create_extracted_content_from_gpt4v(content_text, spec, page_num)

        except Exception as e:
            logger.error(f"GPT-4V content extraction failed: {e}")
            return None

    def get_supported_content_types(self) -> List[ContentType]:
        """GPT-4V supports all content types through vision understanding."""
        return list(ContentType)

    def _pdf_to_images(self, pdf_path: str) -> List[bytes]:
        """Convert PDF to images - implement with actual PDF library."""
        # Placeholder implementation
        return []

    def _parse_gpt4v_response(self, response_text: str, page_num: int) -> List[Dict]:
        """Parse non-JSON GPT-4V response."""
        # Implementation for flexible parsing
        return []

    def _create_extracted_content_from_gpt4v(self, response_text: str, spec: Dict, page_num: int) -> Optional[ExtractedContent]:
        """Create ExtractedContent from GPT-4V response."""
        try:
            data = json.loads(response_text)

            return ExtractedContent(
                content_id=f"{spec.get('type', 'content')}_{page_num}_{int(time.time())}",
                content_type=ContentType(spec.get('type', 'figure')),
                title=data.get('title', spec.get('title', 'Untitled')),
                description=data.get('description', ''),
                page_number=page_num,
                text_content=data.get('text_content', ''),
                metadata=data.get('technical_details', {}),
                confidence_score=0.92,  # GPT-4V provides high-quality results
                extraction_method="openai_gpt4v"
            )
        except Exception as e:
            logger.error(f"Failed to create ExtractedContent from GPT-4V: {e}")
            return None

class GoogleDocumentAIBackend(ExtractionBackendInterface):
    """Google Document AI backend."""

    def __init__(self):
        self.client = None
        self.processor_path = None

    async def initialize(self, config: ExtractionConfig) -> bool:
        """Initialize Google Document AI backend."""
        try:
            project_id = config.api_credentials.get('google_project_id')
            location = config.api_credentials.get('google_location', 'us')
            processor_id = config.api_credentials.get('google_processor_id')

            if not all([project_id, processor_id]):
                logger.error("Google Cloud credentials not provided")
                return False

            self.client = documentai.DocumentProcessorServiceClient()
            self.processor_path = self.client.processor_path(project_id, location, processor_id)

            logger.info("Google Document AI backend initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Google Document AI backend: {e}")
            return False

    async def detect_content(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Detect content using Google Document AI."""
        try:
            # Process document
            with open(pdf_path, 'rb') as pdf_file:
                document_content = pdf_file.read()

            document = documentai.Document(content=document_content, mime_type='application/pdf')
            request = documentai.ProcessRequest(name=self.processor_path, document=document)

            result = self.client.process_document(request=request)
            processed_doc = result.document

            detected_content = []

            # Extract entities and layouts
            for entity in processed_doc.entities:
                detected_content.append({
                    'type': entity.type_.lower(),
                    'title': entity.mention_text,
                    'description': f"Detected {entity.type_}",
                    'page': self._get_page_number(entity.page_anchor),
                    'confidence': entity.confidence
                })

            return detected_content

        except Exception as e:
            logger.error(f"Google Document AI detection failed: {e}")
            return []

    async def extract_content(self, pdf_path: str, content_specs: List[Dict]) -> List[ExtractedContent]:
        """Extract specified content using Google Document AI."""
        # Implementation for Google Document AI extraction
        return []

    def get_supported_content_types(self) -> List[ContentType]:
        """Google Document AI supports structured document understanding."""
        return [
            ContentType.TABLE,
            ContentType.FIGURE,
            ContentType.SECTION,
            ContentType.CUSTOM
        ]

    def _get_page_number(self, page_anchor) -> int:
        """Extract page number from page anchor."""
        if page_anchor and page_anchor.page_refs:
            return page_anchor.page_refs[0].page + 1
        return 1

class AWSTextractBackend(ExtractionBackendInterface):
    """AWS Textract backend."""

    def __init__(self):
        self.textract_client = None

    async def initialize(self, config: ExtractionConfig) -> bool:
        """Initialize AWS Textract backend."""
        try:
            aws_access_key = config.api_credentials.get('aws_access_key_id')
            aws_secret_key = config.api_credentials.get('aws_secret_access_key')
            region = config.api_credentials.get('aws_region', 'us-east-1')

            if not aws_access_key or not aws_secret_key:
                logger.error("AWS credentials not provided")
                return False

            self.textract_client = boto3.client(
                'textract',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=region
            )

            logger.info("AWS Textract backend initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize AWS Textract backend: {e}")
            return False

    async def detect_content(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Detect content using AWS Textract."""
        try:
            with open(pdf_path, 'rb') as pdf_file:
                document_bytes = pdf_file.read()

            # Use Textract analyze_document for advanced features
            response = self.textract_client.analyze_document(
                Document={'Bytes': document_bytes},
                FeatureTypes=['TABLES', 'FORMS']
            )

            detected_content = []

            # Process tables
            for block in response.get('Blocks', []):
                if block['BlockType'] == 'TABLE':
                    detected_content.append({
                        'type': 'table',
                        'title': f"Table {len([c for c in detected_content if c['type'] == 'table']) + 1}",
                        'description': 'Detected table',
                        'page': block.get('Page', 1),
                        'confidence': block.get('Confidence', 0.0) / 100.0
                    })

            return detected_content

        except Exception as e:
            logger.error(f"AWS Textract detection failed: {e}")
            return []

    async def extract_content(self, pdf_path: str, content_specs: List[Dict]) -> List[ExtractedContent]:
        """Extract specified content using AWS Textract."""
        # Implementation for AWS Textract extraction
        return []

    def get_supported_content_types(self) -> List[ContentType]:
        """AWS Textract primarily supports tables and forms."""
        return [
            ContentType.TABLE,
            ContentType.SECTION,
            ContentType.CUSTOM
        ]

class HuggingFaceTransformersBackend(ExtractionBackendInterface):
    """Hugging Face Transformers backend using open-source models."""

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.vision_model = None
        self.text_model = None

    async def initialize(self, config: ExtractionConfig) -> bool:
        """Initialize Hugging Face Transformers backend."""
        try:
            # Load vision-language model (e.g., BLIP, LLaVA, or similar)
            model_name = config.api_credentials.get('hf_model_name', 'Salesforce/blip-image-captioning-base')

            self.vision_model = pipeline(
                "image-to-text",
                model=model_name,
                device=0 if self.device == "cuda" else -1
            )

            logger.info(f"Hugging Face Transformers backend initialized with {model_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Hugging Face backend: {e}")
            return False

    async def detect_content(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Detect content using Hugging Face models."""
        try:
            images = self._pdf_to_images(pdf_path)
            detected_content = []

            for page_num, image_data in enumerate(images, 1):
                # Convert bytes to PIL Image
                image = Image.open(BytesIO(image_data))

                # Use vision model to analyze the page
                result = self.vision_model(image)

                # Parse results (this would need custom logic based on model output)
                if result and len(result) > 0:
                    description = result[0].get('generated_text', '')

                    # Simple heuristics to detect content types
                    if 'figure' in description.lower() or 'graph' in description.lower():
                        detected_content.append({
                            'type': 'figure',
                            'title': f"Figure from page {page_num}",
                            'description': description,
                            'page': page_num,
                            'confidence': 0.75
                        })
                    elif 'table' in description.lower():
                        detected_content.append({
                            'type': 'table',
                            'title': f"Table from page {page_num}",
                            'description': description,
                            'page': page_num,
                            'confidence': 0.75
                        })

            return detected_content

        except Exception as e:
            logger.error(f"Hugging Face content detection failed: {e}")
            return []

    async def extract_content(self, pdf_path: str, content_specs: List[Dict]) -> List[ExtractedContent]:
        """Extract specified content using Hugging Face models."""
        extracted_items = []

        try:
            images = self._pdf_to_images(pdf_path)

            for spec in content_specs:
                page_num = spec.get('page', 1)
                if page_num <= len(images):
                    image_data = images[page_num - 1]
                    image = Image.open(BytesIO(image_data))

                    # Use vision model for extraction
                    result = self.vision_model(image)

                    if result and len(result) > 0:
                        description = result[0].get('generated_text', '')

                        extracted_content = ExtractedContent(
                            content_id=f"{spec.get('type', 'content')}_{page_num}_{int(time.time())}",
                            content_type=ContentType(spec.get('type', 'figure')),
                            title=spec.get('title', f"Content from page {page_num}"),
                            description=description,
                            page_number=page_num,
                            text_content=description,
                            confidence_score=0.75,
                            extraction_method="huggingface_transformers"
                        )

                        extracted_items.append(extracted_content)

            return extracted_items

        except Exception as e:
            logger.error(f"Hugging Face content extraction failed: {e}")
            return []

    def get_supported_content_types(self) -> List[ContentType]:
        """Hugging Face models support various content types depending on the model."""
        return [
            ContentType.FIGURE,
            ContentType.DIAGRAM,
            ContentType.CUSTOM
        ]

    def _pdf_to_images(self, pdf_path: str) -> List[bytes]:
        """Convert PDF to images."""
        # Placeholder - implement with actual PDF library
        return []

class TraditionalCVBackend(ExtractionBackendInterface):
    """Traditional computer vision backend using OpenCV and classical techniques."""

    def __init__(self):
        self.initialized = False

    async def initialize(self, config: ExtractionConfig) -> bool:
        """Initialize traditional CV backend."""
        try:
            # No external API required for traditional CV
            self.initialized = True
            logger.info("Traditional CV backend initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Traditional CV backend: {e}")
            return False

    async def detect_content(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Detect content using traditional computer vision techniques."""
        try:
            images = self._pdf_to_images(pdf_path)
            detected_content = []

            for page_num, image_data in enumerate(images, 1):
                # Convert to OpenCV format
                nparr = np.frombuffer(image_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                # Detect figures using contour analysis
                figures = self._detect_figures_cv(img)
                for i, fig in enumerate(figures):
                    detected_content.append({
                        'type': 'figure',
                        'title': f"Figure {i+1} from page {page_num}",
                        'description': 'Detected using contour analysis',
                        'page': page_num,
                        'bbox': fig['bbox'],
                        'confidence': fig['confidence']
                    })

                # Detect tables using line detection
                tables = self._detect_tables_cv(img)
                for i, table in enumerate(tables):
                    detected_content.append({
                        'type': 'table',
                        'title': f"Table {i+1} from page {page_num}",
                        'description': 'Detected using line analysis',
                        'page': page_num,
                        'bbox': table['bbox'],
                        'confidence': table['confidence']
                    })

            return detected_content

        except Exception as e:
            logger.error(f"Traditional CV detection failed: {e}")
            return []

    async def extract_content(self, pdf_path: str, content_specs: List[Dict]) -> List[ExtractedContent]:
        """Extract specified content using traditional CV."""
        # Implementation for traditional CV extraction
        return []

    def get_supported_content_types(self) -> List[ContentType]:
        """Traditional CV supports basic visual content types."""
        return [
            ContentType.FIGURE,
            ContentType.TABLE,
            ContentType.DIAGRAM
        ]

    def _detect_figures_cv(self, img: np.ndarray) -> List[Dict]:
        """Detect figures using contour analysis."""
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply threshold to get binary image
        _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        figures = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 1000:  # Filter small contours
                x, y, w, h = cv2.boundingRect(contour)
                figures.append({
                    'bbox': [x, y, x+w, y+h],
                    'confidence': 0.6,
                    'area': area
                })

        return figures

    def _detect_tables_cv(self, img: np.ndarray) -> List[Dict]:
        """Detect tables using line detection."""
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect horizontal and vertical lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))

        horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel, iterations=2)

        # Combine lines to find table regions
        table_mask = cv2.addWeighted(horizontal_lines, 0.5, vertical_lines, 0.5, 0.0)

        # Find contours in table mask
        contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        tables = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 5000:  # Filter small regions
                x, y, w, h = cv2.boundingRect(contour)
                tables.append({
                    'bbox': [x, y, x+w, y+h],
                    'confidence': 0.7,
                    'area': area
                })

        return tables

    def _pdf_to_images(self, pdf_path: str) -> List[bytes]:
        """Convert PDF to images."""
        # Placeholder implementation
        return []


# Add the new backends to the backend map
def create_backend_map():
    """Create complete backend mapping."""
    return {
        ExtractionBackend.TRADITIONAL_CV: TraditionalCVBackend,
        ExtractionBackend.NVIDIA_NVLM: NVIDIANVLMBackend,
        ExtractionBackend.AZURE_DOCUMENT_INTELLIGENCE: AzureDocumentIntelligenceBackend,
        ExtractionBackend.OPENAI_GPT4V: OpenAIGPT4VBackend,
        ExtractionBackend.GOOGLE_DOCUMENT_AI: GoogleDocumentAIBackend,
        ExtractionBackend.AWS_TEXTRACT: AWSTextractBackend,
        ExtractionBackend.HUGGINGFACE_TRANSFORMERS: HuggingFaceTransformersBackend,
    }


# Configuration factory functions
def create_openai_config(api_key: str) -> ExtractionConfig:
    """Create configuration for OpenAI GPT-4V backend."""
    return ExtractionConfig(
        backend=ExtractionBackend.OPENAI_GPT4V,
        content_types=[ContentType.FIGURE, ContentType.ALGORITHM, ContentType.TABLE, ContentType.EQUATION],
        output_formats=['json', 'markdown'],
        quality_settings={'image_quality': 'high', 'text_accuracy': 'high'},
        api_credentials={'openai_api_key': api_key}
    )

def create_google_config(project_id: str, processor_id: str, location: str = 'us') -> ExtractionConfig:
    """Create configuration for Google Document AI backend."""
    return ExtractionConfig(
        backend=ExtractionBackend.GOOGLE_DOCUMENT_AI,
        content_types=[ContentType.TABLE, ContentType.FIGURE, ContentType.SECTION],
        output_formats=['json'],
        quality_settings={'layout_analysis': 'detailed', 'ocr_accuracy': 'high'},
        api_credentials={
            'google_project_id': project_id,
            'google_processor_id': processor_id,
            'google_location': location
        }
    )

def create_aws_config(access_key: str, secret_key: str, region: str = 'us-east-1') -> ExtractionConfig:
    """Create configuration for AWS Textract backend."""
    return ExtractionConfig(
        backend=ExtractionBackend.AWS_TEXTRACT,
        content_types=[ContentType.TABLE, ContentType.SECTION],
        output_formats=['json'],
        quality_settings={'table_extraction': 'detailed', 'form_detection': 'enabled'},
        api_credentials={
            'aws_access_key_id': access_key,
            'aws_secret_access_key': secret_key,
            'aws_region': region
        }
    )

def create_huggingface_config(model_name: str = 'Salesforce/blip-image-captioning-base') -> ExtractionConfig:
    """Create configuration for Hugging Face Transformers backend."""
    return ExtractionConfig(
        backend=ExtractionBackend.HUGGINGFACE_TRANSFORMERS,
        content_types=[ContentType.FIGURE, ContentType.DIAGRAM, ContentType.CUSTOM],
        output_formats=['json', 'text'],
        quality_settings={'model_precision': 'fp16', 'batch_size': 1},
        api_credentials={'hf_model_name': model_name}
    )

def create_traditional_cv_config() -> ExtractionConfig:
    """Create configuration for Traditional CV backend."""
    return ExtractionConfig(
        backend=ExtractionBackend.TRADITIONAL_CV,
        content_types=[ContentType.FIGURE, ContentType.TABLE, ContentType.DIAGRAM],
        output_formats=['json'],
        quality_settings={'contour_threshold': 1000, 'line_detection_sensitivity': 'medium'},
        api_credentials={}
    )
