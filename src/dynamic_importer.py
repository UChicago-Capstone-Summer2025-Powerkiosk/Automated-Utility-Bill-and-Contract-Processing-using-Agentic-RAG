import importlib
from typing import Dict, Optional, Any
from dependency_checker import REQUIRED_PACKAGES

def dynamic_multi_from_import_as(
    module_name: str,
    symbol_alias_map: Dict[str, Optional[str]],
    namespace: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Dynamically import multiple symbols from a module.
    Each symbol can have an alias or keep original name if alias is None.
    Inject imported symbols into provided namespace (default: globals).
    Returns a dictionary mapping alias -> imported symbol or None if failed.
    """

    results: Dict[str, Any] = {}
    target_ns = namespace if namespace is not None else globals()

    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        print(f"❌ Error importing module '{module_name}': {e}")
        return results

    for symbol_name, alias_name in symbol_alias_map.items():
        try:
            symbol = getattr(module, symbol_name)
            alias = alias_name or symbol_name
            target_ns[alias] = symbol
            results[alias] = symbol
        except AttributeError as e:
            print(f"❌ Symbol '{symbol_name}' not found in module '{module_name}': {e}")
            results[alias_name or symbol_name] = None

    return results

def import_all_dependencies(namespace: Optional[Dict[str, Any]] = None) -> None:
    """
    For all REQUIRED_PACKAGES:
    - Import whole module if no specific symbols required.
    - Otherwise, dynamically import specified symbols with optional aliases.
    Inject imports into provided namespace (default: globals).
    """

    target_ns = namespace if namespace is not None else globals()

    for pkg in REQUIRED_PACKAGES:
        module_name = pkg[1]
        symbol_or_dict = pkg[2] if len(pkg) > 2 else None

        if symbol_or_dict is None:
            # Import entire module
            mod = importlib.import_module(module_name)
            target_ns[module_name] = mod
        elif isinstance(symbol_or_dict, str):
            # Single symbol import without alias
            dynamic_multi_from_import_as(module_name, {symbol_or_dict: None}, namespace=target_ns)
        elif isinstance(symbol_or_dict, dict):
            # Multiple symbols with aliases import
            dynamic_multi_from_import_as(module_name, symbol_or_dict, namespace=target_ns)
        else:
            print(f"❌ Unexpected symbol format in REQUIRED_PACKAGES: {symbol_or_dict}")
