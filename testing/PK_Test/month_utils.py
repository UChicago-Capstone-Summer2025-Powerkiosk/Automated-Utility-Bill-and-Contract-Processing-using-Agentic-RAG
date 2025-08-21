import ast
import logging
from config import logger

VALID_MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def parse_and_validate_month_list(output_str: str) -> list | None:
    """Try parsing and validating a month list from LLM output."""
    try:
        result = ast.literal_eval(output_str)
        if not isinstance(result, list):
            raise ValueError("LLM output is not a list.")
        invalid = [m for m in result if m not in VALID_MONTHS]
        if invalid:
            raise ValueError(f"Invalid months found: {invalid}")
        return result
    except Exception as e:
        logger.warning(f"Month list validation failed: {e}")
        return None


def recover_month_list(
    img_path: str,
    usage: float,
    unit: str,
    statement_month: str,
    statement_year: str,
    send_query_func,
) -> list:
    """
    Use LLM to extract a list of month names from a bar chart image.
    Automatically retries if the output is invalid.
    """
    # Step 1: Initial prompt
    base_prompt = f"""
Last bar is {statement_month} of {statement_year} its {usage}{unit}
"""

    img_sys_prompt = """
You are a visual reasoning assistant. Your task is to identify the month represented beneath each bar in a bar chart, reading strictly from **left to right**.

Each bar has a label that may be:
- A full month name (e.g., "January")
- A 3-letter abbreviation (e.g., "Jan")
- A single letter (e.g., "J")

Your responsibilities:
1. Return the **full month names** for each bar, preserving **left-to-right** order.
2. Use the **standard month sequence** (January → December) to resolve ambiguous or abbreviated labels.
   - For example: ["J", "F", "M"] → ["January", "February", "March"]
   - For repeated letters like "J", infer by position (e.g., ["J", "A", "J"] → ["January", "April", "June"])
3. Do **not skip**, ignore, or merge duplicate months — if a label appears twice, it must appear twice in the output.
   - For example, if "December" appears at both ends, both must be preserved.
4. Treat the sequence as **spanning across years** if necessary.
   - If the list starts with "December" and continues with "January", assume the year wraps correctly.
   - The **last “December” in the list marks the end of the reporting period** (i.e., statement year).

🧾 Return format:
- Output a **Python-style list of full month names**, ordered left to right.
- Do **not** include explanations or extra commentary.

✅ Example Outputs:
["December", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
["October", "November", "December", "January", "February", "March", "April", "May"]
["December", "January", "February", "March"]
"""

    # Step 2: First attempt
    logger.info("Sending initial month list query...")
    initial_response = send_query_func(img_sys_prompt, base_prompt, img_path)
    raw_output = initial_response[0]
    print("month_list raw", raw_output)
    month_list = parse_and_validate_month_list(raw_output)
    print("month_list parsed", month_list)
    # Step 3: Retry if needed
    if month_list is None:
        logger.info("Initial response failed validation. Retrying with repair prompt.")

        repair_sys = "You are a visual assistant repairing a bad month label output from a bar chart."

        error_description = f"""Original LLM output:
{raw_output}

Error:
- Output must be a Python-style list (e.g., ["January", "February"])
- Only valid month names are allowed: {', '.join(VALID_MONTHS)}
"""

        repair_prompt = f"""
Please re-output the correct list of full month names from the bar chart image.

⚠️ Format Rules:
- Python-style list only, ordered left to right.
- Each item must be one of: {', '.join(VALID_MONTHS)}
- No typos. No extra text. No formatting like Markdown.

Fix this:
{error_description}
"""

        fixed_response = send_query_func(repair_sys, repair_prompt, img_path)
        month_list = parse_and_validate_month_list(fixed_response[0])

        if month_list is None:
            raise ValueError(
                "LLM failed to produce a valid month list even after repair."
            )

    logger.info("Month list successfully recovered.")
    return month_list


month_map = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}