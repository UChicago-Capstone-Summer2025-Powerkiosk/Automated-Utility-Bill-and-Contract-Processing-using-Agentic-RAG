#!/usr/bin/env python3
# %%
import os
import glob
import json
import traceback
from pathlib import Path
from copy import deepcopy
from datetime import datetime
from dotenv import load_dotenv

from bill_split import *
from logger import BillLogger
from config import ONEDRIVE_PATH
from llm_image_utils import im2txt
from utils import send_query, fix_llm_json
from usage_by_plots import extract_yearly_breakdown
from month_utils import month_map, recover_month_list
from prompts import get_cls_usr_prompt, image_extraction_prompt
from usage_utils import (
    fix_years,
    merge_and_flatten_service_entries,
    flatten_all_service_entries,
    estimate_monthly_usage,
)
from extraction_utils import (
    agg_extract_service_entries,
    extract_bill_info,
    clean_account_numbers,
    deduplicate_service_entries,
    BillVariationManager,
    determine_variation_class_name,
)

load_dotenv()


def run(md_content, file_path, loggers=None, issuer=""):

    bill_json = {}
    bill_json["file"] = str(md_content).split("/")[-1]

    for meter_type in ["electricity", "natural_gas"]:
        logger = loggers.get(meter_type)
        if logger:
            logger.log_step(
                step="run_start", status="started", input={"file_path": str(file_path)}
            )
        print(f"\n=== Processing meter type: {meter_type} ===")
        if logger:
            logger.log_step(step=f"process_{meter_type}_start", status="started")
        try:
            svc = agg_extract_service_entries(
                file_path, md_content, meter_type, logger=logger, issuer=issuer
            )
            print(f"[DEBUG] service_entries: {svc!r}")
            if logger:
                logger.log_step(
                    step=f"agg_extract_service_entries_{meter_type}",
                    status="finished",
                    input={"file_path": str(file_path), "meter_type": meter_type},
                    output=svc,
                )
            if isinstance(svc, dict) and svc.get("Pass") == "Pass":
                bill_info = svc
            elif next(iter(svc.keys())) == "Pass":
                bill_info = {"Pass": "Pass"}
            else:
                bill_info = extract_bill_info(
                    md_content, meter_type, logger=logger, issuer=issuer
                )

                bill_info["service_entries"] = svc
                clean_account_numbers(bill_info)
                stmt = bill_info.get("statement_date", {})
                stmt_month = month_map.get(stmt.get("month"))
                stmt_year = str(stmt.get("year"))
                svc_raw = svc.copy()
                bill_info["service_entries"] = estimate_monthly_usage(
                    file_path, svc, stmt_month, stmt_year
                )
                if logger:
                    logger.log_step(
                        step=f"estimate_monthly_usage_{meter_type}",
                        status="finished",
                        input={
                            "svc": svc_raw,
                            "stmt_month": stmt_month,
                            "stmt_year": stmt_year,
                        },
                        output=bill_info["service_entries"],
                    )
                bill_info["service_entries"] = deduplicate_service_entries(
                    bill_info["service_entries"], logger
                )

                merged = merge_and_flatten_service_entries(bill_info["service_entries"])
                if logger:
                    logger.log_step(
                        step="merge_and_flatten_service_entries",
                        status="success",
                        input={"n_entries_in": len(bill_info["service_entries"])},
                        output={"n_entries_out": len(merged)},
                    )
                bill_info["service_entries"] = merged

                # Flatten all
                flattened = flatten_all_service_entries(bill_info)
                if logger:
                    logger.log_step(
                        step="flatten_all_service_entries",
                        status="success",
                        input={"keys_in": list(bill_info.keys())},
                        output={"keys_out": list(flattened.keys())},
                    )
                bill_info = flattened

                # Extracting yearly breakdown by graph if not already extracted.
                se = bill_info.get("service_entries")
                if (
                    (se is None)
                    or (not isinstance(se, dict))
                    or (list(se.keys()) == ["Pass"])
                    or (
                        all(
                            [
                                len(sev.get("yearly_estimated_usage") or {}) == 0
                                for sev in se.values()
                            ]
                        )
                    )
                ):
                    bill_info["aggregated_yearly_estimated_usage"] = (
                        extract_yearly_breakdown(file_path, meter_type)
                    )

            bill_json[meter_type] = bill_info
            print(f"[DEBUG] bill_json['{meter_type}']: {bill_json[meter_type]!r}")
            print("\n=== Completed processing all meter types ===")
            print(json.dumps(bill_json, indent=2))
            if logger:
                logger.log_step(
                    step=f"process_{meter_type}_complete",
                    status="success",
                    output=bill_info,
                )
        except Exception as e:
            import traceback

            print(f"❌❌❌ Error in meter type {meter_type}: {e}")
            traceback.print_exc()
            if logger:
                logger.log_error(e, traceback_str=traceback.format_exc())
                logger.log_step(
                    step=f"process_{meter_type}_error",
                    status="error",
                    input={"file_path": str(file_path), "meter_type": meter_type},
                    output=None,
                )

    # if logger:
    #     logger.log_step(step="run_complete", status="finished", output=bill_json)

    return bill_json


# %%

issuer = "AMEREN"
bill_path = Path(ONEDRIVE_PATH + "/dataset/bills/bill_issuers") / issuer

[i.split("\\")[-1] for i in glob.glob(str(bill_path) + "/*")]

# %%
target_docs = [
    "document_558",
]
ignore_docs = []

manager = BillVariationManager(
    f"all_jsons/bill_variations_{issuer}_testingBEN.json",
    f"all_jsons/final_bills_{issuer}_testingBEN.json",
)
use_existing_md_file = False

# Loop through folders
print(bill_path)
for sample_dir in bill_path.glob("document_*"):
    sample_number = sample_dir.name.replace("document_", "")
    if target_docs and sample_dir.name not in target_docs:
        continue  # ⬅️ Skip if not in target list
    if ignore_docs and sample_dir.name in ignore_docs:
        continue
    logger_global = BillLogger("logs", f"document_{sample_number}_global", issuer)
    logger_electricity = BillLogger(
        "logs", f"document_{sample_number}_electricity", issuer
    )
    logger_natural_gas = BillLogger(
        "logs", f"document_{sample_number}_natural_gas", issuer
    )
    loggers = {"electricity": logger_electricity, "natural_gas": logger_natural_gas}

    logger_global.log_step(
        step="start_bill_processing",
        status="started",
        input={"document": sample_dir.name},
    )
    try:
        file_path = sample_dir / f"document_{sample_number}.pdf"
        if not file_path.exists():
            msg = f"❌ Skipping missing file: {file_path}"
            print(msg)
            logger_global.log_step(
                step="missing_pdf",
                status="skipped",
                input={"file_path": str(file_path)},
                output=msg,
            )
            logger_global.finish(final_status="skipped")
            continue

        pdf_file_path = (
            Path(bill_path) / f"document_{sample_number}/document_{sample_number}.pdf"
        )
        print(pdf_file_path)

        sys_prompt = "You are a highly accurate assistant trained to extract structured utility bill data for energy savings and budget reporting."

        if (
            len(list(pdf_file_path.parent.glob(f"{pdf_file_path.parent.name}_*_*.pdf")))
            > 0
        ):
            split_pdf_paths = list(
                pdf_file_path.parent.glob(f"{pdf_file_path.parent.name}_*_*.pdf")
            )
        else:
            pages = get_bill_pages(Path(pdf_file_path))
            split_pdf_paths = split_pdf(Path(pdf_file_path), pages)

        for oper_pdf_path in split_pdf_paths:
            # if oper_pdf_path.with_suffix('.md').exists():
            #     continue

            try:
                logger_global = BillLogger(
                    "logs", f"{oper_pdf_path.with_suffix('').name}_global", issuer
                )
                logger_electricity = BillLogger(
                    "logs", f"{oper_pdf_path.with_suffix('').name}_electricity", issuer
                )
                logger_natural_gas = BillLogger(
                    "logs", f"{oper_pdf_path.with_suffix('').name}_natural_gas", issuer
                )
                loggers = {
                    "electricity": logger_electricity,
                    "natural_gas": logger_natural_gas,
                }

                logger_global.log_step(
                    step="start_bill_processing",
                    status="started",
                    input={"document": sample_dir.name},
                )

                # Load or extract markdown
                if use_existing_md_file and os.path.exists(
                    oper_pdf_path.with_suffix(".md")
                ):
                    with open(
                        oper_pdf_path.with_suffix(".md"), "r", encoding="utf-8"
                    ) as f:
                        md_content_raw = f.read()
                    print("File exists.")
                    logger_global.log_step(
                        step="load_existing_md",
                        status="success",
                        input={"md_file": str(f.name)},
                    )
                else:
                    if use_existing_md_file:
                        print("File does not exist.")
                        logger_global.log_step(
                            step="load_existing_md", status="not_found"
                        )
                    md_content_raw = im2txt(
                        str(sample_dir),
                        oper_pdf_path,
                        image_extraction_prompt,
                        logger_global,
                    )
                    logger_global.log_step(step="extract_md", status="success")

                md_content = md_content_raw
                # print("MD CONTENT\n\n\n")
                # print(md_content)
                logger_global.log_step(step="md_content_loaded", status="success")

                # Classify
                cls_usr_msg = get_cls_usr_prompt(md_content)
                cls_sys_msg = (
                    "You are a helpful assistant for classifying utility bills."
                )
                rsp_cls, _ = send_query(
                    cls_sys_msg, cls_usr_msg, file_path=None, logger=logger_global
                )

                cls_dict = fix_llm_json(rsp_cls)
                cls_name = determine_variation_class_name(cls_dict)
                logger_global.log_step(
                    step="bill_classification",
                    status="success",
                    output={"cls_name": cls_name},
                )

                # Extract
                result = run(md_content, oper_pdf_path, loggers=loggers, issuer=issuer)
                result["filename"] = oper_pdf_path.with_suffix("").name
                result["issuer"] = issuer

                if issuer in ["COMED"]:
                    fixed_result = fix_years(result)
                else:
                    fixed_result = deepcopy(result)

                manager.add_result(issuer, cls_name, fixed_result)
                logger_global.log_step(
                    step="add_result", status="success", output={"cls_name": cls_name}
                )

                merged_log = {
                    "document_id": oper_pdf_path.with_suffix("").name,
                    "issuer": issuer,
                    "steps": logger_global.log,
                    "electricity": logger_electricity.log,
                    "natural_gas": logger_natural_gas.log,
                    "final_status": "success",
                    "finished_at": datetime.now().isoformat(),
                }

                run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_filename = (
                    f"{issuer}_{oper_pdf_path.with_suffix('').name}_{run_id}.json"
                )
                log_path = os.path.join("logs", log_filename)
                with open(log_path, "w", encoding="utf-8") as f:
                    json.dump(merged_log, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Processed {oper_pdf_path.with_suffix('').name} → {cls_name}")
                print("\n\n", fixed_result)
                print("-" * 50)
                # break

            except Exception as e:
                print(f"❌❌❌❌ Failed {oper_pdf_path.with_suffix('').name}")
                print("Error message:", e)
                print("Full traceback:")
                traceback.print_exc()
                print("-" * 50)

                # Log error for post-mortem
                error_info = {
                    "type": type(e).__name__,
                    "message": str(e),
                    "traceback": traceback.format_exc(),
                }
                # You can put error_info in global steps, or as its own key
                logger_global.log["error"] = error_info

                merged_log = {
                    "document_id": oper_pdf_path.with_suffix("").name,
                    "issuer": issuer,
                    "steps": logger_global.log,
                    "electricity": logger_electricity.log,
                    "natural_gas": logger_natural_gas.log,
                    "final_status": "success",
                    "finished_at": datetime.now().isoformat(),
                }
                run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_filename = f"{issuer}_{oper_pdf_path.name}_{run_id}.json"
                log_path = os.path.join("logs", log_filename)
                with open(log_path, "w", encoding="utf-8") as f:
                    json.dump(merged_log, f, indent=2, ensure_ascii=False, default=str)

    except Exception as e:
        print(f"❌❌❌❌ Failed {pdf_file_path.name}")
        print("Error message:", e)
        print("Full traceback:")
        traceback.print_exc()
        print("-" * 50)
# %%