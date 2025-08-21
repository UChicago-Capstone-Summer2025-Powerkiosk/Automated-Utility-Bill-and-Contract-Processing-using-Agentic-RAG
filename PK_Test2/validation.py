import json
from typing import Any, List
from pydantic import ValidationError, TypeAdapter
from utils import (
    fix_llm_json,
    normalize_null_strings,
    fix_with_llm,
    llm_fix_with_original_text,
    logger,
    fix_json_algo,
)

from models import LineCorrection


def get_validation(
    llm_raw: str,
    strict_adapter: TypeAdapter[Any],
    loose_adapter: TypeAdapter[Any],
    system_prompt: str,
    original_md: str,
) -> Any:
    """
    1) Parse & normalize JSON → strict_adapter.validate_python
    2) On failure → fix_with_llm → strict_adapter.validate_python
    3) On failure → llm_fix_with_original_text → loose_adapter.validate_python
    4) On ultimate failure → return raw dict
    """
    clean_json = None

    print("\n=== get_validation START ===")
    # print("System prompt:", system_prompt)
    print("Original LLM raw output:\n", llm_raw)

    # --- 1) Strict first pass ---
    try:
        clean_json = fix_llm_json(llm_raw)
        print("After fix_llm_json:\n", clean_json)

        if isinstance(clean_json, dict) and clean_json.get("Pass") == "Pass":
            print("Detected Pass response, returning as-is.")
            return clean_json

        clean_json = normalize_null_strings(clean_json)
        print("After normalize_null_strings:\n", clean_json)

        parsed = strict_adapter.validate_python(clean_json)
        print("✅ Strict validation succeeded.")
        print("Parsed object:", parsed)
        print("=== get_validation END (strict) ===\n")
        return parsed

    except (json.JSONDecodeError, ValidationError) as e1:
        print("❌ Strict validation failed with error:")
        print(e1)

        # --- 2) LLM-based fix_with_llm ---
        print("Attempting fix_with_llm fallback...")
        try:
            corrected = fix_with_llm(llm_raw, e1, strict_adapter)
            print("Output from fix_with_llm:\n", corrected)

            clean_json = fix_llm_json(corrected)
            print("After fix_llm_json(corrected):\n", clean_json)

            clean_json = normalize_null_strings(clean_json)
            print("After normalize_null_strings:\n", clean_json)

            parsed = strict_adapter.validate_python(clean_json)
            print("✅ fix_with_llm validation succeeded.")
            print("Parsed object:", parsed)
            print("=== get_validation END (fix_with_llm) ===\n")
            return parsed

        except Exception as e2:
            print("❌ fix_with_llm failed with error:")
            print(e2)

            # --- 3) LLM-based fallback with original text prompt ---
            print("Attempting llm_fix_with_original_text fallback...")
            try:
                fallback_fixed = llm_fix_with_original_text(
                    system_prompt,
                    original_md,
                    e2,
                    strict_adapter,
                )
                print("Output from llm_fix_with_original_text:\n", fallback_fixed)

                clean_json = fix_llm_json(fallback_fixed)
                print("After fix_llm_json(fallback_fixed):\n", clean_json)

                clean_json = normalize_null_strings(clean_json)
                print("After normalize_null_strings:\n", clean_json)

                parsed = loose_adapter.validate_python(clean_json)
                print("✅ llm_fix_with_original_text validation succeeded (loose).")
                print("Parsed (loose) object:", parsed)
                print("=== get_validation END (loose) ===\n")
                return parsed

            except Exception as e3:
                print("❌ llm_fix_with_original_text failed with error:")
                print(e3)

                # --- 4) Final fallback: give back whatever dict we have ---
                print("Final fallback: returning raw dict or JSON load.")
                if isinstance(clean_json, dict):
                    print("Returning last clean_json dict.")
                    return clean_json
                try:
                    raw_dict = json.loads(llm_raw or "{}")
                    print("JSON-loaded raw dict:", raw_dict)
                    return raw_dict
                except Exception as e4:
                    try:
                        raw_dict = fix_json_algo(llm_raw)
                        return raw_dict
                    except Exception as e5:
                        print("Failed to json.loads llm_raw:", e5)
                        print("Returning empty dict {}.")
                        return {}
