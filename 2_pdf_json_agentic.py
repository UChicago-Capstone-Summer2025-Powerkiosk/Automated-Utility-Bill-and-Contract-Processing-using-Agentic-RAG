import os
import json
from agentic_doc.parse import parse

# Configuration
PDF_SOURCE_DIR = "corrected_pdfs/"
GENERIC_JSON_OUTPUT_DIR = "generic_json_outputs/"

if __name__ == "__main__":
    print("--- Starting PDF-to-Generic-JSON Pilot (Upgraded Method) ---")

    if 'VISION_AGENT_API_KEY' not in os.environ:
        print("\n--- ERROR: VISION_AGENT_API_KEY environment variable is not set. ---")
        exit()

    os.makedirs(GENERIC_JSON_OUTPUT_DIR, exist_ok=True)

    pdf_files = [os.path.join(PDF_SOURCE_DIR, f) for f in os.listdir(PDF_SOURCE_DIR) if f.lower().endswith('.pdf')]

    if not pdf_files:
        print(f"No PDF files found in '{PDF_SOURCE_DIR}'.")
    else:
        print(f"Found {len(pdf_files)} PDF(s) to process.")
        
        try:
            print("\nProcessing documents with settings to maximize data clarity...")
            
            # --- THE UPGRADE IS HERE ---
            results = parse(
                pdf_files,
                include_marginalia=False,
                include_metadata_in_markdown=False
            )
            # --- END OF UPGRADE ---

            print("Processing complete. Now saving generic JSON files...")

            for source_path, parsed_doc in zip(pdf_files, results):
                base_name = os.path.splitext(os.path.basename(source_path))[0]
                output_json_path = os.path.join(GENERIC_JSON_OUTPUT_DIR, f"{base_name}.json")

                print(f"  - Saving generic JSON for: '{os.path.basename(source_path)}'")
                chunks_data = [chunk.dict() for chunk in parsed_doc.chunks]
                
                with open(output_json_path, "w", encoding="utf-8") as f:
                    json.dump(chunks_data, f, indent=2)
                
                print(f"  ✅ Successfully saved to '{output_json_path}'")

        except Exception as e:
            print(f"  --- ❌ An unexpected error occurred ---")
            print(f"  Error: {e}")

    print("\n--- Pilot Run Complete ---")