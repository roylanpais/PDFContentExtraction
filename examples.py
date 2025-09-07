"""
Example usage of the PDF Visual Content Extractor.

This script demonstrates various ways to use the extraction pipeline.
"""

from pathlib import Path
from pdf_extractor import (
    PDFExtractor, 
    ExtractionConfig, 
    ExtractionMethod, 
    TargetType,
    extract_figure,
    extract_algorithm,
    extract_all_figures
)


def example_figure_extraction():
    """Example: Extract a specific figure from PDF."""
    print("🖼️ Extracting specific figure...")
    
    # Quick extraction using convenience function
    results = extract_figure(
        pdf_path="example.pdf",
        figure_id="Figure 1",
        method="hybrid",
        output_dir="./examples/figure_output"
    )
    
    for result in results:
        print(f"  ✅ Extracted: {result.element_id}")
        print(f"     Page: {result.page_number}")
        print(f"     Confidence: {result.confidence:.2f}")
        if result.caption:
            print(f"     Caption: {result.caption[:100]}...")


def example_algorithm_extraction():
    """Example: Extract algorithms from specific pages."""
    print("\n🤖 Extracting algorithms...")
    
    results = extract_algorithm(
        pdf_path="example.pdf",
        pages=[3, 4, 5],  # Search pages 3-5
        method="vlm",
        output_dir="./examples/algorithm_output"
    )
    
    for result in results:
        print(f"  ✅ Found algorithm: {result.element_id}")
        print(f"     Page: {result.page_number}")


def example_batch_processing():
    """Example: Process multiple PDFs in batch."""
    print("\n📦 Batch processing multiple PDFs...")
    
    config = ExtractionConfig(
        target_type=TargetType.FIGURE,
        extraction_method=ExtractionMethod.HYBRID,
        output_dir="./examples/batch_output",
        confidence_threshold=0.8,
        parallel_processing=True
    )
    
    extractor = PDFExtractor(config)
    
    # Process all PDFs in directory
    pdf_files = list(Path("./examples/pdfs/").glob("*.pdf"))
    
    if pdf_files:
        batch_results = extractor.extract_batch(pdf_files, config)
        
        total_extracted = sum(len(results) for results in batch_results.values())
        print(f"  ✅ Processed {len(pdf_files)} files")
        print(f"  ✅ Extracted {total_extracted} total elements")
    else:
        print("  ⚠️ No PDF files found in ./examples/pdfs/")


def example_custom_vlm():
    """Example: Using specific VLM model with custom configuration."""
    print("\n🧠 Using custom VLM configuration...")
    
    config = ExtractionConfig(
        target_type=TargetType.TABLE,
        extraction_method=ExtractionMethod.VLM,
        vlm_model="gpt-4-vision",
        vlm_temperature=0.1,
        vlm_max_tokens=1000,
        confidence_threshold=0.75,
        include_captions=True,
        output_dir="./examples/vlm_output"
    )
    
    extractor = PDFExtractor(config)
    
    try:
        results = extractor.extract("example.pdf", config)
        
        for result in results:
            print(f"  ✅ Table found: {result.element_id}")
            print(f"     VLM Model: {result.metadata.get('vlm_model')}")
            print(f"     Confidence: {result.confidence:.2f}")
    
    except Exception as e:
        print(f"  ❌ VLM extraction failed: {e}")
        print("  💡 Make sure OPENAI_API_KEY is set in your environment")


def example_azure_extraction():
    """Example: Using Azure Document Intelligence."""
    print("\n☁️ Using Azure Document Intelligence...")
    
    config = ExtractionConfig(
        target_type=TargetType.FIGURE,
        extraction_method=ExtractionMethod.AZURE,
        azure_model="prebuilt-layout",
        azure_features=["layout", "figures"],
        output_dir="./examples/azure_output"
    )
    
    extractor = PDFExtractor(config)
    
    try:
        results = extractor.extract("example.pdf", config)
        
        for result in results:
            print(f"  ✅ Found: {result.element_id}")
            print(f"     Azure Model: {result.metadata.get('azure_model')}")
    
    except Exception as e:
        print(f"  ❌ Azure extraction failed: {e}")
        print("  💡 Make sure Azure credentials are configured")


def example_custom_patterns():
    """Example: Using custom extraction patterns."""
    print("\n🔍 Using custom extraction patterns...")
    
    config = ExtractionConfig(
        target_type=TargetType.CUSTOM,
        extraction_method=ExtractionMethod.HYBRID,
        custom_patterns=[
            r"Algorithm \d+:",
            r"Procedure \w+",
            r"Method \d+\.\d+",
            r"Step \d+:"
        ],
        confidence_threshold=0.6,
        output_dir="./examples/custom_output"
    )
    
    extractor = PDFExtractor(config)
    
    try:
        results = extractor.extract("example.pdf", config)
        
        for result in results:
            print(f"  ✅ Custom match: {result.element_id}")
            print(f"     Pattern matched: {result.caption[:50]}...")
    
    except Exception as e:
        print(f"  ❌ Custom pattern extraction failed: {e}")


def example_advanced_configuration():
    """Example: Advanced configuration with all options."""
    print("\n⚙️ Advanced configuration example...")
    
    config = ExtractionConfig(
        # Target configuration
        target_type=TargetType.FIGURE,
        target_identifier="Figure 1",
        
        # Method configuration
        extraction_method=ExtractionMethod.HYBRID,
        vlm_model="gpt-4-vision",
        
        # Processing configuration
        pages=[1, 2, 3],  # Only process first 3 pages
        confidence_threshold=0.8,
        max_retries=2,
        parallel_processing=False,
        gpu_enabled=True,
        
        # Output configuration
        output_dir="./examples/advanced_output",
        output_format="png",
        include_captions=True,
        include_metadata=True,
        save_intermediate=True,
        
        # Azure configuration (if using Azure method)
        azure_model="prebuilt-layout",
        azure_features=["layout", "figures", "tables"],
        
        # Custom patterns
        custom_patterns=[r"Fig\.?\s*\d+", r"Figure\s+\d+"]
    )
    
    print(f"  📋 Configuration:")
    print(f"     Target: {config.target_type.value}")
    print(f"     Method: {config.extraction_method.value}")
    print(f"     Confidence: {config.confidence_threshold}")
    print(f"     Pages: {config.pages}")


def main():
    """Run all examples."""
    print("🚀 PDF Visual Content Extractor - Examples\n")
    
    # Create example directories
    for dir_name in ["figure_output", "algorithm_output", "batch_output", 
                     "vlm_output", "azure_output", "custom_output", "advanced_output"]:
        Path(f"./examples/{dir_name}").mkdir(parents=True, exist_ok=True)
    
    # Note about example PDF
    example_pdf = Path("example.pdf")
    if not example_pdf.exists():
        print("⚠️  Note: 'example.pdf' not found. Using the provided assignment PDF for examples.")
        print("   You can replace this with any PDF file for testing.\n")
        
        # For the assignment, we'll use the provided PDF
        example_pdf = Path("Assignment-PDF.pdf")
        if not example_pdf.exists():
            print("❌ Assignment-PDF.pdf not found. Please ensure the file is in the current directory.")
            return
    
    try:
        # Run examples
        example_figure_extraction()
        example_algorithm_extraction()
        example_batch_processing()
        example_custom_vlm()
        example_azure_extraction()
        example_custom_patterns()
        example_advanced_configuration()
        
        print("\n🎉 All examples completed!")
        print("📁 Check the ./examples/ directory for extracted content")
        
    except Exception as e:
        print(f"\n❌ Example execution failed: {e}")
        print("💡 Make sure to install dependencies and configure API keys")


if __name__ == "__main__":
    main()