
import os
import json
import shutil

# --- Configuration ---
FINAL_JSON_DIR = "final_pdf_json_outputs/"
# For this script, we'll look in the folder with the original PDFs, not the corrected ones.
# This way, the user gets the untouched original for their manual review.
SOURCE_PDF_DIR = "source_pdfs/"
REVIEW_DIR = "manual_review_needed/"

if __name__ == "__main__":
    print("--- Starting QC Check and PDF Flagging ---")

    os.makedirs(REVIEW_DIR, exist_ok=True)
    
    flagged_count = 0
    total_count = 0

    # Make sure the input directory exists before trying to read it
    if not os.path.isdir(FINAL_JSON_DIR):
        print(f"--- ❗️ ERROR: The directory '{FINAL_JSON_DIR}' was not found. ---")
        print("Please run '2_convert_to_final_json.py' first to generate the final JSON files.")
        exit()

    for filename in os.listdir(FINAL_JSON_DIR):
        if not filename.endswith('.json'):
            continue
        
        total_count += 1
        file_path = os.path.join(FINAL_JSON_DIR, filename)

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            if data.get('_qc_flag') is True:
                flagged_count += 1
                reason = data.get('_qc_reason', 'No reason specified.')
                print(f"  - 🚩 FLAGGED: {filename} | Reason: {reason}")

                doc_id = filename.replace('.json', '')
                # We now look directly in the source folder, not in a subfolder.
                original_pdf_path = os.path.join(SOURCE_PDF_DIR, f"{doc_id}.pdf")
                destination_path = os.path.join(REVIEW_DIR, f"{doc_id}.pdf")

                if os.path.exists(original_pdf_path):
                    # Use shutil.move to move the file
                    shutil.move(original_pdf_path, destination_path)
                    print(f"    - Moved '{doc_id}.pdf' to '{REVIEW_DIR}'")
                else:
                    print(f"    - ❗️ WARNING: Could not find original PDF to move at '{original_pdf_path}'")
        
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  - ❗️ ERROR reading {filename}: {e}. Skipping.")

    print("\n--- QC Check Complete ---")
    print(f"Processed {total_count} files.")
    print(f"Flagged {flagged_count} document(s) for manual review.")