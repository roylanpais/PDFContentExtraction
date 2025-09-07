
"""
Test Suite for PDF Content Extraction Pipeline
==============================================
"""

import unittest
import json
import os
from pathlib import Path
from simple_extractor import SimplePDFExtractor

class TestPDFExtraction(unittest.TestCase):
    """Test cases for PDF content extraction functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_pdf = "Assignment-PDF.pdf"
        self.test_output = "test_output"
        self.extractor = SimplePDFExtractor(self.test_pdf, self.test_output)

    def test_figure_1_extraction(self):
        """Test Figure 1 extraction functionality."""
        print("\nTesting Figure 1 extraction...")

        result = self.extractor.extract_figure_1()

        # Verify extraction success
        self.assertTrue(result["extracted"], "Figure 1 should be successfully extracted")
        self.assertEqual(result["figure_number"], "1", "Should extract Figure 1")

        # Verify metadata exists
        metadata_file = Path(self.test_output) / "figures" / "figure_1_metadata.json"
        self.assertTrue(metadata_file.exists(), "Figure 1 metadata should be saved")

        print("✓ Figure 1 extraction test passed")

    def test_ada_algorithm_extraction(self):
        """Test ADA algorithm extraction functionality."""
        print("\nTesting ADA algorithm extraction...")

        result = self.extractor.extract_ada_algorithm()

        # Verify extraction success
        self.assertTrue(result["extracted"], "ADA algorithm should be successfully extracted")
        self.assertEqual(result["page"], 11, "Should extract from page 11")
        self.assertIn("ADA", result["algorithm_name"], "Should identify ADA algorithm")

        # Verify algorithm structure
        self.assertIn("inputs", result, "Should identify algorithm inputs")
        self.assertIn("outputs", result, "Should identify algorithm outputs")
        self.assertIn("algorithm_steps", result, "Should extract algorithm steps")

        # Verify file creation
        algo_file = Path(self.test_output) / "algorithms" / "ada_algorithm_details.json"
        self.assertTrue(algo_file.exists(), "Algorithm details should be saved")

        print("✓ ADA algorithm extraction test passed")

    def test_metadata_generation(self):
        """Test metadata generation functionality."""
        print("\nTesting metadata generation...")

        metadata = self.extractor.generate_metadata()

        # Verify metadata structure
        self.assertIn("pdf_analyzed", metadata, "Should record PDF path")
        self.assertIn("target_extractions", metadata, "Should document extraction targets")
        self.assertIn("methodology", metadata, "Should describe methodology")

        # Verify file creation
        metadata_file = Path(self.test_output) / "metadata" / "extraction_metadata.json"
        self.assertTrue(metadata_file.exists(), "Metadata should be saved")

        print("✓ Metadata generation test passed")

    def test_full_pipeline(self):
        """Test the complete extraction pipeline."""
        print("\nTesting full extraction pipeline...")

        results = self.extractor.run_extraction()

        # Verify overall success
        self.assertTrue(results["extraction_success"], "Pipeline should complete successfully")
        self.assertTrue(results["figure_1_extracted"], "Figure 1 should be extracted")
        self.assertTrue(results["ada_algorithm_extracted"], "ADA algorithm should be extracted")

        # Verify all output files exist
        for file_path in results["files_created"]:
            self.assertTrue(Path(file_path).exists(), f"Output file should exist: {file_path}")

        print("✓ Full pipeline test passed")

    def test_output_structure(self):
        """Test that output directory structure is correct."""
        print("\nTesting output directory structure...")

        # Run extraction
        self.extractor.run_extraction()

        # Verify directory structure
        base_dir = Path(self.test_output)
        self.assertTrue(base_dir.exists(), "Base output directory should exist")

        expected_dirs = ["figures", "algorithms", "metadata"]
        for dir_name in expected_dirs:
            dir_path = base_dir / dir_name
            self.assertTrue(dir_path.exists(), f"Subdirectory should exist: {dir_name}")

        print("✓ Output structure test passed")

    def tearDown(self):
        """Clean up test environment."""
        # Note: In a real implementation, you might want to clean up test files
        # For this demo, we'll leave them to show the results
        pass

def run_tests():
    """Run all tests and display results."""
    print("="*60)
    print("PDF CONTENT EXTRACTION PIPELINE - TEST SUITE")
    print("="*60)

    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPDFExtraction)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Display summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n🎉 ALL TESTS PASSED! Pipeline is working correctly.")
    else:
        print("\n❌ Some tests failed. Check the output above for details.")

    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
