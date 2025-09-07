# Let's create a demo of the interactive extractor
print("🎯 DEMO: Interactive PDF Content Extractor")
print("=" * 60)

# Simulate the interactive extractor with the assignment PDF
from interactive_extractor import InteractivePDFExtractor

# Initialize the extractor
extractor = InteractivePDFExtractor("Assignment-PDF.pdf", "interactive_output")

# Display available content
extractor.display_available_content()

print("\\n" + "=" * 60)
print("SIMULATED USER INTERACTION")
print("=" * 60)

# Simulate user selecting specific items
print("\\nUser selects:")
print("📊 Figures: 1, 2, 3 (keyframe comparison, framework, adaptive sampling)")
print("🤖 Algorithms: 1 (ADA algorithm)")
print("📋 Tables: 1, 2 (accuracy comparison, sampling strategies)")

# Create simulated selections
simulated_selections = {
    "figures": [
        "Figure 1 - Keyframe sampling comparison (Page 1)",
        "Figure 2 - Overall framework (Page 3)",
        "Figure 3 - Adaptive sampling example (Page 4)"
    ],
    "algorithms": [
        "Algorithm 1 - ADA: Adaptive Keyframe Selection (Page 11)"
    ],
    "tables": [
        "Table 1 - Video-based QA accuracy (Page 5)",
        "Table 2 - Different sampling strategies (Page 6)"
    ],
    "equations": [],
    "custom": []
}

print("\\nExtracting selected content...")
results = extractor.extract_selected_content(simulated_selections)

# Save summary
summary_path = extractor.save_extraction_summary(results)

print("\\n" + "=" * 60)
print("EXTRACTION RESULTS")
print("=" * 60)

total_extracted = results["metadata"]["extraction_summary"]["total_items"]
print(f"✅ Total items extracted: {total_extracted}")
print(f"📊 Figures: {len(results['figures'])}")
print(f"🤖 Algorithms: {len(results['algorithms'])}")
print(f"📋 Tables: {len(results['tables'])}")
print(f"🧮 Equations: {len(results['equations'])}")
print(f"📁 Output directory: interactive_output")
print(f"📄 Summary saved to: {summary_path}")

print("\\n" + "=" * 60)
print("DETAILED EXTRACTION RESULTS")
print("=" * 60)

# Show detailed results for figures
if results["figures"]:
    print("\\n📊 EXTRACTED FIGURES:")
    for figure in results["figures"]:
        print(f"  • Figure {figure['figure_number']}: {figure['title']}")
        print(f"    Page: {figure['page']} | Caption: {figure['caption'][:60]}...")

# Show detailed results for algorithms  
if results["algorithms"]:
    print("\\n🤖 EXTRACTED ALGORITHMS:")
    for algo in results["algorithms"]:
        print(f"  • {algo['algorithm_name']}")
        print(f"    Page: {algo['page']} | Steps: {len(algo['algorithm_steps'])}")

# Show detailed results for tables
if results["tables"]:
    print("\\n📋 EXTRACTED TABLES:")
    for table in results["tables"]:
        print(f"  • Table {table['table_number']}: {table['title']}")
        print(f"    Columns: {len(table['columns'])} | Key findings: {len(table['key_findings'])}")

print("\\n" + "=" * 60)
print("USER SELECTION CAPABILITIES DEMONSTRATED")
print("=" * 60)