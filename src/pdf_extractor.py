
"""
PDF Figure and Algorithm Extraction Pipeline
============================================

This module provides functionality to extract specific figures and algorithms
from PDF documents using a combination of computer vision and NLP techniques.

Author: AI Research Assistant
Date: September 2025
"""

import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image
import re
import json
import os
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFContentExtractor:
    """
    A comprehensive PDF content extraction pipeline that identifies and extracts
    figures, algorithms, and associated metadata from scientific documents.
    """

    def __init__(self, pdf_path: str, output_dir: str = "extracted_content"):
        """
        Initialize the PDF content extractor.

        Args:
            pdf_path (str): Path to the input PDF file
            output_dir (str): Directory to save extracted content
        """
        self.pdf_path = pdf_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Create subdirectories
        self.figures_dir = self.output_dir / "figures"
        self.algorithms_dir = self.output_dir / "algorithms"
        self.metadata_dir = self.output_dir / "metadata"

        for dir_path in [self.figures_dir, self.algorithms_dir, self.metadata_dir]:
            dir_path.mkdir(exist_ok=True)

        self.doc = None
        self.extracted_content = {
            "figures": [],
            "algorithms": [],
            "metadata": {}
        }

    def load_pdf(self):
        """Load the PDF document."""
        try:
            self.doc = fitz.open(self.pdf_path)
            logger.info(f"Successfully loaded PDF: {self.pdf_path}")
            logger.info(f"Document has {len(self.doc)} pages")
        except Exception as e:
            logger.error(f"Error loading PDF: {e}")
            raise

    def extract_text_with_positions(self, page_num: int) -> List[Dict]:
        """
        Extract text with position information from a specific page.

        Args:
            page_num (int): Page number (0-indexed)

        Returns:
            List[Dict]: Text blocks with position and content information
        """
        if self.doc is None:
            raise ValueError("PDF not loaded. Call load_pdf() first.")

        page = self.doc[page_num]
        text_dict = page.get_text("dict")

        text_blocks = []
        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text_blocks.append({
                            "text": span["text"],
                            "bbox": span["bbox"],  # (x0, y0, x1, y1)
                            "font": span["font"],
                            "size": span["size"],
                            "flags": span["flags"]
                        })

        return text_blocks

    def find_figure_references(self, page_num: int) -> List[Dict]:
        """
        Find figure references (e.g., "Figure 1", "Fig. 2") on a page.

        Args:
            page_num (int): Page number to search

        Returns:
            List[Dict]: Figure references with positions
        """
        text_blocks = self.extract_text_with_positions(page_num)
        figure_refs = []

        # Pattern to match figure references
        fig_patterns = [
            r"Figure\s+(\d+)",
            r"Fig\.\s*(\d+)",
            r"FIGURE\s+(\d+)"
        ]

        for block in text_blocks:
            text = block["text"]
            for pattern in fig_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    figure_refs.append({
                        "figure_number": match.group(1),
                        "full_text": match.group(0),
                        "bbox": block["bbox"],
                        "page": page_num
                    })

        return figure_refs

    def find_algorithm_blocks(self, page_num: int) -> List[Dict]:
        """
        Find algorithm blocks on a page using text patterns and formatting.

        Args:
            page_num (int): Page number to search

        Returns:
            List[Dict]: Algorithm blocks with positions
        """
        text_blocks = self.extract_text_with_positions(page_num)
        algorithm_blocks = []

        # Patterns that indicate algorithm content
        algorithm_patterns = [
            r"Algorithm\s+(\d+)",
            r"ALGORITHM\s+(\d+)",
            r"Function\s+\w+",
            r"Input:",
            r"Output:",
            r"return\s+",
            r"foreach\s+",
            r"if\s+.*then",
            r"else\s+if"
        ]

        for block in text_blocks:
            text = block["text"]
            for pattern in algorithm_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    algorithm_blocks.append({
                        "text": text,
                        "bbox": block["bbox"],
                        "page": page_num,
                        "pattern_matched": pattern
                    })
                    break

        return algorithm_blocks

    def extract_images_from_page(self, page_num: int) -> List[Dict]:
        """
        Extract all images from a specific page.

        Args:
            page_num (int): Page number to extract images from

        Returns:
            List[Dict]: Image information and data
        """
        if self.doc is None:
            raise ValueError("PDF not loaded. Call load_pdf() first.")

        page = self.doc[page_num]
        image_list = page.get_images()
        extracted_images = []

        for img_index, img in enumerate(image_list):
            try:
                # Get image data
                xref = img[0]
                pix = fitz.Pixmap(self.doc, xref)

                if pix.n - pix.alpha < 4:  # GRAY or RGB
                    img_data = pix.tobytes("png")
                    img_path = self.figures_dir / f"page_{page_num}_img_{img_index}.png"

                    with open(img_path, "wb") as f:
                        f.write(img_data)

                    extracted_images.append({
                        "page": page_num,
                        "index": img_index,
                        "path": str(img_path),
                        "width": pix.width,
                        "height": pix.height,
                        "xref": xref
                    })

                pix = None  # Clean up

            except Exception as e:
                logger.warning(f"Could not extract image {img_index} from page {page_num}: {e}")

        return extracted_images

    def extract_figure_1(self) -> Optional[Dict]:
        """
        Specifically extract Figure 1 from the document.

        Returns:
            Optional[Dict]: Figure 1 information and path, or None if not found
        """
        logger.info("Searching for Figure 1...")

        for page_num in range(len(self.doc)):
            # Find figure references on this page
            figure_refs = self.find_figure_references(page_num)

            for ref in figure_refs:
                if ref["figure_number"] == "1":
                    logger.info(f"Found Figure 1 reference on page {page_num + 1}")

                    # Extract images from this page
                    images = self.extract_images_from_page(page_num)

                    if images:
                        # Assume the first image on the page with Figure 1 reference is Figure 1
                        fig1_image = images[0]

                        # Rename the file to be more descriptive
                        new_path = self.figures_dir / "figure_1.png"
                        os.rename(fig1_image["path"], new_path)
                        fig1_image["path"] = str(new_path)

                        # Extract caption
                        caption = self.extract_figure_caption(page_num, ref["bbox"])

                        result = {
                            "figure_number": "1",
                            "page": page_num + 1,
                            "image_path": str(new_path),
                            "caption": caption,
                            "reference_bbox": ref["bbox"]
                        }

                        self.extracted_content["figures"].append(result)
                        return result

        logger.warning("Figure 1 not found in the document")
        return None

    def extract_figure_caption(self, page_num: int, figure_bbox: Tuple[float, float, float, float]) -> str:
        """
        Extract the caption text near a figure.

        Args:
            page_num (int): Page number
            figure_bbox (Tuple): Bounding box of the figure reference

        Returns:
            str: Extracted caption text
        """
        text_blocks = self.extract_text_with_positions(page_num)

        # Look for text blocks near the figure reference
        caption_texts = []
        fig_x, fig_y = figure_bbox[0], figure_bbox[1]

        for block in text_blocks:
            block_x, block_y = block["bbox"][0], block["bbox"][1]

            # Check if text block is reasonably close to figure reference
            distance = ((block_x - fig_x) ** 2 + (block_y - fig_y) ** 2) ** 0.5

            if distance < 200:  # Adjust threshold as needed
                text = block["text"].strip()
                if text and len(text) > 10:  # Filter out short text
                    caption_texts.append(text)

        return " ".join(caption_texts[:3])  # Take first few relevant text blocks

    def extract_ada_algorithm(self) -> Optional[Dict]:
        """
        Extract the ADA algorithm from page 11.

        Returns:
            Optional[Dict]: ADA algorithm information, or None if not found
        """
        logger.info("Searching for ADA algorithm on page 11...")

        # Page 11 (0-indexed: page 10)
        target_page = 10

        if len(self.doc) <= target_page:
            logger.warning(f"Document doesn't have page {target_page + 1}")
            return None

        # Extract all text from page 11
        page = self.doc[target_page]
        page_text = page.get_text()

        # Look for algorithm patterns
        algorithm_blocks = self.find_algorithm_blocks(target_page)

        if algorithm_blocks:
            # Extract the page as an image for visual algorithm representation
            mat = fitz.Matrix(2, 2)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=mat)
            img_path = self.algorithms_dir / "ada_algorithm_page11.png"
            pix.save(str(img_path))

            # Extract algorithm text
            algorithm_text = self.extract_algorithm_text(page_text)

            result = {
                "algorithm_name": "ADA (Adaptive Keyframe Sampling)",
                "page": target_page + 1,
                "image_path": str(img_path),
                "algorithm_text": algorithm_text,
                "blocks": algorithm_blocks
            }

            self.extracted_content["algorithms"].append(result)
            return result

        logger.warning("ADA algorithm not found on page 11")
        return None

    def extract_algorithm_text(self, page_text: str) -> str:
        """
        Extract structured algorithm text from page content.

        Args:
            page_text (str): Full page text content

        Returns:
            str: Cleaned algorithm text
        """
        lines = page_text.split("\n")
        algorithm_lines = []

        in_algorithm = False

        for line in lines:
            line = line.strip()

            # Start of algorithm
            if re.search(r"Algorithm\s+\d+", line, re.IGNORECASE):
                in_algorithm = True
                algorithm_lines.append(line)
                continue

            if in_algorithm:
                # Algorithm content patterns
                if any(pattern in line.lower() for pattern in [
                    "function", "input:", "output:", "return", "if", "else", 
                    "for", "while", "foreach", "append", "split"
                ]):
                    algorithm_lines.append(line)
                elif line == "" or len(line) < 3:
                    # End of algorithm (empty line or very short line)
                    break
                else:
                    algorithm_lines.append(line)

        return "\n".join(algorithm_lines)

    def generate_metadata(self):
        """Generate metadata about the extraction process."""
        metadata = {
            "pdf_path": self.pdf_path,
            "total_pages": len(self.doc) if self.doc else 0,
            "extraction_timestamp": str(Path().resolve()),
            "figures_extracted": len(self.extracted_content["figures"]),
            "algorithms_extracted": len(self.extracted_content["algorithms"])
        }

        # Save metadata
        metadata_path = self.metadata_dir / "extraction_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        self.extracted_content["metadata"] = metadata

    def run_extraction(self) -> Dict:
        """
        Run the complete extraction pipeline.

        Returns:
            Dict: Summary of extracted content
        """
        logger.info("Starting PDF content extraction pipeline...")

        # Load PDF
        self.load_pdf()

        # Extract Figure 1
        figure_1 = self.extract_figure_1()

        # Extract ADA algorithm
        ada_algorithm = self.extract_ada_algorithm()

        # Generate metadata
        self.generate_metadata()

        # Create summary
        summary = {
            "success": True,
            "figure_1_extracted": figure_1 is not None,
            "ada_algorithm_extracted": ada_algorithm is not None,
            "output_directory": str(self.output_dir),
            "extracted_content": self.extracted_content
        }

        # Save summary
        summary_path = self.output_dir / "extraction_summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info("Extraction pipeline completed successfully!")
        return summary

    def __del__(self):
        """Clean up resources."""
        if self.doc:
            self.doc.close()


def main():
    """Main execution function."""
    # Configuration
    pdf_path = "Assignment-PDF.pdf"  # Update with actual path
    output_dir = "extracted_content"

    # Initialize extractor
    extractor = PDFContentExtractor(pdf_path, output_dir)

    try:
        # Run extraction
        results = extractor.run_extraction()

        print("\n" + "="*60)
        print("PDF CONTENT EXTRACTION RESULTS")
        print("="*60)
        print(f"Figure 1 extracted: {results['figure_1_extracted']}")
        print(f"ADA Algorithm extracted: {results['ada_algorithm_extracted']}")
        print(f"Output directory: {results['output_directory']}")
        print("="*60)

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise


if __name__ == "__main__":
    main()
