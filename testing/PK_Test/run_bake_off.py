import json
import os

# We are ly importing ONLY the functions we need
from extraction_utils import agg_extract_service_entries, extract_bill_info, clean_account_numbers
from usage_utils import estimate_monthly_usage, merge_and_flatten_service_entries, flatten_all_service_entries
from month_utils import month_map

# --- Configuration ---
MARKDOWN_PATH = "input_markdown/document_1124.md"
OUTPUT_PATH = "test_bake_off_result.json"
ISSUER = "NATIONAL_GRID"  # We have to provide this manually

if __name__ == "__main__":
    print(f"--- Starting  Bake-Off for {MARKDOWN_PATH} ---")

    try:
        with open(MARKDOWN_PATH, 'r') as f:
            md_content = f.read()
        print("  - Loaded our high-quality Markdown.")

        # --- Manually Replicating Their 'new_main.py' Logic ---

        # 1. Extract Service Entries (like meters, accounts)
        print("  - Step 1: Extracting service entries...")
        service_entries = agg_extract_service_entries(
            file_path=MARKDOWN_PATH,  # It needs a path, even if just for logging
            md_content=md_content,
            type="electricity",
            issuer=ISSUER
        )

        # 2. Extract Top-Level Bill Info
        print("  - Step 2: Extracting main bill info...")
        final_json = extract_bill_info(
            md_content=md_content,
            type="electricity",
            issuer=ISSUER
        )
        final_json["service_entries"] = service_entries

        # 3. Run their data cleaning and estimation functions
        print("  - Step 3: Running data cleaning and usage estimation...")
        clean_account_numbers(final_json)
        stmt_date = final_json.get("statement_date", {})
        stmt_month = month_map.get(stmt_date.get("month"))
        stmt_year = str(stmt_date.get("year"))
        
        final_json["service_entries"] = estimate_monthly_usage(
            bill_dir=None, # Not needed as we're not reading images
            service_entries=final_json["service_entries"],
            statement_month=stmt_month,
            statement_year=stmt_year
        )

        # 4. Merge and flatten the final structure
        print("  - Step 4: Merging and flattening results...")
        merged = merge_and_flatten_service_entries(final_json["service_entries"])
        final_json["service_entries"] = merged
        final_json = flatten_all_service_entries(final_json)

        # 5. Save the final result
        with open(OUTPUT_PATH, 'w') as f:
            json.dump(final_json, f, indent=2)
            
        print(f"\n  ✅ Bake-Off successful! Output saved to '{OUTPUT_PATH}'")

    except Exception as e:
        import traceback
        print(f"\n  --- ❌ An error occurred ---")
        print(f"  Error Type: {type(e).__name__}")
        print(f"  Error Details: {e}")
        print("  Traceback:")
        traceback.print_exc()

    print("\n---  Bake-Off Complete ---")