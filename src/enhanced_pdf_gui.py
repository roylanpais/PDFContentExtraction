
"""
Enhanced Interactive Interface
=============================

Advanced user interface supporting all AI backends with dynamic configuration,
real-time backend switching, and comprehensive content management.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import asyncio
from threading import Thread
import json
from pathlib import Path
from dataclasses import asdict

# Import our backend systems
from generalized_pdf_extractor import (
    GeneralizedPDFExtractor, ExtractionConfig, ExtractionBackend, 
    ContentType, ExtractedContent
)
from additional_backends import (
    create_backend_map, create_nvidia_config, create_azure_config,
    create_openai_config, create_google_config, create_aws_config,
    create_huggingface_config, create_traditional_cv_config
)

class EnhancedPDFExtractorGUI:
    """Enhanced GUI with support for all AI backends."""

    def __init__(self, root):
        self.root = root
        self.root.title("Enhanced AI-Powered PDF Content Extractor")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')

        # State variables
        self.pdf_path = tk.StringVar()
        self.output_path = tk.StringVar(value="extracted_content")
        self.selected_backend = tk.StringVar(value=ExtractionBackend.TRADITIONAL_CV.value)

        # Backend configurations
        self.backend_configs = {}
        self.current_extractor = None
        self.available_content = {}

        # Selection variables by content type
        self.content_selections = {
            content_type.value: {} for content_type in ContentType
        }

        self.setup_ui()
        self.setup_backend_configs()

    def setup_ui(self):
        """Setup the enhanced user interface."""
        # Create notebook for tabbed interface
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Configuration tab
        self.config_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.config_frame, text="🔧 Configuration")
        self.setup_configuration_tab()

        # Content detection tab
        self.detection_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.detection_frame, text="🔍 Content Detection")
        self.setup_detection_tab()

        # Content selection tab
        self.selection_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.selection_frame, text="📋 Content Selection")
        self.setup_selection_tab()

        # Extraction results tab
        self.results_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.results_frame, text="📊 Results")
        self.setup_results_tab()

    def setup_configuration_tab(self):
        """Setup configuration tab with backend selection and credentials."""
        # Title
        title_label = ttk.Label(self.config_frame, text="AI-Powered PDF Content Extractor", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(10, 20))

        # File selection frame
        file_frame = ttk.LabelFrame(self.config_frame, text="Document & Output", padding="10")
        file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)

        # PDF file input
        ttk.Label(file_frame, text="PDF File:").grid(row=0, column=0, sticky=tk.W, pady=2)
        pdf_entry = ttk.Entry(file_frame, textvariable=self.pdf_path, width=60)
        pdf_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 5), pady=2)
        ttk.Button(file_frame, text="Browse", command=self.browse_pdf).grid(
            row=0, column=2, padx=(5, 0), pady=2)

        # Output directory
        ttk.Label(file_frame, text="Output Dir:").grid(row=1, column=0, sticky=tk.W, pady=2)
        output_entry = ttk.Entry(file_frame, textvariable=self.output_path, width=60)
        output_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 5), pady=2)
        ttk.Button(file_frame, text="Browse", command=self.browse_output).grid(
            row=1, column=2, padx=(5, 0), pady=2)

        # Backend selection frame
        backend_frame = ttk.LabelFrame(self.config_frame, text="AI Backend Selection", padding="10")
        backend_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        backend_frame.columnconfigure(1, weight=1)

        # Backend selection
        ttk.Label(backend_frame, text="AI Backend:").grid(row=0, column=0, sticky=tk.W, pady=2)
        backend_combo = ttk.Combobox(backend_frame, textvariable=self.selected_backend, 
                                    values=[backend.value for backend in ExtractionBackend],
                                    state='readonly', width=30)
        backend_combo.grid(row=0, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        backend_combo.bind('<<ComboboxSelected>>', self.on_backend_changed)

        # Backend info
        self.backend_info_label = ttk.Label(backend_frame, text="Select a backend to see details", 
                                           foreground='gray')
        self.backend_info_label.grid(row=1, column=0, columnspan=3, pady=(5, 0))

        # Credentials frame (dynamic based on backend)
        self.credentials_frame = ttk.LabelFrame(self.config_frame, text="API Credentials", padding="10")
        self.credentials_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        self.credentials_frame.columnconfigure(1, weight=1)

        # Initialize with Traditional CV (no credentials needed)
        self.setup_credentials_ui()

        # Action buttons
        action_frame = ttk.Frame(self.config_frame)
        action_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0))

        ttk.Button(action_frame, text="Test Connection", command=self.test_backend_connection).pack(
            side=tk.LEFT, padx=(0, 10))
        ttk.Button(action_frame, text="Analyze PDF", command=self.analyze_pdf).pack(
            side=tk.LEFT)

    def setup_detection_tab(self):
        """Setup content detection tab."""
        # Detection results display
        detection_label = ttk.Label(self.detection_frame, text="Detected Content", 
                                   font=('Arial', 14, 'bold'))
        detection_label.pack(pady=(10, 5))

        # Treeview for detected content
        columns = ('Type', 'Title', 'Description', 'Page', 'Confidence')
        self.detection_tree = ttk.Treeview(self.detection_frame, columns=columns, show='headings')

        for col in columns:
            self.detection_tree.heading(col, text=col)
            self.detection_tree.column(col, width=150)

        # Scrollbars for treeview
        v_scrollbar = ttk.Scrollbar(self.detection_frame, orient=tk.VERTICAL, command=self.detection_tree.yview)
        h_scrollbar = ttk.Scrollbar(self.detection_frame, orient=tk.HORIZONTAL, command=self.detection_tree.xview)
        self.detection_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Pack treeview and scrollbars
        self.detection_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X, padx=(10, 10))

        # Detection controls
        control_frame = ttk.Frame(self.detection_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(control_frame, text="Refresh Detection", command=self.refresh_detection).pack(
            side=tk.LEFT, padx=10)
        ttk.Button(control_frame, text="Export Detection Results", command=self.export_detection).pack(
            side=tk.LEFT, padx=10)

    def setup_selection_tab(self):
        """Setup content selection tab with dynamic content types."""
        selection_label = ttk.Label(self.selection_frame, text="Select Content for Extraction", 
                                   font=('Arial', 14, 'bold'))
        selection_label.pack(pady=(10, 5))

        # Create canvas and scrollbar for scrollable content
        canvas = tk.Canvas(self.selection_frame)
        scrollbar = ttk.Scrollbar(self.selection_frame, orient="vertical", command=canvas.yview)
        self.scrollable_selection_frame = ttk.Frame(canvas)

        self.scrollable_selection_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_selection_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=(10, 0))
        scrollbar.pack(side="right", fill="y")

        # Selection controls
        selection_control_frame = ttk.Frame(self.selection_frame)
        selection_control_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(selection_control_frame, text="Select All", command=self.select_all_content).pack(
            side=tk.LEFT, padx=5)
        ttk.Button(selection_control_frame, text="Clear All", command=self.clear_all_content).pack(
            side=tk.LEFT, padx=5)
        ttk.Button(selection_control_frame, text="Extract Selected", 
                  command=self.extract_selected_content, style='Accent.TButton').pack(
            side=tk.RIGHT, padx=5)

    def setup_results_tab(self):
        """Setup results tab for extraction outputs."""
        results_label = ttk.Label(self.results_frame, text="Extraction Results", 
                                 font=('Arial', 14, 'bold'))
        results_label.pack(pady=(10, 5))

        # Results display
        self.results_text = scrolledtext.ScrolledText(self.results_frame, height=25, width=100)
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Progress bar
        self.progress_bar = ttk.Progressbar(self.results_frame, mode='indeterminate')
        self.progress_bar.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Results controls
        results_control_frame = ttk.Frame(self.results_frame)
        results_control_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(results_control_frame, text="Save Results", command=self.save_results).pack(
            side=tk.LEFT, padx=5)
        ttk.Button(results_control_frame, text="Clear Results", command=self.clear_results).pack(
            side=tk.LEFT, padx=5)
        ttk.Button(results_control_frame, text="Open Output Folder", command=self.open_output_folder).pack(
            side=tk.RIGHT, padx=5)

    def setup_backend_configs(self):
        """Initialize backend configurations."""
        self.backend_configs = {
            ExtractionBackend.TRADITIONAL_CV.value: create_traditional_cv_config(),
            ExtractionBackend.NVIDIA_NVLM.value: None,
            ExtractionBackend.AZURE_DOCUMENT_INTELLIGENCE.value: None,
            ExtractionBackend.OPENAI_GPT4V.value: None,
            ExtractionBackend.GOOGLE_DOCUMENT_AI.value: None,
            ExtractionBackend.AWS_TEXTRACT.value: None,
            ExtractionBackend.HUGGINGFACE_TRANSFORMERS.value: None,
        }

    def setup_credentials_ui(self):
        """Setup credentials UI based on selected backend."""
        # Clear existing widgets
        for widget in self.credentials_frame.winfo_children():
            widget.destroy()

        backend = self.selected_backend.get()

        if backend == ExtractionBackend.TRADITIONAL_CV.value:
            ttk.Label(self.credentials_frame, text="No credentials required for Traditional CV", 
                     foreground='green').pack(pady=10)

        elif backend == ExtractionBackend.NVIDIA_NVLM.value:
            self.setup_nvidia_credentials()

        elif backend == ExtractionBackend.AZURE_DOCUMENT_INTELLIGENCE.value:
            self.setup_azure_credentials()

        elif backend == ExtractionBackend.OPENAI_GPT4V.value:
            self.setup_openai_credentials()

        elif backend == ExtractionBackend.GOOGLE_DOCUMENT_AI.value:
            self.setup_google_credentials()

        elif backend == ExtractionBackend.AWS_TEXTRACT.value:
            self.setup_aws_credentials()

        elif backend == ExtractionBackend.HUGGINGFACE_TRANSFORMERS.value:
            self.setup_huggingface_credentials()

    def setup_nvidia_credentials(self):
        """Setup NVIDIA NVLM credentials form."""
        ttk.Label(self.credentials_frame, text="NVIDIA API Key:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.nvidia_api_key = ttk.Entry(self.credentials_frame, width=50, show='*')
        self.nvidia_api_key.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)

        info_label = ttk.Label(self.credentials_frame, 
                              text="Get your NVIDIA API key from: https://build.nvidia.com/nvidia/nvlm-d-72b", 
                              foreground='blue', cursor='hand2')
        info_label.grid(row=1, column=0, columnspan=2, pady=(5, 0))

    def setup_azure_credentials(self):
        """Setup Azure Document Intelligence credentials form."""
        ttk.Label(self.credentials_frame, text="Azure Endpoint:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.azure_endpoint = ttk.Entry(self.credentials_frame, width=50)
        self.azure_endpoint.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)

        ttk.Label(self.credentials_frame, text="Azure API Key:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.azure_api_key = ttk.Entry(self.credentials_frame, width=50, show='*')
        self.azure_api_key.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)

    def setup_openai_credentials(self):
        """Setup OpenAI GPT-4V credentials form."""
        ttk.Label(self.credentials_frame, text="OpenAI API Key:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.openai_api_key = ttk.Entry(self.credentials_frame, width=50, show='*')
        self.openai_api_key.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)

    def setup_google_credentials(self):
        """Setup Google Document AI credentials form."""
        ttk.Label(self.credentials_frame, text="Project ID:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.google_project_id = ttk.Entry(self.credentials_frame, width=50)
        self.google_project_id.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)

        ttk.Label(self.credentials_frame, text="Processor ID:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.google_processor_id = ttk.Entry(self.credentials_frame, width=50)
        self.google_processor_id.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)

        ttk.Label(self.credentials_frame, text="Location:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.google_location = ttk.Entry(self.credentials_frame, width=50)
        self.google_location.insert(0, "us")
        self.google_location.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)

    def setup_aws_credentials(self):
        """Setup AWS Textract credentials form."""
        ttk.Label(self.credentials_frame, text="Access Key ID:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.aws_access_key = ttk.Entry(self.credentials_frame, width=50, show='*')
        self.aws_access_key.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)

        ttk.Label(self.credentials_frame, text="Secret Access Key:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.aws_secret_key = ttk.Entry(self.credentials_frame, width=50, show='*')
        self.aws_secret_key.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)

        ttk.Label(self.credentials_frame, text="Region:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.aws_region = ttk.Entry(self.credentials_frame, width=50)
        self.aws_region.insert(0, "us-east-1")
        self.aws_region.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)

    def setup_huggingface_credentials(self):
        """Setup Hugging Face Transformers credentials form."""
        ttk.Label(self.credentials_frame, text="Model Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.hf_model_name = ttk.Entry(self.credentials_frame, width=50)
        self.hf_model_name.insert(0, "Salesforce/blip-image-captioning-base")
        self.hf_model_name.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)

    def on_backend_changed(self, event=None):
        """Handle backend selection change."""
        backend = self.selected_backend.get()

        # Update backend info
        backend_info = {
            ExtractionBackend.TRADITIONAL_CV.value: "Uses OpenCV and classical computer vision techniques. No API required.",
            ExtractionBackend.NVIDIA_NVLM.value: "NVIDIA's advanced vision-language model. Requires NVIDIA API key.",
            ExtractionBackend.AZURE_DOCUMENT_INTELLIGENCE.value: "Microsoft's document understanding service. Requires Azure credentials.",
            ExtractionBackend.OPENAI_GPT4V.value: "OpenAI's GPT-4 with vision capabilities. Requires OpenAI API key.",
            ExtractionBackend.GOOGLE_DOCUMENT_AI.value: "Google's document processing service. Requires Google Cloud credentials.",
            ExtractionBackend.AWS_TEXTRACT.value: "Amazon's text and data extraction service. Requires AWS credentials.",
            ExtractionBackend.HUGGINGFACE_TRANSFORMERS.value: "Open-source models from Hugging Face. No API required."
        }

        self.backend_info_label.config(text=backend_info.get(backend, "Unknown backend"))

        # Update credentials UI
        self.setup_credentials_ui()

    def browse_pdf(self):
        """Browse for PDF file."""
        filename = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if filename:
            self.pdf_path.set(filename)

    def browse_output(self):
        """Browse for output directory."""
        dirname = filedialog.askdirectory(title="Select Output Directory")
        if dirname:
            self.output_path.set(dirname)

    def test_backend_connection(self):
        """Test connection to selected backend."""
        try:
            config = self.create_current_config()
            if not config:
                return

            # Create extractor and test initialization
            extractor = GeneralizedPDFExtractor(config)

            # Run test in separate thread
            def test_connection():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(extractor.initialize())

                    if result:
                        self.root.after(0, lambda: messagebox.showinfo(
                            "Success", f"Successfully connected to {self.selected_backend.get()}!"))
                    else:
                        self.root.after(0, lambda: messagebox.showerror(
                            "Connection Failed", f"Failed to connect to {self.selected_backend.get()}"))
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Error", f"Connection test failed: {str(e)}"))

            Thread(target=test_connection, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to test connection: {str(e)}")

    def create_current_config(self) -> ExtractionConfig:
        """Create configuration based on current settings."""
        backend = self.selected_backend.get()

        try:
            if backend == ExtractionBackend.TRADITIONAL_CV.value:
                return create_traditional_cv_config()

            elif backend == ExtractionBackend.NVIDIA_NVLM.value:
                api_key = getattr(self, 'nvidia_api_key', None)
                if not api_key or not api_key.get():
                    messagebox.showerror("Error", "NVIDIA API key is required")
                    return None
                return create_nvidia_config(api_key.get())

            elif backend == ExtractionBackend.AZURE_DOCUMENT_INTELLIGENCE.value:
                endpoint = getattr(self, 'azure_endpoint', None)
                api_key = getattr(self, 'azure_api_key', None)
                if not endpoint or not api_key or not endpoint.get() or not api_key.get():
                    messagebox.showerror("Error", "Azure endpoint and API key are required")
                    return None
                return create_azure_config(endpoint.get(), api_key.get())

            elif backend == ExtractionBackend.OPENAI_GPT4V.value:
                api_key = getattr(self, 'openai_api_key', None)
                if not api_key or not api_key.get():
                    messagebox.showerror("Error", "OpenAI API key is required")
                    return None
                return create_openai_config(api_key.get())

            elif backend == ExtractionBackend.GOOGLE_DOCUMENT_AI.value:
                project_id = getattr(self, 'google_project_id', None)
                processor_id = getattr(self, 'google_processor_id', None)
                location = getattr(self, 'google_location', None)
                if not project_id or not processor_id or not project_id.get() or not processor_id.get():
                    messagebox.showerror("Error", "Google project ID and processor ID are required")
                    return None
                return create_google_config(project_id.get(), processor_id.get(), 
                                          location.get() if location else 'us')

            elif backend == ExtractionBackend.AWS_TEXTRACT.value:
                access_key = getattr(self, 'aws_access_key', None)
                secret_key = getattr(self, 'aws_secret_key', None)
                region = getattr(self, 'aws_region', None)
                if not access_key or not secret_key or not access_key.get() or not secret_key.get():
                    messagebox.showerror("Error", "AWS access key and secret key are required")
                    return None
                return create_aws_config(access_key.get(), secret_key.get(), 
                                       region.get() if region else 'us-east-1')

            elif backend == ExtractionBackend.HUGGINGFACE_TRANSFORMERS.value:
                model_name = getattr(self, 'hf_model_name', None)
                model = model_name.get() if model_name else 'Salesforce/blip-image-captioning-base'
                return create_huggingface_config(model)

            else:
                messagebox.showerror("Error", f"Unsupported backend: {backend}")
                return None

        except Exception as e:
            messagebox.showerror("Error", f"Failed to create configuration: {str(e)}")
            return None

    def analyze_pdf(self):
        """Analyze PDF using selected backend."""
        if not self.pdf_path.get():
            messagebox.showerror("Error", "Please select a PDF file first")
            return

        config = self.create_current_config()
        if not config:
            return

        self.progress_bar.start()
        self.log_message("Starting PDF analysis...")

        def analyze():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                extractor = GeneralizedPDFExtractor(config)
                if not loop.run_until_complete(extractor.initialize()):
                    self.root.after(0, lambda: messagebox.showerror("Error", "Failed to initialize backend"))
                    return

                self.current_extractor = extractor
                available_content = loop.run_until_complete(
                    extractor.detect_available_content(self.pdf_path.get())
                )

                self.root.after(0, lambda: self.update_detection_results(available_content))

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Analysis failed: {str(e)}"))
            finally:
                self.root.after(0, lambda: self.progress_bar.stop())

        Thread(target=analyze, daemon=True).start()

    def update_detection_results(self, available_content):
        """Update detection results in the UI."""
        self.available_content = available_content

        # Clear existing items
        for item in self.detection_tree.get_children():
            self.detection_tree.delete(item)

        # Add detected content to treeview
        for content_type, items in available_content.items():
            for item in items:
                self.detection_tree.insert('', 'end', values=(
                    content_type.title(),
                    item.get('title', 'N/A'),
                    item.get('description', 'N/A')[:50] + '...' if len(item.get('description', '')) > 50 else item.get('description', 'N/A'),
                    item.get('page', 'N/A'),
                    f"{item.get('confidence', 0):.2f}" if item.get('confidence') else 'N/A'
                ))

        # Update selection tab
        self.update_selection_options()

        # Switch to detection tab
        self.notebook.select(1)

        self.log_message(f"Analysis complete. Found {sum(len(items) for items in available_content.values())} items.")

    def update_selection_options(self):
        """Update content selection options."""
        # Clear existing selection widgets
        for widget in self.scrollable_selection_frame.winfo_children():
            widget.destroy()

        self.content_selections = {content_type.value: {} for content_type in ContentType}

        # Create selection widgets for each content type
        for content_type, items in self.available_content.items():
            if not items:
                continue

            # Create frame for this content type
            type_frame = ttk.LabelFrame(self.scrollable_selection_frame, 
                                       text=f"{content_type.title()} ({len(items)} items)", 
                                       padding="10")
            type_frame.pack(fill=tk.X, padx=10, pady=5)

            # Select all/none buttons for this type
            button_frame = ttk.Frame(type_frame)
            button_frame.pack(fill=tk.X, pady=(0, 5))

            ttk.Button(button_frame, text="Select All", 
                      command=lambda ct=content_type: self.select_all_type(ct)).pack(side=tk.LEFT)
            ttk.Button(button_frame, text="Clear All", 
                      command=lambda ct=content_type: self.clear_all_type(ct)).pack(side=tk.LEFT, padx=(5, 0))

            # Checkboxes for each item
            for item in items:
                var = tk.BooleanVar()
                self.content_selections[content_type][item['title']] = var

                cb = ttk.Checkbutton(type_frame, 
                                    text=f"{item['title']} (Page {item.get('page', 'N/A')})", 
                                    variable=var)
                cb.pack(anchor=tk.W, pady=1)

    def select_all_type(self, content_type):
        """Select all items of a specific content type."""
        for var in self.content_selections[content_type].values():
            var.set(True)

    def clear_all_type(self, content_type):
        """Clear all items of a specific content type."""
        for var in self.content_selections[content_type].values():
            var.set(False)

    def select_all_content(self):
        """Select all available content."""
        for content_type in self.content_selections.values():
            for var in content_type.values():
                var.set(True)

    def clear_all_content(self):
        """Clear all content selections."""
        for content_type in self.content_selections.values():
            for var in content_type.values():
                var.set(False)

    def extract_selected_content(self):
        """Extract user-selected content."""
        if not self.current_extractor:
            messagebox.showerror("Error", "Please analyze PDF first")
            return

        # Get selections
        selections = {}
        total_selected = 0

        for content_type, items in self.content_selections.items():
            selected_items = [title for title, var in items.items() if var.get()]
            selections[content_type] = selected_items
            total_selected += len(selected_items)

        if total_selected == 0:
            messagebox.showwarning("Warning", "No content selected for extraction")
            return

        if not messagebox.askyesno("Confirm", f"Extract {total_selected} selected items?"):
            return

        self.progress_bar.start()
        self.log_message(f"Extracting {total_selected} selected items...")

        def extract():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                results = loop.run_until_complete(
                    self.current_extractor.extract_selected_content(self.pdf_path.get(), selections)
                )

                summary_path = self.current_extractor.save_extraction_results(
                    results, self.pdf_path.get()
                )

                self.root.after(0, lambda: self.show_extraction_results(results, summary_path))

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Extraction failed: {str(e)}"))
            finally:
                self.root.after(0, lambda: self.progress_bar.stop())

        Thread(target=extract, daemon=True).start()

    def show_extraction_results(self, results, summary_path):
        """Show extraction results."""
        # Switch to results tab
        self.notebook.select(3)

        # Display results
        total_extracted = sum(len(items) for items in results.values())

        result_text = f"🎉 EXTRACTION COMPLETED SUCCESSFULLY!\n"
        result_text += f"{'=' * 60}\n\n"
        result_text += f"📊 Total items extracted: {total_extracted}\n"
        result_text += f"🔧 Backend used: {self.selected_backend.get()}\n"
        result_text += f"📁 Output directory: {self.output_path.get()}\n"
        result_text += f"📄 Summary file: {summary_path}\n\n"

        for content_type, items in results.items():
            if items:
                result_text += f"📋 {content_type.upper()}:\n"
                for item in items:
                    result_text += f"  • {item.title} (Page {item.page_number})\n"
                    if item.description:
                        result_text += f"    Description: {item.description[:100]}...\n"
                result_text += "\n"

        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, result_text)

        self.log_message("Extraction completed successfully!")

        messagebox.showinfo("Success", 
                           f"Extraction completed!\n\n"
                           f"Items extracted: {total_extracted}\n"
                           f"Output: {self.output_path.get()}")

    def refresh_detection(self):
        """Refresh content detection."""
        if self.current_extractor and self.pdf_path.get():
            self.analyze_pdf()
        else:
            messagebox.showwarning("Warning", "Please configure backend and select PDF first")

    def export_detection(self):
        """Export detection results."""
        if not self.available_content:
            messagebox.showwarning("Warning", "No detection results to export")
            return

        filename = filedialog.asksaveasfilename(
            title="Export Detection Results",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.available_content, f, indent=2, default=str)
                messagebox.showinfo("Success", f"Detection results exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")

    def save_results(self):
        """Save extraction results."""
        if not self.results_text.get(1.0, tk.END).strip():
            messagebox.showwarning("Warning", "No results to save")
            return

        filename = filedialog.asksaveasfilename(
            title="Save Results",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.results_text.get(1.0, tk.END))
                messagebox.showinfo("Success", f"Results saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {str(e)}")

    def clear_results(self):
        """Clear results display."""
        self.results_text.delete(1.0, tk.END)

    def open_output_folder(self):
        """Open output folder in file explorer."""
        import os
        import subprocess
        import sys

        output_path = Path(self.output_path.get())
        if output_path.exists():
            try:
                if sys.platform == "win32":
                    os.startfile(output_path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", output_path])
                else:
                    subprocess.run(["xdg-open", output_path])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open folder: {str(e)}")
        else:
            messagebox.showwarning("Warning", "Output folder does not exist")

    def log_message(self, message):
        """Log message to results area."""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.results_text.insert(tk.END, log_entry)
        self.results_text.see(tk.END)


def main():
    """Main function to run the enhanced GUI."""
    root = tk.Tk()
    app = EnhancedPDFExtractorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
