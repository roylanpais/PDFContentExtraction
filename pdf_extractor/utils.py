"""
Utility functions for the PDF Visual Content Extractor.
"""

import logging
import os
import colorlog
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


def setup_logging(level: str = None) -> None:
    """Set up colored logging for the application."""
    
    # Get log level from environment or parameter
    if level is None:
        level = os.getenv('LOG_LEVEL', 'INFO')
    
    # Convert string to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create colored formatter
    formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    # Set up handler
    handler = colorlog.StreamHandler()
    handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers = []  # Clear existing handlers
    root_logger.addHandler(handler)


def validate_config(config) -> None:
    """Validate extraction configuration."""
    
    # Check required fields
    if not hasattr(config, 'target_type'):
        raise ValueError("target_type is required in configuration")
    
    # Check VLM configuration
    if config.extraction_method.value == "vlm":
        if not config.vlm_model:
            raise ValueError("vlm_model is required for VLM extraction")
        
        # Check API keys for commercial models
        if config.vlm_model == "gpt-4-vision" and not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable required for GPT-4 Vision")
        
        if config.vlm_model == "claude-vision" and not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY environment variable required for Claude Vision")
        
        if config.vlm_model == "gemini-vision" and not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("GOOGLE_API_KEY environment variable required for Gemini Vision")
    
    # Check Azure configuration
    if config.extraction_method.value == "azure":
        if not os.getenv("AZURE_DOC_INTELLIGENCE_ENDPOINT"):
            raise ValueError("AZURE_DOC_INTELLIGENCE_ENDPOINT environment variable required")
        if not os.getenv("AZURE_DOC_INTELLIGENCE_KEY"):
            raise ValueError("AZURE_DOC_INTELLIGENCE_KEY environment variable required")
    
    # Validate confidence threshold
    if not 0 <= config.confidence_threshold <= 1:
        raise ValueError("confidence_threshold must be between 0 and 1")
    
    # Validate pages
    if config.pages and any(p <= 0 for p in config.pages):
        raise ValueError("Page numbers must be positive integers")


def create_output_directory(output_dir: str) -> Path:
    """Create output directory if it doesn't exist."""
    
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_extraction_metadata(results: List, config, output_dir: Path) -> Path:
    """Save extraction metadata to JSON file."""
    
    from datetime import datetime
    
    metadata = {
        "extraction_info": {
            "timestamp": datetime.now().isoformat(),
            "total_results": len(results),
            "target_type": config.target_type.value,
            "extraction_method": config.extraction_method.value,
            "confidence_threshold": config.confidence_threshold
        },
        "configuration": {
            "target_identifier": config.target_identifier,
            "pages": config.pages,
            "vlm_model": config.vlm_model if hasattr(config, 'vlm_model') else None,
            "output_format": config.output_format,
            "include_captions": config.include_captions
        },
        "results": [result.to_dict() for result in results]
    }
    
    metadata_path = output_dir / "extraction_metadata.json"
    
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    return metadata_path


def load_config_from_file(config_path: Path) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config_to_file(config, config_path: Path) -> None:
    """Save configuration to JSON file."""
    
    config_dict = {
        "target_type": config.target_type.value,
        "target_identifier": config.target_identifier,
        "extraction_method": config.extraction_method.value,
        "pages": config.pages,
        "vlm_model": config.vlm_model,
        "confidence_threshold": config.confidence_threshold,
        "output_format": config.output_format,
        "include_captions": config.include_captions,
        "custom_patterns": config.custom_patterns
    }
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_dict, f, indent=2)


def check_dependencies() -> Dict[str, bool]:
    """Check if required dependencies are available."""
    
    dependencies = {}
    
    # Core dependencies
    try:
        import torch
        dependencies['pytorch'] = True
    except ImportError:
        dependencies['pytorch'] = False
    
    try:
        import cv2
        dependencies['opencv'] = True
    except ImportError:
        dependencies['opencv'] = False
    
    try:
        from pdf2image import convert_from_path
        dependencies['pdf2image'] = True
    except ImportError:
        dependencies['pdf2image'] = False
    
    # VLM dependencies
    try:
        import openai
        dependencies['openai'] = True
    except ImportError:
        dependencies['openai'] = False
    
    try:
        import anthropic
        dependencies['anthropic'] = True
    except ImportError:
        dependencies['anthropic'] = False
    
    try:
        from transformers import LlavaNextProcessor
        dependencies['transformers'] = True
    except ImportError:
        dependencies['transformers'] = False
    
    # Azure dependencies
    try:
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        dependencies['azure'] = True
    except ImportError:
        dependencies['azure'] = False
    
    # OCR dependencies
    try:
        import pytesseract
        dependencies['tesseract'] = True
    except ImportError:
        dependencies['tesseract'] = False
    
    try:
        import easyocr
        dependencies['easyocr'] = True
    except ImportError:
        dependencies['easyocr'] = False
    
    return dependencies


def get_system_info() -> Dict[str, Any]:
    """Get system information for debugging."""
    
    import platform
    import psutil
    
    info = {
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor()
        },
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation()
        },
        "memory": {
            "total_gb": round(psutil.virtual_memory().total / 1024**3, 2),
            "available_gb": round(psutil.virtual_memory().available / 1024**3, 2),
            "percent_used": psutil.virtual_memory().percent
        },
        "cpu": {
            "count": psutil.cpu_count(),
            "frequency_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else None
        }
    }
    
    # GPU information
    try:
        import torch
        if torch.cuda.is_available():
            info["gpu"] = {
                "available": True,
                "count": torch.cuda.device_count(),
                "current_device": torch.cuda.current_device(),
                "device_name": torch.cuda.get_device_name(0),
                "memory_gb": round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2)
            }
        else:
            info["gpu"] = {"available": False}
    except ImportError:
        info["gpu"] = {"available": False, "error": "PyTorch not installed"}
    
    return info


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


def estimate_processing_time(pdf_path: Path, config) -> Dict[str, float]:
    """Estimate processing time based on PDF size and configuration."""
    
    try:
        # Get PDF info
        file_size = pdf_path.stat().st_size
        
        # Rough estimates based on method (seconds per page)
        time_per_page = {
            "vlm": 10.0,      # VLM models are slower
            "azure": 3.0,     # Azure is fast
            "traditional": 1.0, # Traditional is fastest
            "hybrid": 6.0     # Hybrid is middle ground
        }
        
        # Estimate page count based on file size (rough approximation)
        estimated_pages = max(1, file_size // (100 * 1024))  # ~100KB per page
        
        # Apply page restriction if specified
        if config.pages:
            estimated_pages = min(estimated_pages, len(config.pages))
        
        base_time = time_per_page.get(config.extraction_method.value, 5.0)
        
        return {
            "estimated_pages": estimated_pages,
            "time_per_page": base_time,
            "total_time_seconds": estimated_pages * base_time,
            "total_time_minutes": (estimated_pages * base_time) / 60
        }
        
    except Exception:
        return {
            "estimated_pages": 1,
            "time_per_page": 5.0,
            "total_time_seconds": 5.0,
            "total_time_minutes": 0.1
        }


class ProgressTracker:
    """Simple progress tracking utility."""
    
    def __init__(self, total_steps: int, description: str = "Processing"):
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.logger = logging.getLogger(__name__)
    
    def update(self, step: int = None, message: str = None):
        """Update progress."""
        if step is not None:
            self.current_step = step
        else:
            self.current_step += 1
        
        percentage = (self.current_step / self.total_steps) * 100
        
        log_message = f"{self.description}: {self.current_step}/{self.total_steps} ({percentage:.1f}%)"
        if message:
            log_message += f" - {message}"
        
        self.logger.info(log_message)
    
    def complete(self, message: str = "Completed"):
        """Mark as complete."""
        self.current_step = self.total_steps
        self.logger.info(f"{self.description}: {message}")


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry function on failure."""
    
    def decorator(func):
        import time
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:  # Don't sleep on last attempt
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                    continue
            
            # If we get here, all retries failed
            raise last_exception
        
        return wrapper
    return decorator