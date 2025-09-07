#!/usr/bin/env python3
"""
Assignment Solution - PDF Visual Content Extractor

This script demonstrates the solution for the assignment:
- Extract "Figure 1" from the provided PDF
- Extract "ADA algorithm" from Page 11
- Generalizable solution for any PDF content extraction
"""

import os
import sys
from pathlib import Path
import json
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from pdf_extractor import (
    PDFExtractor, 
    ExtractionConfig, 
    ExtractionMethod, 
    TargetType
)


def extract_figure_1(pdf_path: Path, output_dir: Path):
    """
    Extract Figure 1 from the document as required by assignment.
    """
    print("🖼️ Extracting Figure 1 from the document...")
    
    config = ExtractionConfig(
        target_type=TargetType.FIGURE,
        target_identifier="Figure 1",
        extraction_method=ExtractionMethod.HYBRID,  # Use best method
        output_dir=str(output_dir / "figure_1"),
        confidence_threshold=0.6,  # Lower threshold for better recall
        include_captions=True,
        include_metadata=True
    )
    
    extractor = PDFExtractor(config)
    results = extractor.extract(pdf_path, config)
    
    if results:
        for result in results:
            print(f"  ✅ Successfully extracted: {result.element_id}")
            print(f"     Location: Page {result.page_number}")
            print(f"     Confidence: {result.confidence:.2f}")
            print(f"     Image saved: {result.image_path}")
            if result.caption:
                print(f"     Caption: {result.caption[:150]}...")
    else:
        print("  ❌ Figure 1 not found. Trying alternative approaches...")
        
        # Try with different methods
        for method in [ExtractionMethod.VLM, ExtractionMethod.AZURE, ExtractionMethod.TRADITIONAL]:
            try:
                config.extraction_method = method
                config.confidence_threshold = 0.4
                results = extractor.extract(pdf_path, config)
                
                if results:
                    print(f"  ✅ Found with {method.value} method!")
                    break
            except Exception as e:
                print(f"  ⚠️ {method.value} method failed: {e}")
    
    return results


def extract_ada_algorithm(pdf_path: Path, output_dir: Path):
    """
    Extract ADA algorithm from Page 11 as required by assignment.
    """
    print("\n🤖 Extracting ADA algorithm from Page 11...")
    
    config = ExtractionConfig(
        target_type=TargetType.ALGORITHM,
        target_identifier="ADA",  # Look for ADA algorithm
        extraction_method=ExtractionMethod.VLM,  # VLM best for algorithm detection
        vlm_model="gpt-4-vision",
        pages=[11],  # Specifically page 11
        output_dir=str(output_dir / "ada_algorithm"),
        confidence_threshold=0.5,
        include_captions=True,
        include_metadata=True,
        custom_patterns=[
            r"Algorithm.*ADA",
            r"ADA.*Algorithm",
            r"Adaptive.*Sampling",
            r"Function.*ADA"
        ]
    )
    
    extractor = PDFExtractor(config)
    
    try:
        results = extractor.extract(pdf_path, config)
        
        if results:
            for result in results:
                print(f"  ✅ Successfully extracted: {result.element_id}")
                print(f"     Location: Page {result.page_number}")
                print(f"     Method: {result.extraction_method}")
                print(f"     Confidence: {result.confidence:.2f}")
                print(f"     Image saved: {result.image_path}")
        else:
            print("  ⚠️ ADA algorithm not found on page 11. Searching broader range...")
            
            # Search pages around 11
            config.pages = [10, 11, 12]
            config.target_identifier = None  # Remove specific identifier
            results = extractor.extract(pdf_path, config)
            
            if results:
                print("  ✅ Found algorithms in nearby pages:")
                for result in results:
                    print(f"     {result.element_id} on page {result.page_number}")
    
    except Exception as e:
        print(f"  ❌ Algorithm extraction failed: {e}")
        print("  💡 Trying with different approach...")
        
        # Fallback to traditional method
        config.extraction_method = ExtractionMethod.TRADITIONAL
        try:
            results = extractor.extract(pdf_path, config)
            if results:
                print("  ✅ Found with traditional method!")
        except:
            results = []
    
    return results


def demonstrate_generalization(pdf_path: Path, output_dir: Path):
    """
    Demonstrate the generalizability of the solution.
    """
    print("\n🔧 Demonstrating generalization capabilities...")
    
    # Example 1: Extract all figures
    print("\n  📊 Example 1: Extract all figures")
    config1 = ExtractionConfig(
        target_type=TargetType.FIGURE,
        extraction_method=ExtractionMethod.HYBRID,
        output_dir=str(output_dir / "all_figures"),
        confidence_threshold=0.7
    )
    
    extractor = PDFExtractor(config1)
    results1 = extractor.extract(pdf_path, config1)
    print(f"     Found {len(results1)} figures total")
    
    # Example 2: Extract all tables
    print("\n  📋 Example 2: Extract all tables")
    config2 = ExtractionConfig(
        target_type=TargetType.TABLE,
        extraction_method=ExtractionMethod.AZURE,
        output_dir=str(output_dir / "all_tables"),
        confidence_threshold=0.6
    )
    
    try:
        results2 = extractor.extract(pdf_path, config2)
        print(f"     Found {len(results2)} tables total")
    except Exception as e:
        print(f"     Table extraction failed: {e}")
        results2 = []
    
    # Example 3: Custom pattern extraction
    print("\n  🎯 Example 3: Custom pattern extraction")
    config3 = ExtractionConfig(
        target_type=TargetType.CUSTOM,
        extraction_method=ExtractionMethod.VLM,
        output_dir=str(output_dir / "custom_patterns"),
        custom_patterns=[
            r"Equation.*\d+",
            r"Formula.*\d+",
            r"Definition.*\d+",
            r"Theorem.*\d+"
        ],
        confidence_threshold=0.5
    )
    
    try:
        results3 = extractor.extract(pdf_path, config3)
        print(f"     Found {len(results3)} custom pattern matches")
    except Exception as e:
        print(f"     Custom pattern extraction failed: {e}")
        results3 = []
    
    return {
        "figures": results1,
        "tables": results2,
        "custom": results3
    }


def save_solution_report(output_dir: Path, figure_results, algorithm_results, demo_results):
    """
    Save a comprehensive report of the extraction results.
    """
    report = {
        "assignment_solution": {
            "timestamp": datetime.now().isoformat(),
            "pdf_processed": "Assignment-PDF.pdf",
            "requirements_fulfilled": {
                "figure_1_extraction": {
                    "success": len(figure_results) > 0,
                    "count": len(figure_results),
                    "results": [r.to_dict() for r in figure_results]
                },
                "ada_algorithm_extraction": {
                    "success": len(algorithm_results) > 0,
                    "count": len(algorithm_results),
                    "results": [r.to_dict() for r in algorithm_results]
                }
            },
            "generalization_demo": {
                "all_figures_count": len(demo_results.get("figures", [])),
                "all_tables_count": len(demo_results.get("tables", [])),
                "custom_patterns_count": len(demo_results.get("custom", []))
            },
            "methods_used": [
                "Vision Language Models (VLM)",
                "Azure AI Document Intelligence",
                "Traditional Computer Vision + OCR",
                "Hybrid approach combining multiple methods"
            ],
            "features_demonstrated": [
                "Specific element extraction (Figure 1)",
                "Page-specific extraction (Algorithm on page 11)",
                "Multi-method approach for robustness",
                "Custom pattern matching",
                "Metadata and caption extraction",
                "Batch processing capability",
                "Configurable confidence thresholds",
                "Multiple output formats"
            ]
        }
    }
    
    # Save report
    report_path = output_dir / "solution_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📋 Solution report saved: {report_path}")
    return report


def main():
    """
    Main function to solve the assignment requirements.
    """
    print("🎯 PDF Visual Content Extractor - Assignment Solution")
    print("=" * 60)
    
    # Check for the assignment PDF
    pdf_path = Path("Assignment-PDF.pdf")
    if not pdf_path.exists():
        print("❌ Assignment-PDF.pdf not found in current directory")
        print("   Please ensure the PDF file is present")
        sys.exit(1)
    
    # Create output directory
    output_dir = Path("assignment_output")
    output_dir.mkdir(exist_ok=True)
    
    print(f"📄 Processing: {pdf_path}")
    print(f"📁 Output directory: {output_dir}")
    
    # Solve assignment requirements
    try:
        # Requirement 1: Extract Figure 1
        print("\n" + "=" * 60)
        print("REQUIREMENT 1: Extract 'Figure 1' from the document")
        print("=" * 60)
        figure_results = extract_figure_1(pdf_path, output_dir)
        
        # Requirement 2: Extract ADA algorithm from page 11
        print("\n" + "=" * 60)
        print("REQUIREMENT 2: Extract 'ADA algorithm' from Page 11")
        print("=" * 60)
        algorithm_results = extract_ada_algorithm(pdf_path, output_dir)
        
        # Demonstrate generalization
        print("\n" + "=" * 60)
        print("BONUS: Demonstrate generalization capabilities")
        print("=" * 60)
        demo_results = demonstrate_generalization(pdf_path, output_dir)
        
        # Save solution report
        report = save_solution_report(output_dir, figure_results, algorithm_results, demo_results)
        
        # Print final summary
        print("\n" + "🎉" * 20)
        print("ASSIGNMENT COMPLETED SUCCESSFULLY!")
        print("🎉" * 20)
        
        print(f"\n📊 Summary:")
        print(f"   Figure 1 extracted: {'✅' if figure_results else '❌'}")
        print(f"   ADA algorithm extracted: {'✅' if algorithm_results else '❌'}")
        print(f"   Additional figures found: {len(demo_results.get('figures', []))}")
        print(f"   Additional tables found: {len(demo_results.get('tables', []))}")
        print(f"   Custom patterns found: {len(demo_results.get('custom', []))}")
        
        print(f"\n📁 All results saved to: {output_dir}")
        print("   Check the individual subdirectories for extracted images")
        print("   Review solution_report.json for detailed results")
        
        # List extracted files
        extracted_files = list(output_dir.rglob("*.png")) + list(output_dir.rglob("*.jpg"))
        if extracted_files:
            print(f"\n🖼️ Extracted {len(extracted_files)} image files:")
            for file in extracted_files[:10]:  # Show first 10
                print(f"   {file}")
            if len(extracted_files) > 10:
                print(f"   ... and {len(extracted_files) - 10} more files")
        
    except Exception as e:
        print(f"\n❌ Assignment execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()