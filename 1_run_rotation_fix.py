import os
import ocrmypdf
import shutil

SOURCE_DIR = "all_pdfs/"
CORRECTED_DIR = "corrected_pdfs/"

def correct_pdf_rotations(source_path, output_path):
    print(f"  - Checking and correcting rotation for: {os.path.basename(source_path)}")
    try:
        ocrmypdf.ocr(
            source_path, output_path,
            deskew=True, rotate_pages=True, clean=True,
            tesseract_timeout=0, force_ocr=False
        )
        print(f"  - Saved corrected file to: {os.path.basename(output_path)}")
        return True
    except Exception as e:
        print(f"  --- ERROR correcting {os.path.basename(source_path)}: {e} ---")
        return False

if __name__ == "__main__":
    print("--- Starting FULL PDF Rotation Correction Pipeline ---")
    os.makedirs(CORRECTED_DIR, exist_ok=True)

    pdf_files = []
    for root, dirs, files in os.walk(SOURCE_DIR):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))

    if not pdf_files:
        print("No PDFs found in 'all_pdfs/'. Please copy the full dataset.")
    else:
        print(f"Found {len(pdf_files)} PDFs to process.")
        for source_pdf_path in pdf_files:
            relative_path = os.path.relpath(os.path.dirname(source_pdf_path), SOURCE_DIR)
            output_dir = os.path.join(CORRECTED_DIR, relative_path)
            os.makedirs(output_dir, exist_ok=True)
            output_pdf_path = os.path.join(output_dir, os.path.basename(source_pdf_path))
            
            if os.path.exists(output_pdf_path):
                print(f"Skipping '{os.path.basename(source_pdf_path)}', corrected version already exists.")
                continue

            correct_pdf_rotations(source_pdf_path, output_pdf_path)

    print("\n--- FULL PDF Rotation Correction Complete ---")