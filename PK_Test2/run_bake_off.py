# In run_bake_off.py (Final Version with Transformation Step)

import json
import os
from pathlib import Path

# --- Core Extraction Imports (from their code) ---
from extraction_utils import agg_extract_service_entries, extract_bill_info, clean_account_numbers
from usage_utils import estimate_monthly_usage, merge_and_flatten_service_entries, flatten_all_service_entries
from month_utils import month_map

# --- The CRITICAL New Import for Transformation ---
from to_final_bill import create_final_bill_result 

# --- Configuration ---
MARKDOWN_PATH = "input_data/document_1124.md"
OUTPUT_PATH = "bake_off_output_FINAL.json" # New output file name
ISSUER = "NATIONAL_GRID"

if __name__ == "__main__":
    print(f"--- Starting Full Bake-Off for {MARKDOWN_PATH} ---")

    if 'OPENAI_API_KEY' not in os.environ:
        print("FATAL ERROR: OPENAI_API_KEY environment variable not set.")
        exit()

    try:
        with open(MARKDOWN_PATH, 'r') as f:
            md_content = f.read()
        print("  - Loaded our high-quality Markdown.")

        # --- STAGE 1: RUNNING THEIR RAW EXTRACTION LOGIC ---
        
        intermediate_result = {}
        meter_type = "electricity" 
        
        print(f"\n=== STAGE 1: Performing Raw Extraction ===")
        
        service_entries = agg_extract_service_entries(
            file_path=Path(MARKDOWN_PATH),
            md_content=md_content,
            meter_type=meter_type,
            issuer=ISSUER
        )
        
        if "Pass" not in service_entries:
            bill_info = extract_bill_info(md_content, meter_type, issuer=ISSUER)
            bill_info["service_entries"] = service_entries
            clean_account_numbers(bill_info)
            stmt = bill_info.get("statement_date", {})
            stmt_month = month_map.get(stmt.get("month"))
            stmt_year = str(stmt.get("year"))
            
            bill_info["service_entries"] = estimate_monthly_usage(
                bill_dir=Path(MARKDOWN_PATH).parent,
                service_entries=service_entries,
                statement_month=stmt_month,
                statement_year=stmt_year
            )

            merged = merge_and_flatten_service_entries(bill_info["service_entries"])
            bill_info["service_entries"] = merged
            intermediate_result[meter_type] = flatten_all_service_entries(bill_info)
        
        # Add the filename and issuer, which their transformer needs
        intermediate_result['filename'] = Path(MARKDOWN_PATH).stem
        intermediate_result['issuer'] = ISSUER
        print("  - Stage 1 Complete. Intermediate JSON created.")

        # --- STAGE 2: RUNNING THEIR TRANSFORMATION LOGIC ---
        
        print("\n=== STAGE 2: Transforming to Final Bill Format ===")
        
        # This function takes the messy object and returns the clean one.
        # We're interested in the 'electricity' part of the result.
        final_output_dict = create_final_bill_result(ISSUER, "bake_off_test", intermediate_result)
        final_json = final_output_dict.get("electricity") # Get the final electricity bill

        if not final_json:
            raise ValueError("Transformation step did not produce a final 'electricity' bill object.")

        # --- SAVE THE FINAL RESULT ---
        with open(OUTPUT_PATH, 'w') as f:
            json.dump(final_json, f, indent=2)
            
        print(f"\n  ✅ Bake-Off successful! Final output saved to '{OUTPUT_PATH}'")

    except Exception as e:
        import traceback
        print(f"\n--- ❌ An error occurred ---")
        print(f"  Error Type: {type(e).__name__}")
        traceback.print_exc()

    print("\n--- Full Bake-Off Complete ---")