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

def create_folders(folders):
    # Allow single folder (Path or str) or list of them
    if not isinstance(folders, (list, tuple)):
        folders = [folders]

    for folder in folders:
        folder = Path(folder).resolve()
        if not folder.exists():
            folder.mkdir(parents=True)
            print(f"Created folder: {folder}")
        else:
            print(f"Folder already exists: {folder}")

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
        archive = Path(archive).resolve()
        dest = Path(dest).resolve()

        if not archive.exists():
            print(f"❌ Archive not found: {archive}")
            continue

        dest.mkdir(parents=True, exist_ok=True)

        if archive.suffix == ".zip":
            print(f"Unzipping {archive} to {dest}")
            try:
                with zipfile.ZipFile(archive, 'r') as zip_ref:
                    zip_ref.extractall(dest)
            except zipfile.BadZipFile:
                print(f"❌ Bad zip file: {archive}")
        elif archive.suffix == ".7z":
            print(f"Extracting {archive} to {dest}")
            result = subprocess.run(["7z"], capture_output=True)
            if result.returncode != 0:
                print("❌ 7z command not found. Please install p7zip or 7-Zip and add to PATH.")
                sys.exit(1)
            subprocess.run(["7z", "x", str(archive), f"-o{str(dest)}", "-y"], check=True)
        else:
            print(f"Unsupported archive format: {archive}")

def move_files(source_folder, destination_folder, pattern="*"):
    source = Path(source_folder).resolve()
    dest = Path(destination_folder).resolve()
    if not source.is_dir():
        print(f"Source folder {source} does not exist!")
        return
    dest.mkdir(parents=True, exist_ok=True)

    files = list(source.glob(pattern))
    if not files:
        print(f"No files matching '{pattern}' found in {source}")
        return

    for f in files:
        try:
            shutil.move(str(f), str(dest))
        except Exception as e:
            print(f"Failed to move {f}: {e}")
    print(f"Moved files from {source} to {dest}")

def move_all(source_folder, destination_folder):
    source = Path(source_folder).resolve()
    dest = Path(destination_folder).resolve()
    if not source.is_dir():
        print(f"Source folder {source} does not exist!")
        return
    dest.mkdir(parents=True, exist_ok=True)

    items = list(source.iterdir())
    if not items:
        print(f"No items found in {source}")
        return

    for item in items:
        try:
            shutil.move(str(item), str(dest))
        except Exception as e:
            print(f"Failed to move {item}: {e}")
    print(f"Moved files/folders from {source} to {dest}")

def main():
    script_dir = Path(__file__).resolve().parent

    # Folders to create
    folders = [
        script_dir / "../data",
        script_dir / "../docs",
        script_dir / "../samples",
    ]
    create_folders(folders)

    # List of archives and corresponding extraction folders (relative to script_dir)
    archives = [
        script_dir / "../artifacts/UsageExtractionDocuments.zip" ,
        script_dir / "../artifacts/downloaded_pdfs.zip",
        script_dir / "../artifacts/outputs.7z",
        script_dir / "../artifacts/mist_outputs.7z",
    ]

    dest_dirs = [
        script_dir / "../artifacts/",
        script_dir / "../artifacts/downloaded_pdfs",
        script_dir / "../artifacts/",
        script_dir / "../artifacts/",
    ]

    extract_archives(archives, dest_dirs)

    # Move files, paths relative to script location
    # UsageExtractionDocuments
    move_files(script_dir / "../artifacts/UsageExtractionDocuments/", script_dir / "../samples/raw_samples", "*.pdf")
    move_files(script_dir / "../artifacts/UsageExtractionDocuments/", script_dir / "../docs/", "*.docx")
    move_files(script_dir / "../artifacts/UsageExtractionDocuments/", script_dir / "../schema", "*.xlsx")

    # downloaded_pdfs
    move_files(script_dir / "../artifacts/downloaded_pdfs/content/downloaded_pdfs", script_dir / "../data/raw_data", "*.pdf")

    # outputs (move all files/folders)
    move_all(script_dir / "../artifacts/outputs", script_dir / "../samples/ocr_results_samples")

    # mist_outputs (move all files/folders)
    move_all(script_dir / "../artifacts/mist_outputs", script_dir / "../data/ocr_results_outputs")
    
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check-tools":
        check_tools()
        sys.exit(0)
    else:
        check_tools()
        main()