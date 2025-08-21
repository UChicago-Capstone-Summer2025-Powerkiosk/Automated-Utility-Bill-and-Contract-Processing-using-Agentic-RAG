import re
import cv2
import datetime
from pathlib import Path
from copy import deepcopy
from typing import Dict, List
from collections import defaultdict

from utils import send_query, fix_llm_json
from month_utils import month_map, recover_month_list
# from image_processing import extract_bars_from_image, crop_bar_chart_above_month_axis


def estimate_monthly_usage(
    bill_dir: Path,
    service_entries: dict,
    statement_month: str,
    statement_year: str,
) -> dict:
    # logger.debug(f"Starting estimate_image_usage for {len(service_entries)} entries")

    for key, se in service_entries.items():
        breakdown = se.get("yearly_usage_breakdown") or {}
        btype = breakdown.get("type")

        # 1) TABLE or TEXT → single LLM call to normalize JSON
        if btype in ("table", "text"):
            raw = breakdown.get("content", "")
            # build a user prompt that asks for exactly the JSON map
            user_msg = f"""
You’re given a yearly usage breakdown for a utility bill, in {se.get("unit")}.  
If the table does not include individual monthly usage values, return null.
Transform it into a JSON object where each key is "FullMonthName Year" and each value is the integer usage.

The bottom year should be {statement_year}. If there is multiple same months in OCR still keep it and assign previous year on first appeared month
Do not discard any value keep all months-usage pairs even if duplicated.
Only add years.
For the metadata field:

If the table mentions “on-peak” or “off-peak”, use the exact string found: “on-peak” or “off-peak”.

If there is no on-peak or off-peak information anywhere in the table, set metadata to “regular”.
"metadata": "on-peak" | "off-peak" | "regular"



Here is the raw breakdown:
{raw}


Examples:

Example 1:  
If the OCR text is like this:



| Monthly {type} Use |  |  |  |  |  |
| :--: | :--: | :--: | :--: | :--: | :--: |
| Dec | Jan | Feb | Mar | Apr | May | Jun |
| <usage_1> | <usage_2> | <usage_3> | <usage_4> | <usage_5> | <usage_6> | <usage_7> |
| Jul | Aug | Sep | Oct | Nov | Dec |  |
| <usage_8> | <usage_9> | <usage_10> | <usage_11> | <usage_12> | <usage_13> |  |

statement year is {statement_year}

{{
"usage":{{
  "December {int(statement_year)-1}": <usage_1>,
  "January {statement_year}": <usage_2>,
  "February {statement_year}": <usage_3>,
  "March {statement_year}": <usage_4>,
  "April {statement_year}": <usage_5>,
  "May {statement_year}": <usage_6>,
  "June {statement_year}": <usage_7>,
  "July {statement_year}": <usage_8>,
  "August {statement_year}": <usage_9>,
  "September {statement_year}": <usage_10>,
  "October {statement_year}": <usage_11>,
  "November {statement_year}": <usage_12>,
  "December {statement_year}": <usage_13>
        }},
"metadata" : "regular"
}}

---

Example 2:  
If the OCR text is like this:
This is not yearly usage breakdown by months
Its showing one value for one year so just ignore it and return null

| Date Range        | Annual Total Usage | Avg Monthly |
| :---------------- | :----------------- | :---------- |
| Dec 2020 - Nov 2021 | 130920 kWh         | 10910 kWh   |

null

""".strip()

            system_msg = (
                "You are a data-normalization assistant. "
                "Convert raw usage breakdowns into clean JSON maps."
            )

            try:
                response_text, _ = send_query(system_msg, user_msg)
                yearly_usage_dict = fix_llm_json(response_text)
                se["yearly_estimated_usage"] = yearly_usage_dict
            except Exception:
                # logger.exception(f"Error parsing table/text breakdown for '{key}'")
                se["yearly_estimated_usage"] = None

            continue  # next service entry

        # 2) IMAGE → your existing bar-chart pipeline
        if btype == "image":
            try:
                img_path = bill_dir / breakdown["content"]
                imgname = "_".join(str(img_path).split("/")[-3:])

                img = cv2.imread(str(img_path))
                cropped_img = crop_bar_chart_above_month_axis(img_path)
                if img is None:
                    raise FileNotFoundError(f"{img_path} not found")

                # extract raw bar heights
                bar_heights_px = extract_bars_from_image(cropped_img, str(img_path))
                cropped_img_path = f"./cropped_images/{imgname}_output_bars_cropped.png"
                # recover the month list via LLM
                month_bar_list = recover_month_list(
                    img_path=str(cropped_img_path),
                    usage=se.get("usage"),
                    unit=se.get("unit"),
                    statement_month=statement_month,
                    statement_year=statement_year,
                    send_query_func=send_query,
                )

                # normalize into month-year → usage
                refined = get_usage_from_bar_chart(
                    bar_heights_px=bar_heights_px,
                    month_bar_list=month_bar_list,
                    statement_month=statement_month,
                    statement_year=statement_year,
                    usage=se.get("usage"),
                    unit=se.get("unit"),
                )
                se["yearly_estimated_usage"] = refined

            except Exception:
                # logger.exception(f"Error in image usage for '{key}'")
                se["yearly_estimated_usage"] = None

            continue

        # 3) anything else → no data
        se["yearly_estimated_usage"] = None

    return service_entries


def get_usage(
    img_path,
    img_sys_prompt,
    bar_heights_px,
    statement_month,
    statement_year,
    usage,
    unit,
):
    print(f"\n[get_usage] img_path: {img_path}")
    print(f"[get_usage] statement_month/year: {statement_month} {statement_year}")
    print(f"[get_usage] raw usage/unit: {usage}{unit}")
    print(f"[get_usage] bar_heights_px: {bar_heights_px}")

    user_prompt = f"Last bar is {statement_month} of {statement_year} its {usage}{unit}"
    print(
        f"[get_usage] sending to LLM:\nSYSTEM_PROMPT: {img_sys_prompt}\nUSER_PROMPT: {user_prompt}"
    )

    bar_llm_response, _ = send_query(img_sys_prompt, user_prompt, img_path)
    print(f"[get_usage] LLM response: {bar_llm_response}")

    try:
        month_bar_list = eval(bar_llm_response[0])
        print(f"[get_usage] Parsed month_bar_list: {month_bar_list}")
    except Exception as e:
        print(f"[get_usage] ✖ failed to eval LLM response: {e}")
        raise

    if not month_bar_list:
        raise ValueError("[get_usage] month_bar_list is empty")

    # if month_bar_list[-1].lower() != statement_month.lower():
    print(
        f"[get_usage] ⚠ last month mismatch: {month_bar_list[-1]} vs {statement_month}"
    )

    # build pixel→month dict
    month_px_dic = {
        month: px for px, month in zip(bar_heights_px.values(), month_bar_list)
    }
    print(f"[get_usage] month_px_dic: {month_px_dic}")

    last_month_pixel = month_px_dic.get(month_bar_list[-1])
    print(f"[get_usage] last_month_pixel: {last_month_pixel}")
    if not last_month_pixel:
        raise ValueError("[get_usage] Height of last bar is zero or missing")

    estimated_usage = {
        month: round((h / last_month_pixel) * usage)
        for month, h in month_px_dic.items()
    }
    print(f"[get_usage] estimated_usage: {estimated_usage}")
    return estimated_usage


def get_usage_from_bar_chart(
    bar_heights_px: Dict[str, int],
    month_bar_list: List[str],
    statement_month: str,
    statement_year: str,
    usage: float,
    unit: str,
) -> Dict[str, int]:
    print(f"\n[get_usage_from_bar_chart] bar_heights_px: {bar_heights_px}")
    print(f"[get_usage_from_bar_chart] month_bar_list: {month_bar_list}")
    print(
        f"[get_usage_from_bar_chart] statement_month/year: {statement_month} {statement_year}"
    )
    print(f"[get_usage_from_bar_chart] usage/unit: {usage}{unit}")

    if not month_bar_list:
        raise ValueError("Month list from LLM is empty.")

    # 1) Build month-year pairs by walking backwards from the statement year
    #    (same as you had, but without requiring the last element to match)
    year_mapped = []
    current_year = int(statement_year)
    n = len(month_bar_list)
    for idx in range(n - 1, -1, -1):
        month = month_bar_list[idx]
        nxt = month_bar_list[idx + 1] if idx + 1 < n else None
        # if you see Dec → Jan boundary, step back a year
        if nxt and month.lower() == "december" and nxt.lower() == "january":
            current_year -= 1
        year_mapped.append((month, current_year))
    year_mapped.reverse()
    print(f"[get_usage_from_bar_chart] year_mapped_months: {year_mapped}")

    # 2) Find the index of the statement month/year in our list
    target = (statement_month.lower(), int(statement_year))
    try:
        stmt_idx = next(
            i
            for i, (m, y) in enumerate(year_mapped)
            if m.lower() == target[0] and y == target[1]
        )
    except StopIteration:
        raise ValueError(
            f"Could not find a bar matching statement date {statement_month} {statement_year} "
            f"in {year_mapped}"
        )
    print(f"[get_usage_from_bar_chart] statement month found at index {stmt_idx}")

    # 3) Grab the pixel-height of that bar as our normalizer
    pixel_values = list(bar_heights_px.values())
    ref_pixel = pixel_values[stmt_idx]
    print(f"[get_usage_from_bar_chart] reference_pixel (statement month): {ref_pixel}")
    if ref_pixel == 0:
        raise ValueError(
            "Height of the statement-month bar is zero; cannot normalize usage."
        )

    # 4) Compute usage for each month up through statement_idx
    estimated_usage = {}
    for i, (month, year) in enumerate(year_mapped[: stmt_idx + 1]):
        height = pixel_values[i]
        key = f"{month} {year}"
        # scale linearly
        estimated_usage[key] = round((height / ref_pixel) * usage)
    print(f"[get_usage_from_bar_chart] estimated_usage: {estimated_usage}")

    return estimated_usage


def fix_usage_for_entry(entry, stmt_year, stmt_month):
    """
    Shifts all months in entry['yearly_estimated_usage'] so that the
    last month aligns correctly with the statement date logic.
    """
    usage = entry.get("yearly_estimated_usage")
    if not usage:
        return

    # 1) Parse keys into (year, month, month_name, value)
    items = []

    for key, val in usage.items():
        mon_name, yr_str = key.split()
        mon_num = datetime.datetime.strptime(mon_name, "%B").month
        yr_num = int(yr_str)
        items.append((yr_num, mon_num, mon_name, val))

    # 2) Find the original max (year, month)
    orig_year, orig_month = max((y, m) for y, m, _, _ in items)

    # 3) Compute target year for that orig_month
    if stmt_month >= orig_month:
        target_year = stmt_year
    else:
        target_year = stmt_year - 1

    year_diff = target_year - orig_year

    # 4) Rebuild shifted usage dict
    usage = {}
    for y, m, mon_name, val in items:
        new_key = f"{mon_name} {y + year_diff}"
        usage[new_key] = val

    entry["yearly_estimated_usage"] = usage


def fix_years(bill):
    """
    For each of 'electricity' and 'natural_gas':
      - If the top-level dict has no 'Pass' key,
      - Then for EACH service_entry under 'service_entries',
        apply fix_usage_for_entry().
    """
    for svc_type in ("electricity", "natural_gas"):
        svc = bill.get(svc_type)
        if not svc or "Pass" in svc:
            continue

        stmt = svc.get("statement_date", {})
        stmt_year = stmt.get("year")
        stmt_month = stmt.get("month")
        if not (stmt_year and stmt_month):
            continue

        for entry in svc.get("service_entries", {}).values():
            fix_usage_for_entry(entry, stmt_year, stmt_month)

    return bill


def merge_and_flatten_service_entries(service_entries):
    grouped = defaultdict(list)
    for entry in service_entries.values():
        if not isinstance(entry, dict):
            continue  # Skip if entry is None or not a dict
        key = tuple(
            entry.get(field)
            for field in [
                "account_number",
                "service_reference",
                "meter_number",
                "unit",
                "service_address",
            ]
        )
        grouped[key].append(entry)

    merged_entries = []
    for key, entries in grouped.items():
        merged_entry = deepcopy(entries[0])
        total_usage = defaultdict(int)

        for entry in entries:
            yeu = entry.get("yearly_estimated_usage")
            if not isinstance(yeu, dict):
                usage_dict = {}
            else:
                usage_dict = yeu.get("usage", {})
            for month, val in usage_dict.items():
                total_usage[month] += val

        merged_entry["yearly_estimated_usage"] = dict(total_usage)
        merged_entry["usage"] = sum(
            entry.get("usage", 0) or 0
            for entry in entries
            if isinstance(entry, dict) and "usage" in entry
        )
        merged_entries.append(merged_entry)

    return {f"service_entry_{i+1}": entry for i, entry in enumerate(merged_entries)}


def flatten_all_service_entries(result):
    result = deepcopy(result)  # don't modify input in-place
    service_entries = result.get("service_entries", {})
    for entry in service_entries.values():
        yeu = entry.get("yearly_estimated_usage")
        if isinstance(yeu, dict) and "usage" in yeu:
            # Replace with just the usage dict, drop 'usage' and 'metadata'
            entry["yearly_estimated_usage"] = dict(yeu["usage"])
    return result