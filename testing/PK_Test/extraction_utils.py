import re
import json
from pathlib import Path
from typing import Any, Union
from collections import defaultdict

from utils import send_query
from validation import get_validation
from utils import send_query, fix_llm_json
from to_final_bill import create_final_bill_result
from prompts import (
    get_sytem_message_checking_count,
    get_user_prompt_checking_count,
    get_sytem_message,
    get_sytem_message_pre_bill,
    get_service_entry_reasoning_prompt,
)
from models import (
    adapter_service_entry,
    adapter_loose_service_entry,
    adapter_utility_bill,
    adapter_loose_utility_bill,
)


def extract_service_entries(
    bill_dir: Path,
    md_content: str,
    meter_type: str,
    logger=None,  # Add logger argument
    issuer="",
) -> dict:
    sys_reasoning_prompt = get_service_entry_reasoning_prompt(meter_type)
    user_reasoning_prompt = get_user_prompt_checking_count(md_content)

    raw_pre, _ = send_query(sys_reasoning_prompt, user_reasoning_prompt)
    print("pre_svc: ", raw_pre)
    sys_prompt = get_sytem_message_checking_count(meter_type)
    user_prompt = get_user_prompt_checking_count(raw_pre)
    # call LLM
    raw, _ = send_query(sys_prompt, user_prompt)

    if logger:
        logger.log_step(
            step="extract_service_entries_llm",
            status="success",
            input={"prompt": sys_prompt, "user_prompt": user_prompt},
            output=raw,
            meta={"meter_type": meter_type, "bill_dir": str(bill_dir)},
        )

    # early-exit if “Pass”
    try:
        raw = re.sub("```json|```|\n", "", raw)
        parsed = fix_llm_json(raw)
        if isinstance(parsed, dict) and parsed.get("Pass") == "Pass":
            if logger:
                logger.log_step(
                    step="extract_service_entries_early_pass",
                    status="pass",
                    output=parsed,
                )
            return parsed
        elif (len(raw) < 20) and "pass" in raw.lower():
            parsed = {"Pass": "Pass"}
            if logger:
                logger.log_step(
                    step="extract_service_entries_early_pass_short",
                    status="pass",
                    output=parsed,
                )
            return parsed
    except json.JSONDecodeError as e:
        if logger:
            logger.log_error(e)

    # validate (strict → loose → raw)
    entries = get_validation(
        llm_raw=raw,
        strict_adapter=adapter_service_entry,
        loose_adapter=adapter_loose_service_entry,
        system_prompt=sys_prompt,
        original_md=md_content,
    )

    # entries is a dict[str, ServiceEntry | PassResponse] or raw dict
    result = {}
    for key, val in entries.items():
        if hasattr(val, "model_dump"):
            result[key] = val.model_dump(exclude_none=True)
        else:
            result[key] = val
    if logger:
        logger.log_step(
            step="extract_service_entries_complete", status="success", output=result
        )
    return result


def agg_extract_service_entries(
    file_path, md_content, meter_type, logger=None, issuer=""
):
    pages = re.split(r"(## Page \d+)", md_content, flags=re.IGNORECASE)
    result = []
    if len(pages) > 1:
        for i in range(1, len(pages), 2):
            header = pages[i].strip()
            content = pages[i + 1].strip() if i + 1 < len(pages) else ""
            result.append(f"{header}\n{content}")
    else:
        content = pages[0].strip()
        result.append(content)

    se_list = []
    for i in range(0, len(result), 3):
        batch = result[i : i + 3]
        batch_md = "\n\n\n".join(batch)
        se = extract_service_entries(
            file_path, batch_md, meter_type, logger=logger, issuer=issuer
        )
        if isinstance(se, dict) and se.get("Pass") == "Pass":
            if logger:
                logger.log_step(
                    step="agg_extract_service_entries_batch_pass",
                    status="pass",
                    output=se,
                )
            pass
        elif (len(str(se)) < 20) and "pass" in str(se).lower():
            if logger:
                logger.log_step(
                    step="agg_extract_service_entries_batch_short_pass",
                    status="pass",
                    output=se,
                )
            pass
        else:
            se_list.append(se)
    if len(se_list) == 0:
        parsed = {"Pass": "Pass"}
        if logger:
            logger.log_step(
                step="agg_extract_service_entries_none_found",
                status="pass",
                output=parsed,
            )
        return parsed
    else:
        merged = {}
        entry_counter = 1
        for d in se_list:
            for entry in d.values():
                key = f"service_entry_{entry_counter}"
                merged[key] = entry
                entry_counter += 1
        if logger:
            logger.log_step(
                step="agg_extract_service_entries_merged",
                status="success",
                output=merged,
            )
        return merged


def extract_bill_info(md_content: str, meter_type: str, logger=None, issuer="") -> dict:
    sys_prompt = get_sytem_message(meter_type, issuer)
    sys_prompt_pre_bill = get_sytem_message_pre_bill(meter_type, issuer)
    raw_pre_bill = send_query(sys_prompt_pre_bill, md_content)
    if logger:
        logger.log_step(
            step="pre_bill_info",
            status="success",
            input={"prompt": sys_prompt_pre_bill, "md_content": md_content},
            output=raw_pre_bill,
        )
    print("PRE_BILL", raw_pre_bill[0], "\n\n\n\n")
    raw, _ = send_query(sys_prompt, raw_pre_bill[0])
    print("BILL_INFO", raw, "\n\n\n\n")
    if logger:
        logger.log_step(
            step="bill_info_raw",
            status="success",
            input={"prompt": sys_prompt, "pre_bill_info": raw_pre_bill[0]},
            output=raw,
        )
    bill = get_validation(
        llm_raw=raw,
        strict_adapter=adapter_utility_bill,
        loose_adapter=adapter_loose_utility_bill,
        system_prompt=sys_prompt,
        original_md=raw_pre_bill,
    )
    print("BILL_INFO", bill, "\n\n\n\n")
    # bill is UtilityBillInfo | PassResponse | raw dict
    if hasattr(bill, "model_dump"):
        bill_output = bill.model_dump(exclude_none=True)
    else:
        bill_output = bill

    if logger:
        logger.log_step(
            step="extract_bill_info",
            status="success",
            input={"md_content": "(truncated)", "meter_type": meter_type},
            output=bill_output,
        )
    return bill_output


def clean_account_numbers(obj: Union[dict, list]) -> None:
    """
    Recursively walk through obj, and for any dict key === "account_number",
    strip all whitespace from its string value in place.
    """
    if isinstance(obj, dict):
        for key, val in obj.items():
            if key == "account_number" and isinstance(val, str):
                # remove all whitespace characters
                obj[key] = re.sub(r"\s+", "", val)
            else:
                clean_account_numbers(val)
    elif isinstance(obj, list):
        for item in obj:
            clean_account_numbers(item)


def deduplicate_service_entries(service_entries, logger=None):
    def group_key(entry):
        meter = entry.get("meter_number")
        if not meter:
            meter = "UNKNOWN_METER"
        return (
            entry.get("account_number", ""),
            meter,
            entry.get("service_address", ""),
        )

    if logger:
        logger.log_step(
            step="deduplicate_service_entries_start",
            status="started",
            input={"input_count": len(service_entries)},
        )

    grouped = defaultdict(list)
    for entry in service_entries.values():
        grouped[group_key(entry)].append(entry)

    if logger:
        logger.log_step(
            step="deduplicate_service_entries_grouped",
            status="grouped",
            input={"group_count": len(grouped)},
        )

    deduped = {}
    idx = 1
    for entries in grouped.values():
        regulars = [e for e in entries if e.get("usage_period", "") == "regular"]
        if regulars:
            for entry in regulars:
                deduped[f"service_entry_{idx}"] = entry
                idx += 1
        else:
            for entry in entries:
                deduped[f"service_entry_{idx}"] = entry
                idx += 1

    if logger:
        logger.log_step(
            step="deduplicate_service_entries_complete",
            status="success",
            output={"deduped_count": len(deduped)},
        )

    return deduped


class BillVariationManager:
    def __init__(
        self,
        bill_variations_path="bill_variations.json",
        final_bills_path="final_bills.json",
    ):
        self.bill_variations_path = Path(bill_variations_path)
        self.final_bills_path = Path(final_bills_path)

        if self.bill_variations_path.exists():
            try:
                content = self.bill_variations_path.read_text().strip()
                self.variations = json.loads(content) if content else {}
            except json.JSONDecodeError:
                print(f"⚠️ Invalid JSON in {self.bill_variations_path}. Starting fresh.")
                self.variations = {}
        else:
            self.variations = {}

        if self.final_bills_path.exists():
            try:
                content = self.final_bills_path.read_text().strip()
                self.final_bills = json.loads(content) if content else []
            except json.JSONDecodeError:
                print(f"⚠️ Invalid JSON in {self.final_bills_path}. Starting fresh.")
                self.final_bills = []
        else:
            self.final_bills = []

    def add_result(self, issuer: str, variation: str, result: dict):
        filename = result.get("filename")
        if not filename:
            raise ValueError("Result must include 'filename' to ensure uniqueness.")

        issuer_data = self.variations.setdefault(issuer, {})
        variation_list = issuer_data.setdefault(variation, [])

        # Replace existing result with same filename
        updated = False
        for i, entry in enumerate(variation_list):
            if entry.get("filename") == filename:
                variation_list[i] = result
                updated = True
                break

        if not updated:
            variation_list.append(result)

        # Creating final result and adding
        final_results = create_final_bill_result(issuer, variation, result)
        for commodity, res in final_results.items():
            updated = False
            for i, entry in enumerate(self.final_bills):
                if (
                    entry.get("documentId", "") == filename
                    and entry.get("issuer", "") == issuer
                    and entry.get("commodity", "") == commodity
                ):
                    self.final_bills[i] = res
                    updated = True
                    break

            if not updated:
                self.final_bills.append(res)

        self._save()

    def _save(self):
        self.bill_variations_path.write_text(
            json.dumps(self.variations, indent=2, ensure_ascii=False)
        )
        self.final_bills_path.write_text(
            json.dumps(self.final_bills, indent=2, ensure_ascii=False)
        )

    def to_dict(self):
        return self.variations


from pathlib import Path


def determine_variation_class_name(classification: dict) -> str:
    structural = classification.get("structuralClass")
    usage_aggregated = classification.get("usageAggregated")

    if structural == "one_to_one":
        return "one_to_one"

    if structural == "one_account_multiple_addresses":
        return (
            "one_account_multiple_addresses_aggregated_usage"
            if usage_aggregated
            else "one_account_multiple_addresses_multi_usage"
        )

    if structural == "one_address_multiple_accounts":
        return (
            "one_address_multiple_accounts_aggregated_usage"
            if usage_aggregated
            else "one_address_multiple_accounts_multi_usage"
        )

    raise ValueError(f"Unsupported structuralClass: {structural}")
