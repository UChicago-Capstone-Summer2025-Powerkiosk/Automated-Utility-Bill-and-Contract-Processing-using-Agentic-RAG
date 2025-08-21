import os
from agentic_doc.parse import parse

# --- Configuration for FULL RUN ---
PDF_SOURCE_DIR = "corrected_pdfs/"
MARKDOWN_OUTPUT_DIR = "final_markdown_outputs/"

if __name__ == "__main__":
    print("--- Starting FULL Markdown Conversion Pipeline ---")

    if 'VISION_AGENT_API_KEY' not in os.environ:
        print("\n--- ERROR: VISION_AGENT_API_KEY not set ---")
        exit()

    os.makedirs(MARKDOWN_OUTPUT_DIR, exist_ok=True)

    pdf_files = []
    for root, dirs, files in os.walk(PDF_SOURCE_DIR):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))

    if not pdf_files:
        print(f"No corrected PDFs found in '{PDF_SOURCE_DIR}'. Did you run '1_run_rotation_fix.py' first?")
    else:
        print(f"Found {len(pdf_files)} corrected PDF(s) to process.")
        
        try:
            print("\nProcessing all documents with agentic-doc... This will take a significant amount of time.")
            results = parse(pdf_files)
            print("Processing complete. Now saving markdown files...")

            for source_path, parsed_doc in zip(pdf_files, results):
                base_name = os.path.splitext(os.path.basename(source_path))[0]
                output_md_path = os.path.join(MARKDOWN_OUTPUT_DIR, f"{base_name}.md")

                print(f"  - Saving result for: '{os.path.basename(source_path)}'")
                markdown_content = parsed_doc.markdown
                
                with open(output_md_path, "w", encoding="utf-8") as f:
                    f.write(markdown_content)
                
                print(f"  ✅ Successfully saved to '{output_md_path}'")

        except Exception as e:
            print(f"  --- ❌ An unexpected error occurred during processing ---")
            print(f"  Error: {e}")

    print("\n--- FULL Markdown Conversion Complete ---")