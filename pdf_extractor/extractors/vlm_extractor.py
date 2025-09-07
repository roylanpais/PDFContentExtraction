"""
Vision Language Model (VLM) based extractor implementation.
"""

import base64
import io
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image
import requests
import os

from .base import BaseExtractor
from ..models import ExtractionResult

logger = logging.getLogger(__name__)


class VLMExtractor(BaseExtractor):
    """Extractor using Vision Language Models."""
    
    def __init__(self):
        """Initialize VLM extractor."""
        super().__init__("VLM")
        self.vlm_models = {
            "gpt-4-vision": GPT4VisionModel(),
            "claude-vision": ClaudeVisionModel(),
            "gemini-vision": GeminiVisionModel(),
            "llava": LLaVAModel(),
            "blip2": BLIP2Model()
        }
    
    def extract(self, pdf_path: Path, config) -> List[ExtractionResult]:
        """Extract content using VLM."""
        try:
            # Convert PDF to images
            images = self.preprocess_pdf(pdf_path, config)
            
            # Get VLM model
            vlm_model = self.vlm_models.get(config.vlm_model)
            if not vlm_model:
                raise ValueError(f"Unsupported VLM model: {config.vlm_model}")
            
            results = []
            
            for page_num, image in enumerate(images, 1):
                page_results = self._extract_from_page(
                    image, page_num, config, vlm_model
                )
                results.extend(page_results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"VLM extraction failed: {e}")
            raise
    
    def _extract_from_page(self, image: Image.Image, page_num: int, 
                          config, vlm_model) -> List[ExtractionResult]:
        """Extract content from a single page using VLM."""
        results = []
        
        try:
            # Create extraction prompt based on target type
            prompt = self._create_extraction_prompt(config)
            
            # Query VLM
            response = vlm_model.query(image, prompt, config)
            
            # Parse response
            extracted_elements = self._parse_vlm_response(response, config)
            
            # Create extraction results
            for element in extracted_elements:
                if self._should_include_element(element, config):
                    result = self._create_extraction_result(
                        element, page_num, image, config
                    )
                    results.append(result)
        
        except Exception as e:
            self.logger.error(f"Page {page_num} extraction failed: {e}")
        
        return results
    
    def _create_extraction_prompt(self, config) -> str:
        """Create prompt for VLM based on extraction configuration."""
        base_prompts = {
            "figure": """
            Please identify and locate all figures in this document page. For each figure:
            1. Provide the bounding box coordinates (x1, y1, x2, y2)
            2. Extract the figure caption if present
            3. Identify the figure number/identifier
            4. Provide a confidence score (0-1)
            
            Return the results in JSON format with this structure:
            {
                "figures": [
                    {
                        "id": "figure_1",
                        "bbox": [x1, y1, x2, y2],
                        "caption": "Figure 1. Caption text...",
                        "confidence": 0.95
                    }
                ]
            }
            """,
            
            "algorithm": """
            Please identify and locate all algorithm blocks in this document page. Look for:
            1. Algorithm pseudocode blocks
            2. Procedure definitions
            3. Method descriptions with step-by-step instructions
            
            For each algorithm found:
            1. Provide the bounding box coordinates
            2. Extract the algorithm title/name
            3. Identify any algorithm number
            4. Provide confidence score
            
            Return in JSON format:
            {
                "algorithms": [
                    {
                        "id": "algorithm_1",
                        "bbox": [x1, y1, x2, y2],
                        "title": "Algorithm 1: Adaptive Keyframe Sampling",
                        "confidence": 0.90
                    }
                ]
            }
            """,
            
            "table": """
            Please identify and locate all tables in this document page. For each table:
            1. Provide the bounding box coordinates
            2. Extract the table caption
            3. Identify table structure (rows/columns)
            4. Provide confidence score
            
            Return in JSON format:
            {
                "tables": [
                    {
                        "id": "table_1",
                        "bbox": [x1, y1, x2, y2],
                        "caption": "Table 1. Performance comparison...",
                        "rows": 5,
                        "columns": 3,
                        "confidence": 0.88
                    }
                ]
            }
            """
        }
        
        prompt = base_prompts.get(config.target_type.value, base_prompts["figure"])
        
        # Add specific identifier if provided
        if config.target_identifier:
            prompt += f"\n\nSpecifically look for: {config.target_identifier}"
        
        # Add custom patterns if provided
        if config.custom_patterns:
            patterns_text = ", ".join(config.custom_patterns)
            prompt += f"\n\nAlso look for these patterns: {patterns_text}"
        
        return prompt
    
    def _parse_vlm_response(self, response: str, config) -> List[Dict[str, Any]]:
        """Parse VLM response to extract structured data."""
        try:
            # Try to parse as JSON
            if response.strip().startswith('{'):
                data = json.loads(response)
            else:
                # Extract JSON from response if it's embedded in text
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    self.logger.warning("Could not parse VLM response as JSON")
                    return []
            
            # Extract elements based on target type
            type_key = f"{config.target_type.value}s"
            elements = data.get(type_key, [])
            
            return elements
            
        except Exception as e:
            self.logger.error(f"Failed to parse VLM response: {e}")
            return []
    
    def _should_include_element(self, element: Dict[str, Any], config) -> bool:
        """Check if element should be included based on configuration."""
        # Check confidence threshold
        if element.get('confidence', 0) < config.confidence_threshold:
            return False
        
        # Check specific identifier if provided
        if config.target_identifier:
            element_text = element.get('caption', '') + element.get('title', '')
            if config.target_identifier.lower() not in element_text.lower():
                return False
        
        return True
    
    def _create_extraction_result(self, element: Dict[str, Any], 
                                page_num: int, image: Image.Image, 
                                config) -> ExtractionResult:
        """Create extraction result from element data."""
        # Extract image region if bounding box provided
        extracted_image_path = None
        if 'bbox' in element:
            bbox = element['bbox']
            cropped_image = self.extract_bounding_box(image, bbox)
            
            # Save cropped image
            output_dir = Path(config.output_dir) / "extracted_images"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{element['id']}_page_{page_num}.{config.output_format}"
            image_path = output_dir / filename
            
            if self.save_image(cropped_image, image_path, config.output_format):
                extracted_image_path = str(image_path)
        
        return ExtractionResult(
            element_id=element['id'],
            element_type=config.target_type.value,
            page_number=page_num,
            bounding_box=element.get('bbox'),
            image_path=extracted_image_path,
            caption=element.get('caption') or element.get('title'),
            confidence=element.get('confidence', 0.0),
            extraction_method=f"vlm_{config.vlm_model}",
            metadata={
                'vlm_model': config.vlm_model,
                'raw_response': element
            }
        )


class BaseVLMModel:
    """Base class for VLM model implementations."""
    
    def __init__(self, model_name: str):
        """Initialize VLM model."""
        self.model_name = model_name
        self.logger = logging.getLogger(f"{__name__}.{model_name}")
    
    def query(self, image: Image.Image, prompt: str, config) -> str:
        """Query the VLM with image and prompt."""
        raise NotImplementedError
    
    def encode_image(self, image: Image.Image) -> str:
        """Encode image to base64 for API calls."""
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')


class GPT4VisionModel(BaseVLMModel):
    """OpenAI GPT-4 Vision model implementation."""
    
    def __init__(self):
        super().__init__("gpt-4-vision")
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
    
    def query(self, image: Image.Image, prompt: str, config) -> str:
        """Query GPT-4 Vision API."""
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.api_key)
            
            # Encode image
            base64_image = self.encode_image(image)
            
            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                temperature=config.vlm_temperature,
                max_tokens=config.vlm_max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"GPT-4 Vision query failed: {e}")
            raise


class ClaudeVisionModel(BaseVLMModel):
    """Anthropic Claude Vision model implementation."""
    
    def __init__(self):
        super().__init__("claude-vision")
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    def query(self, image: Image.Image, prompt: str, config) -> str:
        """Query Claude Vision API."""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            # Encode image
            base64_image = self.encode_image(image)
            
            message = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=config.vlm_max_tokens,
                temperature=config.vlm_temperature,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": base64_image
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            return message.content[0].text
            
        except Exception as e:
            self.logger.error(f"Claude Vision query failed: {e}")
            raise


class GeminiVisionModel(BaseVLMModel):
    """Google Gemini Vision model implementation."""
    
    def __init__(self):
        super().__init__("gemini-vision")
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
    
    def query(self, image: Image.Image, prompt: str, config) -> str:
        """Query Gemini Vision API."""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel('gemini-pro-vision')
            
            response = model.generate_content([prompt, image])
            return response.text
            
        except Exception as e:
            self.logger.error(f"Gemini Vision query failed: {e}")
            raise


class LLaVAModel(BaseVLMModel):
    """LLaVA open-source model implementation."""
    
    def __init__(self):
        super().__init__("llava")
        self.model = None
        self.processor = None
        self._load_model()
    
    def _load_model(self):
        """Load LLaVA model and processor."""
        try:
            from transformers import LlavaNextProcessor, LlavaNextForConditionalGeneration
            import torch
            
            model_name = "llava-hf/llava-v1.6-mistral-7b-hf"
            
            self.processor = LlavaNextProcessor.from_pretrained(model_name)
            self.model = LlavaNextForConditionalGeneration.from_pretrained(
                model_name,
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True
            )
            
            if torch.cuda.is_available():
                self.model = self.model.to("cuda")
            
        except Exception as e:
            self.logger.error(f"Failed to load LLaVA model: {e}")
            raise
    
    def query(self, image: Image.Image, prompt: str, config) -> str:
        """Query LLaVA model."""
        try:
            import torch
            
            # Prepare inputs
            inputs = self.processor(prompt, image, return_tensors="pt")
            
            if torch.cuda.is_available():
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
            # Generate response
            with torch.no_grad():
                output = self.model.generate(**inputs, max_new_tokens=200, do_sample=False)
            
            response = self.processor.decode(output[0], skip_special_tokens=True)
            
            # Extract response after the prompt
            response = response.split(prompt)[-1].strip()
            
            return response
            
        except Exception as e:
            self.logger.error(f"LLaVA query failed: {e}")
            raise


class BLIP2Model(BaseVLMModel):
    """BLIP-2 model implementation."""
    
    def __init__(self):
        super().__init__("blip2")
        self.model = None
        self.processor = None
        self._load_model()
    
    def _load_model(self):
        """Load BLIP-2 model and processor."""
        try:
            from transformers import Blip2Processor, Blip2ForConditionalGeneration
            import torch
            
            model_name = "Salesforce/blip2-opt-2.7b"
            
            self.processor = Blip2Processor.from_pretrained(model_name)
            self.model = Blip2ForConditionalGeneration.from_pretrained(
                model_name,
                torch_dtype=torch.float16
            )
            
            if torch.cuda.is_available():
                self.model = self.model.to("cuda")
                
        except Exception as e:
            self.logger.error(f"Failed to load BLIP-2 model: {e}")
            raise
    
    def query(self, image: Image.Image, prompt: str, config) -> str:
        """Query BLIP-2 model."""
        try:
            import torch
            
            # BLIP-2 works better with shorter, more direct prompts
            simplified_prompt = f"Question: {prompt} Answer:"
            
            inputs = self.processor(image, simplified_prompt, return_tensors="pt")
            
            if torch.cuda.is_available():
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
            with torch.no_grad():
                generated_ids = self.model.generate(**inputs, max_new_tokens=100)
            
            response = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            # Extract answer part
            if "Answer:" in response:
                response = response.split("Answer:")[-1].strip()
            
            return response
            
        except Exception as e:
            self.logger.error(f"BLIP-2 query failed: {e}")
            raise