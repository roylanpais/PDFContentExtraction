# Create a comprehensive README.md file
readme_content = """
# PDF Content Extraction Pipeline

A robust pipeline for automatically extracting figures, algorithms, and metadata from scientific PDF documents.

## 🎯 Overview

This project implements an intelligent PDF content extraction system that can:
- Identify and extract specific figures (e.g., "Figure 1") with their captions
- Extract algorithm blocks with proper formatting
- Generate structured metadata about the extraction process
- Handle various PDF layouts and formats

## 🚀 Features

### Core Capabilities
- **Figure Extraction**: Automatically locate and extract labeled figures
- **Algorithm Detection**: Identify and extract algorithm blocks using text patterns
- **Caption Recognition**: Extract figure captions and metadata
- **Multi-format Output**: Save extracted content in various formats
- **Robust Processing**: Handle different PDF layouts and structures

### Technical Highlights
- **Computer Vision**: Image processing for figure extraction
- **NLP Patterns**: Regular expressions for content identification  
- **Layout Analysis**: Spatial text analysis for content association
- **Modular Design**: Clean, extensible architecture

## 📋 Requirements

### System Requirements
- Python 3.8+
- 2GB+ RAM (for processing large PDFs)
- 500MB+ disk space

### Dependencies
```bash
pip install -r requirements.txt
```

Key libraries:
- PyMuPDF (fitz): PDF processing
- OpenCV: Computer vision operations
- Pillow: Image manipulation
- NumPy: Numerical computations

## 🔧 Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd pdf-content-extractor
```

2. **Create virtual environment** (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Verify installation**:
```bash
python pdf_extractor.py --help
```

## 📖 Usage

### Basic Usage

```python
from pdf_extractor import PDFContentExtractor

# Initialize extractor
extractor = PDFContentExtractor(
    pdf_path="your_document.pdf",
    output_dir="extracted_content"
)

# Run extraction
results = extractor.run_extraction()

# Check results
print(f"Figure 1 extracted: {results['figure_1_extracted']}")
print(f"Algorithm extracted: {results['ada_algorithm_extracted']}")
```

### Command Line Usage

```bash
# Extract content from PDF
python pdf_extractor.py

# Specify custom paths
python pdf_extractor.py --pdf path/to/document.pdf --output custom_output/
```

### Advanced Usage

```python
# Custom extraction with specific parameters
extractor = PDFContentExtractor("document.pdf")

# Extract only Figure 1
figure_1 = extractor.extract_figure_1()

# Extract only algorithms from specific page
algorithm = extractor.extract_ada_algorithm()

# Get detailed metadata
extractor.generate_metadata()
```

## 📁 Output Structure

```
extracted_content/
├── figures/
│   ├── figure_1.png          # Extracted Figure 1
│   └── page_X_img_Y.png      # Other images
├── algorithms/
│   └── ada_algorithm_page11.png  # ADA algorithm visualization
├── metadata/
│   └── extraction_metadata.json  # Process metadata
└── extraction_summary.json   # Overall results summary
```

## 🔍 Algorithm Details

### Figure Detection Process
1. **Text Analysis**: Scan for figure references using regex patterns
2. **Spatial Mapping**: Associate references with nearby images
3. **Image Extraction**: Extract high-quality image data
4. **Caption Recognition**: Identify and extract figure captions

### Algorithm Extraction Process
1. **Pattern Matching**: Identify algorithm keywords and structures
2. **Block Detection**: Group related algorithm lines
3. **Visual Capture**: Generate high-resolution page images
4. **Text Extraction**: Extract formatted algorithm text

### Robust Design Features
- **Multi-pattern Recognition**: Multiple regex patterns for flexibility
- **Error Handling**: Graceful failure and logging
- **Format Support**: Various PDF structures and layouts
- **Quality Control**: Image quality validation and enhancement

## 🔧 Configuration

### Extraction Parameters

```python
# Customize figure detection patterns
figure_patterns = [
    r"Figure\\s+(\\d+)",
    r"Fig\\.\\s*(\\d+)", 
    r"FIGURE\\s+(\\d+)"
]

# Algorithm detection keywords
algorithm_keywords = [
    "Algorithm", "Function", "Input:", "Output:", 
    "return", "foreach", "if.*then"
]
```

### Output Settings

```python
# Configure output formats and paths
extractor.configure({
    "image_format": "png",
    "image_quality": 300,  # DPI
    "text_encoding": "utf-8",
    "metadata_format": "json"
})
```

## 🧪 Testing

Run the test suite:
```bash
python -m pytest tests/
```

Test specific components:
```bash
python -m pytest tests/test_figure_extraction.py
python -m pytest tests/test_algorithm_detection.py
```

## 🐛 Troubleshooting

### Common Issues

1. **PDF not loading**:
   - Check file path and permissions
   - Verify PDF is not corrupted or password-protected

2. **No figures extracted**:
   - Check if figures are properly labeled in the document
   - Adjust detection patterns for document-specific formatting

3. **Poor image quality**:
   - Increase extraction resolution in configuration
   - Check original PDF quality

4. **Memory issues with large PDFs**:
   - Process pages individually
   - Reduce image extraction quality temporarily

### Debug Mode

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🚀 Extensions and Improvements

### Potential Enhancements
1. **ML-based Layout Detection**: Use deep learning models for better layout understanding
2. **OCR Integration**: Add text recognition for scanned documents
3. **Multi-language Support**: Extend pattern matching for various languages
4. **Batch Processing**: Handle multiple PDFs simultaneously
5. **API Interface**: RESTful API for web integration

### Advanced Features (Future)
- **Semantic Analysis**: Understanding figure-text relationships
- **Table Extraction**: Automated table detection and extraction
- **Reference Resolution**: Link figures to their references in text
- **Quality Assessment**: Automatic quality scoring for extracted content

## 🤝 Contributing

We welcome contributions! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

### Development Setup
```bash
pip install -e .[dev]
pre-commit install
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- PyMuPDF team for excellent PDF processing capabilities
- OpenCV community for computer vision tools
- Scientific community for standardized document formats

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check the documentation
- Contact the maintainers

---

**Note**: This pipeline is designed for scientific documents with standard formatting. Performance may vary with non-standard layouts or heavily customized document formats.
"""

with open("README.md", "w") as f:
    f.write(readme_content)

print("Created comprehensive README.md file")