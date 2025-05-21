import shutil
from pathlib import Path
import sys
import zipfile
import subprocess
import platform

def check_tools():
    def check_tool(tool_name):
        return shutil.which(tool_name) is not None

    if not check_tool("unzip"):
        print("❌ 'unzip' is not installed. Please install it first.")
        sys.exit(1)

    if not check_tool("7z"):
        print("❌ '7z' (from p7zip) is not installed.")
        os_type = platform.system().lower()
        if os_type == "linux":
            print("👉 Install it with: sudo apt install p7zip-full")
        elif os_type == "darwin":
            print("👉 Install it with: brew install p7zip")
        elif os_type == "windows":
            print("👉 Download and install 7-Zip from: https://www.7-zip.org/")
        else:
            print("👉 Please install '7z' according to your OS.")
        sys.exit(1)

    print("✅ All required tools are available.")

def resolve_relative_path(path, base_dir=None):
    """
    Resolve `path` relative to `base_dir` (default: script directory).
    Returns absolute Path.
    """
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent
    path = Path(path)
    if path.is_absolute():
        return path
    else:
        return (base_dir / path).resolve()
    
def create_folders(folders):
    # Allow single folder (Path or str) or list of them
    if not isinstance(folders, (list, tuple)):
        folders = [folders]

    for folder in folders:
        folder_path = resolve_relative_path(folder)
        if not folder_path.exists():
            folder_path.mkdir(parents=True, exist_ok=True)
            print(f"Created folder: {folder_path}")
        else:
            print(f"Folder already exists: {folder_path}")

def extract_archives(archives, dest_dirs):
    # Allow single archive or list
    if not isinstance(archives, (list, tuple)):
        archives = [archives]
    if not isinstance(dest_dirs, (list, tuple)):
        dest_dirs = [dest_dirs]

    # If only one dest_dir but multiple archives, replicate dest_dir
    if len(dest_dirs) == 1 and len(archives) > 1:
        dest_dirs = dest_dirs * len(archives)

    for archive, dest in zip(archives, dest_dirs):
        archive_path = resolve_relative_path(archive)
        dest_path = resolve_relative_path(dest)

        if not archive_path.exists():
            print(f"❌ Archive not found: {archive_path}")
            continue

        dest_path.mkdir(parents=True, exist_ok=True)

        if archive_path.suffix == ".zip":
            print(f"Unzipping {archive_path} to {dest_path}")
            try:
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(dest_path)
            except zipfile.BadZipFile:
                print(f"❌ Bad zip file: {archive_path}")
        elif archive_path.suffix == ".7z":
            print(f"Extracting {archive_path} to {dest_path}")
            result = subprocess.run(["7z"], capture_output=True)
            if result.returncode != 0:
                print("❌ 7z command not found. Please install p7zip or 7-Zip and add to PATH.")
                sys.exit(1)
            subprocess.run(["7z", "x", str(archive_path), f"-o{str(dest_path)}", "-y"], check=True)
        else:
            print(f"Unsupported archive format: {archive}")

def move_files(source_folder, destination_folder, pattern="*"):
    source_path = resolve_relative_path(source_folder)
    destination_path = resolve_relative_path(destination_folder)
    if not source_path.is_dir():
        print(f"Source folder {source_path} does not exist!")
        return
    destination_path.mkdir(parents=True, exist_ok=True)

    files = list(source_path.glob(pattern))
    if not files:
        print(f"No files matching '{pattern}' found in {source_path}")
        return

    for f in files:
        try:
            shutil.move(str(f), str(destination_path))
        except Exception as e:
            print(f"Failed to move {f}: {e}")
    print(f"Moved files from {source_path} to {destination_path}")

def move_all(source_folder, destination_folder):
    """Move everything (files and folders) using move_files with '*' pattern."""
    move_files(source_folder, destination_folder, pattern="*")
            

def main():
    # Folders to create
    folders = ["../data", "../docs", "../samples",]
    create_folders(folders)

    # List of archives and corresponding extraction folders
    archives = [
        "../artifacts/UsageExtractionDocuments.zip" ,
        "../artifacts/downloaded_pdfs.zip",
        "../artifacts/outputs.7z",
        "../artifacts/mist_outputs.7z",
    ]

    dest_dirs = [
        "../artifacts/",
        "../artifacts/downloaded_pdfs",
        "../artifacts/",
        "../artifacts/",
    ]

    extract_archives(archives, dest_dirs)

    # Move files, paths relative to script location
    # UsageExtractionDocuments
    move_files("../artifacts/UsageExtractionDocuments/", "../samples/raw_samples", "*.pdf")
    move_files("../artifacts/UsageExtractionDocuments/", "../docs/", "*.docx")
    move_files("../artifacts/UsageExtractionDocuments/", "../schema", "*.xlsx")

    # downloaded_pdfs
    move_files("../artifacts/downloaded_pdfs/content/downloaded_pdfs", "../data/raw_data", "*.pdf")

    # outputs (move all files/folders)
    move_all("../artifacts/outputs", "../samples/ocr_results_samples")

    # mist_outputs (move all files/folders)
    move_all("../artifacts/mist_outputs", "../data/ocr_results_outputs")
    
    
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check-tools":
        check_tools()
        sys.exit(0)
    else:
        check_tools()
        main()