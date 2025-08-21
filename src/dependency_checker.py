import importlib
import subprocess
import sys
from typing import Optional

# List of required packages:
# REQUIRED_PACKAGES can contain:
# - (pip_name, module_name)                            -> import module_name
# - (pip_name, module_name, symbol_or_dict)            -> from module_name import symbol(s)
#    symbol_or_dict can be:
#       - str: single symbol to import (optional alias is same string)
#       - dict: {symbol: alias or None} for multiple imports
REQUIRED_PACKAGES = [
    ("pandas", "pandas"),
    ("scikit-learn", "sklearn"),
    ("numpy", "numpy"),
    ("matplotlib", "matplotlib"),
    ("seaborn", "seaborn"),
    # Example with multiple symbol imports and aliases:
    ("collections", {"Counter": "MyCounter", "defaultdict": "dd", "OrderedDict": None}),
]

def check_dependencies(
    auto_install: bool = False,
    strict: bool = True,
    quiet: bool = False
) -> None:
    """
    Check if required packages are installed.
    Optionally auto-install missing packages.
    Exit if missing packages found and strict=True.
    """

    missing = []

    # Helper function to conditionally print output
    def print_if_verbose(*args, **kwargs) -> None:
        if not quiet:
            print(*args, **kwargs)

    # Iterate through each package
    for pip_name, module_name in [(pkg[0], pkg[1]) for pkg in REQUIRED_PACKAGES]:
        try:
            # Try importing the module
            importlib.import_module(module_name)
            print_if_verbose(f"✅ {pip_name} is installed.")
        except ImportError:
            # Package missing
            print(f"❌ {pip_name} is missing.")
            if auto_install:
                print_if_verbose(f"⬇️ Installing {pip_name}...")
                try:
                    # Try to install using pip
                    subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
                    # Try import again after install
                    importlib.import_module(module_name)
                    print_if_verbose(f"✅ {pip_name} installed successfully.")
                except Exception as e:
                    print(f"❌ Failed to install or import {pip_name}: {e}")
                    missing.append(pip_name)
            else:
                missing.append(pip_name)

    # If still missing packages and strict mode enabled, exit program
    if missing and strict:
        print("\n🚫 Missing packages and auto_install=False. Cannot continue:")
        for pkg in missing:
            print(f"   - {pkg}")
        sys.exit(1)
