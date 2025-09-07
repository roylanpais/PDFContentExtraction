# Let's create a requirements.txt file for the dependencies
requirements = """
# PDF Content Extraction Pipeline Requirements
# ============================================

# Core PDF processing
PyMuPDF==1.23.8
fitz

# Computer Vision and Image Processing
opencv-python==4.8.1.78
Pillow==10.0.1
numpy==1.24.3

# Text Processing and NLP
regex==2023.8.8

# Utilities
pathlib2==2.3.7
typing-extensions==4.7.1

# Optional: For advanced layout analysis
# layoutparser==0.3.4
# detectron2  # Requires special installation

# Optional: For OCR capabilities
# pytesseract==0.3.10
# easyocr==1.7.0

# Development and Testing
pytest==7.4.2
"""

with open("requirements.txt", "w") as f:
    f.write(requirements)

print("Created requirements.txt file")