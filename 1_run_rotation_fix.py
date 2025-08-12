import os
import shutil
import ocrmypdf

# --- Configuration ---
SOURCE_DIR = "source_pdfs/"
CORRECTED_DIR = "corrected_pdfs/"

def correct_pdf_rotations(source_path, output_path):
    print(f"  - Attempting to correct: {os.path.basename(source_path)}")
    try:
        ocrmypdf.ocr(
            source_path, output_path,
            deskew=True, rotate_pages=True, clean=True,
            force_ocr=True
        )
        print(f"  - ✅ Successfully corrected and saved: {os.path.basename(output_path)}")
        return True
    except Exception as e:
        print(f"  - ❗️ WARNING: Failed to correct {os.path.basename(source_path)}. Reason: {e}")
        return False

if __name__ == "__main__":
    print("--- Starting PDF Rotation Correction & Triage ---")
    os.makedirs(CORRECTED_DIR, exist_ok=True)

    pdf_files = []
    for root, dirs, files in os.walk(SOURCE_DIR):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))

    if not pdf_files:
        print(f"No PDFs found in '{SOURCE_DIR}'.")
    else:
        print(f"Found {len(pdf_files)} PDFs to process.")
        for source_pdf_path in pdf_files:
            # We will create a flat structure in the corrected folder
            output_pdf_path = os.path.join(CORRECTED_DIR, os.path.basename(source_pdf_path))
                        
            # Attempt the correction
            success = correct_pdf_rotations(source_pdf_path, output_pdf_path)
            
            # If correction fails, copy the original file over as a fallback.
            if not success:
                print(f"  - Fallback: Copying original corrupted file to '{CORRECTED_DIR}'")
                shutil.copy(source_pdf_path, output_pdf_path)
                print(f"  - ✅ Copied original: {os.path.basename(output_pdf_path)}")

    print("\n--- PDF Correction & Triage Complete ---")
    print(f"The '{CORRECTED_DIR}' folder now contains all {len(pdf_files)} documents, ready for the next step.")