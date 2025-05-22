import argparse
import sys
import logging
from setup_tools import (
    check_tools,
    create_folders,
    extract_archives,
    move_files,
    move_all,
    cleanup_subfolders,
    run_all
)

def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=level
    )

    
def main():
    parser = argparse.ArgumentParser(description="Setup utility script with optional commands.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    
    subparsers = parser.add_subparsers(dest="command", required=False)
    
    # Add subparser for 'create_folders'
    cf_parser = subparsers.add_parser('create_folders', help="Create folders")
    cf_parser.add_argument("--folders", nargs="+", default=["data", "docs", "samples"], help="List of folders to create")

    
    ea_parser = subparsers.add_parser("extract_archives", help="Extract archives")
    ea_parser.add_argument("--archives", 
                           nargs="+", 
                           required=False, 
                           default=[
                               "../artifacts/UsageExtractionDocuments.zip" ,
                               "../artifacts/downloaded_pdfs.zip",
                               "../artifacts/outputs.7z",
                               "../artifacts/mist_outputs.7z",
                           ], 
                           help="List of archives to extract (zip or 7z)")
    ea_parser.add_argument("--dest_dirs", 
                           nargs="+", 
                           required=False,
                           default=[
                               "../artifacts/",
                               "../artifacts/downloaded_pdfs",
                               "../artifacts/",
                               "../artifacts/",
                           ],
                           help="List of destination directories")

    mf_parser = subparsers.add_parser("move_files", help="Move files matching pattern")
    mf_parser.add_argument("--source", 
                           required=False, 
                           default="../artifacts/UsageExtractionDocuments/", 
                           help="Source folder")
    mf_parser.add_argument("--dest", 
                           required=False, 
                           default="../samples/raw_samples",
                           help="Destination folder")
    mf_parser.add_argument("--pattern", 
                           required=False,
                           default="*", 
                           help="File glob pattern")

    ma_parser = subparsers.add_parser("move_all", help="Move all files/folders from source to dest")
    ma_parser.add_argument("--source", 
                           required=False, 
                           default="../artifacts/outputs",
                           help="Source folder")
    ma_parser.add_argument("--dest", 
                           required=False, 
                           default="../samples/ocr_results_samples",
                           help="Destination folder")

    cl_parser = subparsers.add_parser("cleanup_subfolders", help="Remove folders")
    cl_parser.add_argument("--folders", 
                           nargs="+", 
                           required=False, 
                           default="../artifacts",
                           help="List of folders to remove")
    
    # Set a default command when none is specified
    parser.set_defaults(command='run_all', help="Run all steps with default parameters")  # default sub-command
    
    args = parser.parse_args()
    setup_logging(args.verbose)

    action_taken = False

    if args.command == "run_all" or len(sys.argv) == 1:
        print("No arguments passed — running default action...")
        run_all()
        action_taken = True
        return

    if args.command == "create_folders":
        if args.folders == []:
            create_folders(["data", "docs", "samples"])
        else:
            create_folders(args.folders)
        action_taken = True

    if args.command == "extract_archives":
        archives, dest_dirs = arg.archives, arg.dest_dirs
        if len(dest_dirs) != len(archives):
            print("Error: --dest_dirs must be same length as --archives")
            sys.exit(1)
        extract_archives(archives, dest_dirs)
        action_taken = True

    if args.command == "move_files":
        source, dest, pattern = args.source, args.dest, args.pattern
        move_files(source, dest, pattern)
        action_taken = True

    if args.command == "move_all":
        source, dest = args.source, args.dest
        move_all(source, dest)
        action_taken = True

    if args.command == "cleanup_subfolders":
        cleanup_subfolders(args.folders)
        action_taken = True
        
    # If no actions were triggered, show help
    if not action_taken:
        parser.print_help()

if __name__ == "__main__":
    # Check tools first
    if "--check-tools" in sys.argv:
        check_tools()
        sys.exit(0)
    else:
        check_tools()
        main()