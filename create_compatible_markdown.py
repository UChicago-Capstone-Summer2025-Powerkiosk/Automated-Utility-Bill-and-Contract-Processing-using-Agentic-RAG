# In create_compatible_markdown.py

import os
from agentic_doc.parse import parse

# --- Configuration ---
PDF_SOURCE_DIR = "source_pdfs_test/"
COMPATIBLE_MD_OUTPUT_DIR = "compatible_markdown_outputs/"

if __name__ == "__main__":
    print("--- Creating 'Compatibility Mode' Markdown ---")

    if 'VISION_AGENT_API_KEY' not in os.environ:
        print("\n--- ERROR: VISION_AGENT_API_KEY not set ---")
        exit()

    os.makedirs(COMPATIBLE_MD_OUTPUT_DIR, exist_ok=True)

    pdf_files = [os.path.join(PDF_SOURCE_DIR, f) for f in os.listdir(PDF_SOURCE_DIR) if f.lower().endswith('.pdf')]

    if not pdf_files:
        print(f"No PDF files found in '{PDF_SOURCE_DIR}'.")
    else:
        print(f"Found {len(pdf_files)} PDF(s) to process in compatibility mode.")
        
        try:
            print("\nProcessing documents with settings to maximize compatibility...")
            
            # These settings strip out extra analysis to produce a more literal transcription.
            results = parse(
                pdf_files,
                include_marginalia=False,          # Excludes headers/footers
                include_metadata_in_markdown=False # Excludes the <!-- comment --> tags
            )

            print("Processing complete. Saving compatible markdown files...")

            for source_path, parsed_doc in zip(pdf_files, results):
                base_name = os.path.splitext(os.path.basename(source_path))[0]
                output_md_path = os.path.join(COMPATIBLE_MD_OUTPUT_DIR, f"{base_name}.md")

                print(f"  - Saving compatible MD for: '{os.path.basename(source_path)}'")
                markdown_content = parsed_doc.markdown
                
                with open(output_md_path, "w", encoding="utf-8") as f:
                    f.write(markdown_content)
                
                print(f"  ✅ Successfully saved to '{output_md_path}'")

        except Exception as e:
            print(f"  --- ❌ An unexpected error occurred ---")
            print(f"  Error: {e}")

    print("\n--- Compatible Markdown creation complete ---")