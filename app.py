"""
PDF Visual Content Extractor - Streamlit Web Interface

A user-friendly web interface for extracting visual content from PDFs.
"""

import streamlit as st
import os
import json
import tempfile
from pathlib import Path
from typing import List, Optional
import pandas as pd
from PIL import Image
import zipfile
import io

from pdf_extractor import (
    PDFExtractor, 
    ExtractionConfig, 
    ExtractionMethod, 
    TargetType
)


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="PDF Visual Content Extractor",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("📄 PDF Visual Content Extractor")
    st.markdown("""
    Extract figures, tables, algorithms, and other visual content from PDF documents
    using advanced AI methods including Vision Language Models and Azure Document Intelligence.
    """)
    
    # Sidebar configuration
    with st.sidebar:
        st.header("🔧 Configuration")
        
        # Extraction method selection
        method = st.selectbox(
            "Extraction Method",
            options=["hybrid", "vlm", "azure", "traditional"],
            help="Choose the extraction method:\n"
                 "- Hybrid: Combines multiple methods for best results\n"
                 "- VLM: Uses Vision Language Models\n"
                 "- Azure: Uses Azure AI Document Intelligence\n"
                 "- Traditional: Uses computer vision and OCR"
        )
        
        # VLM model selection (if VLM method selected)
        vlm_model = "gpt-4-vision"
        if method in ["vlm", "hybrid"]:
            vlm_model = st.selectbox(
                "VLM Model",
                options=["gpt-4-vision", "claude-vision", "gemini-vision", "llava", "blip2"],
                help="Select the Vision Language Model to use"
            )
        
        # Target content type
        target_type = st.selectbox(
            "Content Type",
            options=["figure", "table", "algorithm", "equation", "diagram", "chart"],
            help="Type of content to extract from the PDF"
        )
        
        # Specific identifier
        identifier = st.text_input(
            "Specific Identifier (Optional)",
            placeholder="e.g., Figure 1, Algorithm 2",
            help="Extract only content matching this identifier"
        )
        
        # Page range
        pages = st.text_input(
            "Page Range (Optional)",
            placeholder="e.g., 1-5, 1,3,5",
            help="Specify pages to process (leave empty for all pages)"
        )
        
        # Advanced settings
        with st.expander("Advanced Settings"):
            confidence = st.slider(
                "Confidence Threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.7,
                step=0.05,
                help="Minimum confidence score for extracted content"
            )
            
            output_format = st.selectbox(
                "Output Format",
                options=["png", "jpg", "pdf"],
                help="Format for extracted images"
            )
            
            include_captions = st.checkbox(
                "Include Captions",
                value=True,
                help="Extract and include captions with visual content"
            )
            
            custom_patterns = st.text_area(
                "Custom Patterns (Advanced)",
                placeholder="Enter regex patterns, one per line",
                help="Custom regex patterns for extraction"
            )
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📤 Upload PDF")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            help="Upload the PDF document you want to extract content from"
        )
        
        if uploaded_file is not None:
            # Display file info
            st.success(f"Uploaded: {uploaded_file.name}")
            st.info(f"File size: {len(uploaded_file.getvalue()) / 1024 / 1024:.1f} MB")
            
            # Process button
            if st.button("🚀 Extract Content", type="primary"):
                process_pdf(uploaded_file, method, vlm_model, target_type, identifier, 
                           pages, confidence, output_format, include_captions, custom_patterns)
    
    with col2:
        st.header("📋 Instructions")
        
        st.markdown("""
        ### How to use:
        
        1. **Configure settings** in the sidebar:
           - Choose extraction method
           - Select content type to extract
           - Optionally specify identifiers or page ranges
        
        2. **Upload your PDF** using the file uploader
        
        3. **Click "Extract Content"** to start processing
        
        4. **Download results** when extraction completes
        
        ### Extraction Methods:
        
        **🔄 Hybrid (Recommended)**
        - Combines multiple AI methods
        - Best accuracy and robustness
        - Automatically selects best approach
        
        **🤖 Vision Language Models (VLM)**
        - Uses advanced AI models like GPT-4V
        - Best for complex layouts
        - Requires API keys for commercial models
        
        **☁️ Azure Document Intelligence**
        - Microsoft's document AI service
        - Good for structured documents
        - Requires Azure subscription
        
        **🔧 Traditional CV+OCR**
        - Computer vision and OCR
        - Fastest processing
        - Works offline
        
        ### Content Types:
        - **Figures**: Charts, diagrams, images
        - **Tables**: Data tables with structure
        - **Algorithms**: Pseudocode blocks
        - **Equations**: Mathematical formulas
        - **Diagrams**: Flowcharts, schematics
        - **Charts**: Graphs and visualizations
        """)
    
    # Examples section
    st.header("💡 Examples")
    
    example_col1, example_col2, example_col3 = st.columns(3)
    
    with example_col1:
        st.subheader("Extract Specific Figure")
        st.code("""
        Target: figure
        Identifier: Figure 1
        Method: hybrid
        """)
        st.caption("Extract 'Figure 1' from the document")
    
    with example_col2:
        st.subheader("Extract All Tables")
        st.code("""
        Target: table
        Identifier: (empty)
        Method: azure
        """)
        st.caption("Extract all tables from the document")
    
    with example_col3:
        st.subheader("Extract Algorithm")
        st.code("""
        Target: algorithm
        Pages: 3-5
        Method: vlm
        """)
        st.caption("Extract algorithms from pages 3-5")


def process_pdf(uploaded_file, method, vlm_model, target_type, identifier, 
                pages, confidence, output_format, include_captions, custom_patterns):
    """Process the uploaded PDF file."""
    
    try:
        # Create progress indicator
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("🔄 Setting up extraction...")
        progress_bar.progress(10)
        
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            pdf_path = Path(tmp_file.name)
        
        # Parse configuration
        page_list = None
        if pages:
            page_list = parse_page_range(pages)
        
        patterns = []
        if custom_patterns:
            patterns = [p.strip() for p in custom_patterns.split('\n') if p.strip()]
        
        # Create temporary output directory
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "extracted_content"
            output_dir.mkdir(exist_ok=True)
            
            status_text.text("⚙️ Creating extraction configuration...")
            progress_bar.progress(20)
            
            # Create extraction configuration
            config = ExtractionConfig(
                target_type=TargetType(target_type),
                target_identifier=identifier if identifier else None,
                extraction_method=ExtractionMethod(method),
                vlm_model=vlm_model,
                pages=page_list,
                output_dir=str(output_dir),
                output_format=output_format,
                confidence_threshold=confidence,
                include_captions=include_captions,
                custom_patterns=patterns
            )
            
            status_text.text("🤖 Initializing extractor...")
            progress_bar.progress(30)
            
            # Create extractor and extract
            extractor = PDFExtractor(config)
            
            status_text.text("🔍 Extracting content...")
            progress_bar.progress(50)
            
            results = extractor.extract(pdf_path, config)
            
            progress_bar.progress(80)
            status_text.text("📊 Processing results...")
            
            # Display results
            display_results(results, output_dir, progress_bar, status_text)
        
        # Clean up temporary PDF file
        os.unlink(pdf_path)
        
    except Exception as e:
        st.error(f"❌ Extraction failed: {str(e)}")
        st.exception(e)


def display_results(results: List, output_dir: Path, progress_bar, status_text):
    """Display extraction results in the UI."""
    
    progress_bar.progress(90)
    status_text.text("✅ Extraction completed!")
    
    if not results:
        st.warning("⚠️ No content found matching your criteria. Try adjusting the settings or confidence threshold.")
        return
    
    st.success(f"🎉 Successfully extracted {len(results)} elements!")
    
    # Results overview
    st.subheader("📈 Extraction Summary")
    
    # Create summary dataframe
    summary_data = []
    for result in results:
        summary_data.append({
            "Element ID": result.element_id,
            "Type": result.element_type,
            "Page": result.page_number,
            "Confidence": f"{result.confidence:.2f}",
            "Caption": result.caption[:50] + "..." if result.caption and len(result.caption) > 50 else result.caption or "N/A"
        })
    
    df = pd.DataFrame(summary_data)
    st.dataframe(df, use_container_width=True)
    
    # Display extracted images
    st.subheader("🖼️ Extracted Content")
    
    cols = st.columns(min(3, len(results)))
    
    for idx, result in enumerate(results[:9]):  # Limit to first 9 results
        col = cols[idx % 3]
        
        with col:
            st.write(f"**{result.element_id}**")
            st.write(f"Page {result.page_number} | Confidence: {result.confidence:.2f}")
            
            if result.image_path and Path(result.image_path).exists():
                try:
                    image = Image.open(result.image_path)
                    st.image(image, use_column_width=True)
                except Exception as e:
                    st.error(f"Could not display image: {e}")
            
            if result.caption:
                with st.expander("Caption"):
                    st.write(result.caption)
    
    # Download section
    st.subheader("📥 Download Results")
    
    # Create download package
    zip_buffer = create_download_package(results, output_dir)
    
    if zip_buffer:
        st.download_button(
            label="📦 Download All Results (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="extracted_content.zip",
            mime="application/zip"
        )
    
    # Individual downloads
    with st.expander("Individual Downloads"):
        for result in results:
            if result.image_path and Path(result.image_path).exists():
                with open(result.image_path, 'rb') as f:
                    st.download_button(
                        label=f"📄 {result.element_id}",
                        data=f.read(),
                        file_name=f"{result.element_id}.{result.image_path.split('.')[-1]}",
                        mime=f"image/{result.image_path.split('.')[-1]}"
                    )
    
    progress_bar.progress(100)
    status_text.text("🎊 All done!")


def create_download_package(results: List, output_dir: Path) -> Optional[io.BytesIO]:
    """Create a ZIP file containing all extraction results."""
    
    try:
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add extracted images
            for result in results:
                if result.image_path and Path(result.image_path).exists():
                    zip_file.write(result.image_path, f"images/{Path(result.image_path).name}")
            
            # Add metadata
            metadata = {
                "extraction_summary": {
                    "total_elements": len(results),
                    "elements": [result.to_dict() for result in results]
                }
            }
            
            zip_file.writestr("metadata.json", json.dumps(metadata, indent=2))
            
            # Add summary CSV
            if results:
                summary_data = []
                for result in results:
                    summary_data.append({
                        "element_id": result.element_id,
                        "element_type": result.element_type,
                        "page_number": result.page_number,
                        "confidence": result.confidence,
                        "caption": result.caption or "",
                        "image_file": Path(result.image_path).name if result.image_path else ""
                    })
                
                df = pd.DataFrame(summary_data)
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)
                zip_file.writestr("summary.csv", csv_buffer.getvalue())
        
        zip_buffer.seek(0)
        return zip_buffer
        
    except Exception as e:
        st.error(f"Failed to create download package: {e}")
        return None


def parse_page_range(page_range: str) -> List[int]:
    """Parse page range string to list of page numbers."""
    pages = []
    try:
        for part in page_range.split(','):
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                pages.extend(range(start, end + 1))
            else:
                pages.append(int(part))
        return sorted(list(set(pages)))
    except ValueError:
        st.error("Invalid page range format. Use formats like '1,3,5' or '1-5'")
        return []


# Additional utility functions
def show_setup_info():
    """Show setup and configuration information."""
    
    st.sidebar.header("🔧 Setup Information")
    
    # Check API keys
    api_status = {}
    
    if os.getenv("OPENAI_API_KEY"):
        api_status["OpenAI"] = "✅ Configured"
    else:
        api_status["OpenAI"] = "⚠️ Not configured"
    
    if os.getenv("ANTHROPIC_API_KEY"):
        api_status["Anthropic"] = "✅ Configured"
    else:
        api_status["Anthropic"] = "⚠️ Not configured"
    
    if os.getenv("AZURE_DOC_INTELLIGENCE_KEY"):
        api_status["Azure"] = "✅ Configured"
    else:
        api_status["Azure"] = "⚠️ Not configured"
    
    with st.sidebar.expander("API Status"):
        for service, status in api_status.items():
            st.write(f"{service}: {status}")
    
    # Help and documentation
    with st.sidebar.expander("Need Help?"):
        st.markdown("""
        **Common Issues:**
        - API keys not configured
        - Large files timing out
        - Low extraction accuracy
        
        **Tips:**
        - Use hybrid method for best results
        - Adjust confidence threshold
        - Specify page ranges for large PDFs
        - Try different VLM models
        """)


if __name__ == "__main__":
    main()
    show_setup_info()