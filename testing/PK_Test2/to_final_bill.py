import os
import json
import time
from typing import Dict
from pathlib import Path
from pprint import pprint
from datetime import datetime
from collections import defaultdict
from langchain_openai import ChatOpenAI

from config import ONEDRIVE_PATH
from utils import llm_response_to_json

BASE_PATH = Path(ONEDRIVE_PATH + f"/dataset/bills/bill_issuers")

llm = ChatOpenAI(
    model='gpt-4o', 
    api_key=os.getenv('OPENAI_API_KEY'),
    temperature=0.1,
)

check_yearly_estimated_usage_prompt = """
You are an expert in understanding electricity and gas bills.

# Background:
We have electricity and natural gas bills as PDF. We have extracted the PDF as MD and then extracted some insights from the bill.
In the bills, we have multiple service entries. By 'service entries', we mean that for the same user in the same bill, there are details mentioned for multiple accounts, or service reference, or meter number.
For the total bill or each individual service entry, we also have extracted the yearly estimated usage for the past 12 months.

# Goal:
Your task is to analyze the MD text of the PDF and the extracted JSON data and check if the bill mentions the yearly estimated usage for each service entry individually or the bill mentions one aggregated yearly estimated usage only (once in the pdf).

Note that if the bill mentions one aggregated yearly estimated usage, it is possible that it is repeated in the extracted data for one or more service entry which is an error. Thus, don't get confused. 
Since this can be repeated if it is not present for individual bills, you can use the values from the extracted data itself and not from MD text.

# Output Schema:
Your response should be JSON serializable in the schema mentioned below:
```
{{
    "provided_individually" : (bool) <'true' if bill mentions yearly estimate usage for each service entry individually or 'false' if the bill provides an aggregated yearly estimated usage for all service entries only once.>,
    "aggregated_yearly_estimated_usage" : (dict) <The aggregated yearly estimated usage for each month as dictionary in the format `"Month Year" : value (int)`. This is similar to 'yearly_estimated_usage' from the input.>
}}
```

# Bill MD text:
The markdown text of the bill is mentioned below within backticks:
```
{bill_md_text}
```

# Extracted Data:
```
{data}
```
""".strip()

def check_yearly_estimated_usage(base_data_path:Path, issuer:str, filename:str, data:Dict):
    # Checking if this is required (if multiple service entries are present)
    service_entries = data.get('service_entries') or {}
    if len(service_entries) <= 1:
        return data
    if data.get('aggregated_yearly_estimated_usage') is not None:
        return data
    
    # Reading MD file
    md_path:Path = base_data_path.joinpath(f"{issuer.upper()}/{'_'.join(filename.split('_')[:2])}/{filename}.md")
    md_text:str = md_path.read_text(encoding='utf-8')
    
    # Using LLM to determine aggregated usage is given or not
    try:
        response = llm_response_to_json(llm.invoke(
            check_yearly_estimated_usage_prompt.format(bill_md_text=md_text, data=json.dumps(data, indent=2))
        ).content)
    except:
        time.sleep(5)
        response = llm_response_to_json(llm.invoke(
            check_yearly_estimated_usage_prompt.format(bill_md_text=md_text, data=json.dumps(data, indent=2))
        ).content)
    
    print(f"\nResponse of check_yearly_estimated_usage from LLM for '{issuer}' & '{filename}':")
    pprint(response, width=120)
    
    if not response['provided_individually']:
        for service_entry_key in service_entries.keys():
            if 'yearly_usage_breakdown' in data['service_entries'][service_entry_key]:
                del data['service_entries'][service_entry_key]['yearly_usage_breakdown']
            if 'yearly_estimated_usage' in data['service_entries'][service_entry_key]:
                del data['service_entries'][service_entry_key]['yearly_estimated_usage']
        data['aggregated_yearly_estimated_usage'] = response['aggregated_yearly_estimated_usage']
        
    return data


# Helper to safely parse amounts
def try_parse_amount(value):
    if not value:
        return 0.0
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0.0

# Transformer function
def transform_bill_entry(base_data_path, raw_entry, commodity, issuer):
    data = raw_entry.get(commodity)
    if not isinstance(data, dict):
        return None

    # Skip if the entire commodity section is a placeholder like {"Pass": "Pass"}
    if list(data.keys()) == ["Pass"] and data["Pass"] == "Pass":
        return None

    # Extra: Skip if it's dict but service_entries is also just a "Pass" dict
    if "service_entries" in data:
        se = data["service_entries"]
        if isinstance(se, dict) and list(se.keys()) == ["Pass"] and se["Pass"] == {"yearly_estimated_usage": None}:
            return None
    aggregated_usage_history = defaultdict(float)  # <-- Moved here

    units = set()
    electricity = raw_entry.get(commodity, {})
    commodity = electricity.get("extracting", commodity)
    billed_usage = electricity.get("billed_usage")
    if not isinstance(electricity.get("service_entries"), dict):
        return None

    statement_date = electricity.get("statement_date", {})
    statement_date_str = None
    try:
        statement_date_str = f"{statement_date['year']}-{int(statement_date['month']):02d}-{int(statement_date['day']):02d}"
    except (KeyError, ValueError, TypeError):
        pass

    customer_name = electricity.get("customer_dba_name", None)
    locations = []

    total_delivery = 0.0
    total_supply = 0.0
    total_tax = 0.0
    total_usage = 0.0
    charges_found_in_entries = False
    
    electricity = check_yearly_estimated_usage(base_data_path, raw_entry['issuer'], raw_entry['filename'], electricity)
    if electricity.get('aggregated_yearly_estimated_usage') is not None and isinstance(electricity['aggregated_yearly_estimated_usage'], dict):
        for k, v in electricity['aggregated_yearly_estimated_usage'].items():
            try:
                dt = datetime.strptime(k, "%B %Y")
                month_key = dt.strftime("%Y-%m")
                aggregated_usage_history[month_key] += v
            except (ValueError, TypeError):
                continue

    for entry in electricity["service_entries"].values():
        if not isinstance(entry, dict):
            continue

        unit = entry.get("unit")
        if unit:
            units.add(unit)

        usage_history = []
        yearly_estimates = entry.get("yearly_estimated_usage") or {}

        for k, v in yearly_estimates.items():
            try:
                dt = datetime.strptime(k, "%B %Y")
                month_key = dt.strftime("%Y-%m")
                usage_history.append({"month": month_key, "usage": v})
                aggregated_usage_history[month_key] += v
            except (ValueError, TypeError):
                continue

        current_usage = entry.get("usage") or 0.0
        total_usage += current_usage

        entry_charges = entry.get("charges")
        if entry_charges:
            charges_found_in_entries = True
            total_delivery += try_parse_amount(entry_charges.get("delivery"))
            total_supply += try_parse_amount(entry_charges.get("supply"))
            total_tax += try_parse_amount(entry_charges.get("tax"))

        locations.append({
            "accountNumber": entry.get("account_number", None),
            "serviceAddress": entry.get("service_address", None),
            "meterNumber": entry.get("meter_number", None),
            "commodity": commodity,
            "rateClass": electricity.get("rate_class", None),
            "unit": entry.get("unit", None),
            "usageHistory": usage_history if usage_history else None,
            "currentUsage": current_usage,
            "notes": {}
        })

    top_level_usage_history = [
        {"month": month, "usage": round(usage, 2)}
        for month, usage in sorted(aggregated_usage_history.items())
    ]

    unit_value = units.pop() if len(units) == 1 else None

    if not charges_found_in_entries:
        total_delivery = try_parse_amount(electricity.get("delivery_charge"))
        total_supply = try_parse_amount(electricity.get("supply_charge"))
        total_tax = try_parse_amount(electricity.get("tax_charge"))
        
    total_usage = total_usage if billed_usage is None else billed_usage

    return {
        "documentId": raw_entry.get("filename", None),
        "issuer": issuer,
        "documentType": "sampleBill",
        "commodity": commodity,
        "unit": unit_value,
        "statementDate": statement_date_str,
        "customerName": customer_name,
        "reportType": "savings",
        "deliveryCharge": round(total_delivery, 2),
        "supplyCharge": round(total_supply, 2),
        "taxCharge": round(total_tax, 2),
        "totalUsage": round(total_usage, 2),
        "deliveryRate": round(total_delivery / total_usage, 6) if total_usage else None,
        "supplyRate": round(total_supply / total_usage, 6) if total_usage else None,
        "taxRate": round(total_tax / total_usage, 6) if total_usage else None,
        "usageHistory": top_level_usage_history,
        "locations": locations
    }


def create_final_bill_result(issuer: str, variation: str, variation_result: dict):
    # ✅ Proceed if file is in correct_docs
    results = {}
    for commodity_var in ["electricity", "natural_gas"]:
        transformed = transform_bill_entry(BASE_PATH, variation_result, commodity_var, issuer)
        if transformed:
            results[commodity_var] = transformed
        
    return results