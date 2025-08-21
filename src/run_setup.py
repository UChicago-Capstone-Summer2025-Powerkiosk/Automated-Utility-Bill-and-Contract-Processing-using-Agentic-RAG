import argparse
from dependency_checker import check_dependencies
from dynamic_importer import import_all_dependencies

def run_dependency_setup() -> None:
    """
    CLI entry point for checking and installing packages,
    then dynamically importing symbols as configured.
    """

    parser = argparse.ArgumentParser(description="Check and optionally install required Python packages.")
    parser.add_argument(
        "--auto-install",
        action="store_true",
        help="Automatically install missing packages using pip."
    )
    parser.add_argument(
        "--no-strict",
        action="store_true",
        help="Do not exit if packages are missing (continue even if missing)."
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed output."
    )
    args = parser.parse_args()

    # Run dependency check and installation
    check_dependencies(auto_install=args.auto_install, strict=not args.no_strict, quiet=args.quiet)
    # Dynamically import required modules and symbols
    import_all_dependencies()

if __name__ == "__main__":
    run_dependency_setup()
