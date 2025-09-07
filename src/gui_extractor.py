
"""
GUI PDF Content Extractor
=========================

Graphical user interface for selecting and extracting content from PDFs.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import threading
from pathlib import Path
from interactive_extractor import InteractivePDFExtractor

class PDFExtractorGUI:
    """
    Graphical user interface for the PDF content extractor.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Interactive PDF Content Extractor")
        self.root.geometry("900x700")
        self.root.configure(bg='#f0f0f0')

        self.extractor = None
        self.pdf_path = tk.StringVar()
        self.output_path = tk.StringVar(value="extracted_content")

        # Selection variables
        self.figure_vars = {}
        self.algorithm_vars = {}
        self.table_vars = {}
        self.equation_vars = {}

        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface components."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="PDF Content Extractor", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # File selection section
        self.setup_file_selection(main_frame, row=1)

        # Content selection section  
        self.setup_content_selection(main_frame, row=2)

        # Action buttons
        self.setup_action_buttons(main_frame, row=3)

        # Progress and output section
        self.setup_output_section(main_frame, row=4)

    def setup_file_selection(self, parent, row):
        """Setup file selection UI components."""
        # File selection frame
        file_frame = ttk.LabelFrame(parent, text="PDF File Selection", padding="10")
        file_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)

        # PDF file input
        ttk.Label(file_frame, text="PDF File:").grid(row=0, column=0, sticky=tk.W, pady=2)
        pdf_entry = ttk.Entry(file_frame, textvariable=self.pdf_path, width=50)
        pdf_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 5), pady=2)
        ttk.Button(file_frame, text="Browse", command=self.browse_pdf).grid(
            row=0, column=2, padx=(5, 0), pady=2)

        # Output directory
        ttk.Label(file_frame, text="Output Dir:").grid(row=1, column=0, sticky=tk.W, pady=2)
        output_entry = ttk.Entry(file_frame, textvariable=self.output_path, width=50)
        output_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 5), pady=2)
        ttk.Button(file_frame, text="Browse", command=self.browse_output).grid(
            row=1, column=2, padx=(5, 0), pady=2)

        # Analyze button
        ttk.Button(file_frame, text="Analyze PDF", command=self.analyze_pdf).grid(
            row=2, column=0, columnspan=3, pady=(10, 0))

    def setup_content_selection(self, parent, row):
        """Setup content selection UI components."""
        # Content selection notebook
        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # Configure weight for notebook expansion
        parent.rowconfigure(row, weight=1)

        # Create tabs for different content types
        self.figures_frame = self.create_content_tab("Figures", "📊")
        self.algorithms_frame = self.create_content_tab("Algorithms", "🤖")  
        self.tables_frame = self.create_content_tab("Tables", "📋")
        self.equations_frame = self.create_content_tab("Equations", "🧮")

        # Initially disable tabs
        for i in range(4):
            self.notebook.tab(i, state='disabled')

    def create_content_tab(self, name, icon):
        """Create a content selection tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=f"{icon} {name}")

        # Create scrollable frame
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        return scrollable_frame

    def setup_action_buttons(self, parent, row):
        """Setup action buttons."""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, columnspan=3, pady=(0, 10))

        ttk.Button(button_frame, text="Select All", command=self.select_all).pack(
            side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Clear All", command=self.clear_all).pack(
            side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Extract Selected", command=self.extract_content,
                  style='Accent.TButton').pack(side=tk.LEFT, padx=(10, 0))

    def setup_output_section(self, parent, row):
        """Setup output and progress section."""
        output_frame = ttk.LabelFrame(parent, text="Extraction Output", padding="10")
        output_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        # Progress bar
        self.progress = ttk.Progressbar(output_frame, mode='indeterminate')
        self.progress.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        # Output text area
        self.output_text = scrolledtext.ScrolledText(output_frame, height=10)
        self.output_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure parent row weight
        parent.rowconfigure(row, weight=1)

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

    def analyze_pdf(self):
        """Analyze the PDF and populate content selection options."""
        if not self.pdf_path.get():
            messagebox.showerror("Error", "Please select a PDF file first.")
            return

        try:
            self.log_output("Analyzing PDF...")
            self.progress.start()

            # Initialize extractor
            self.extractor = InteractivePDFExtractor(
                self.pdf_path.get(), 
                self.output_path.get()
            )

            # Get available content
            available = self.extractor.available_extractions

            # Populate content tabs
            self.populate_content_tab(self.figures_frame, available["figures"], self.figure_vars)
            self.populate_content_tab(self.algorithms_frame, available["algorithms"], self.algorithm_vars)
            self.populate_content_tab(self.tables_frame, available["tables"], self.table_vars)
            self.populate_content_tab(self.equations_frame, available["equations"], self.equation_vars)

            # Enable tabs
            for i in range(4):
                self.notebook.tab(i, state='normal')

            self.progress.stop()
            self.log_output("PDF analysis complete. Select content to extract.")

        except Exception as e:
            self.progress.stop()
            messagebox.showerror("Error", f"Failed to analyze PDF: {e}")
            self.log_output(f"Error: {e}")

    def populate_content_tab(self, frame, items, var_dict):
        """Populate a content tab with checkboxes."""
        # Clear existing widgets
        for widget in frame.winfo_children():
            widget.destroy()

        var_dict.clear()

        if not items:
            ttk.Label(frame, text="No items found in this category").pack(pady=20)
            return

        # Add select all/none buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(button_frame, text="Select All", 
                  command=lambda: self.toggle_all(var_dict, True)).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Select None", 
                  command=lambda: self.toggle_all(var_dict, False)).pack(side=tk.LEFT, padx=(5, 0))

        # Add checkboxes for each item
        for i, item in enumerate(items):
            var = tk.BooleanVar()
            var_dict[item] = var

            cb = ttk.Checkbutton(frame, text=item, variable=var)
            cb.pack(anchor=tk.W, pady=2)

    def toggle_all(self, var_dict, state):
        """Toggle all checkboxes in a category."""
        for var in var_dict.values():
            var.set(state)

    def select_all(self):
        """Select all items across all categories."""
        for var_dict in [self.figure_vars, self.algorithm_vars, self.table_vars, self.equation_vars]:
            self.toggle_all(var_dict, True)

    def clear_all(self):
        """Clear all selections across all categories."""
        for var_dict in [self.figure_vars, self.algorithm_vars, self.table_vars, self.equation_vars]:
            self.toggle_all(var_dict, False)

    def get_selections(self):
        """Get current user selections."""
        return {
            "figures": [item for item, var in self.figure_vars.items() if var.get()],
            "algorithms": [item for item, var in self.algorithm_vars.items() if var.get()],
            "tables": [item for item, var in self.table_vars.items() if var.get()],
            "equations": [item for item, var in self.equation_vars.items() if var.get()],
            "custom": []
        }

    def extract_content(self):
        """Extract selected content."""
        if not self.extractor:
            messagebox.showerror("Error", "Please analyze PDF first.")
            return

        selections = self.get_selections()
        total_selected = sum(len(items) for items in selections.values())

        if total_selected == 0:
            messagebox.showwarning("Warning", "No content selected for extraction.")
            return

        # Confirm extraction
        if not messagebox.askyesno("Confirm Extraction", 
                                  f"Extract {total_selected} items?"):
            return

        # Run extraction in separate thread to avoid UI freezing
        self.progress.start()
        self.log_output(f"Starting extraction of {total_selected} items...")

        thread = threading.Thread(target=self.run_extraction, args=(selections,))
        thread.daemon = True
        thread.start()

    def run_extraction(self, selections):
        """Run the extraction process."""
        try:
            results = self.extractor.extract_selected_content(selections)
            summary_path = self.extractor.save_extraction_summary(results)

            # Update UI in main thread
            self.root.after(0, self.extraction_complete, results, summary_path)

        except Exception as e:
            self.root.after(0, self.extraction_error, str(e))

    def extraction_complete(self, results, summary_path):
        """Handle extraction completion."""
        self.progress.stop()

        total_extracted = results["metadata"]["extraction_summary"]["total_items"]

        self.log_output(f"\n✅ Extraction completed successfully!")
        self.log_output(f"📊 Total items extracted: {total_extracted}")
        self.log_output(f"📁 Output directory: {self.output_path.get()}")
        self.log_output(f"📄 Summary: {summary_path}")

        messagebox.showinfo("Success", 
                           f"Extraction completed!\n\n"
                           f"Items extracted: {total_extracted}\n"
                           f"Output: {self.output_path.get()}")

    def extraction_error(self, error_msg):
        """Handle extraction error."""
        self.progress.stop()
        self.log_output(f"❌ Extraction failed: {error_msg}")
        messagebox.showerror("Extraction Failed", error_msg)

    def log_output(self, message):
        """Add message to output log."""
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)


def main():
    """Main function to run the GUI application."""
    root = tk.Tk()
    app = PDFExtractorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
