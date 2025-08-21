def get_sytem_message_checking_count_custom(type, issuer):
    general_instructions = []
    custom_instructions_by_issuer = {
        "COMED": [
            "You may find multiple entries for a meter. These entries may have different reading types like 'On Pk/Peak', 'Off Pk/Peak', 'Total'. In such a scenario, only consider the 'total' reading type as this comprises of on peak, off peak, and some other info.",
            "Extract all meters with reading type 'Total ...'. Do not miss anything.",
        ]
    }

    custom_instructions_text = "\n".join(
        [
            f"- {inst}"
            for inst in custom_instructions_by_issuer.get(issuer)
            or general_instructions
        ]
    )
    custom_instructions_text = (
        f"Here are some additional instructions knowledge points for you to keep in mind:\n{custom_instructions_text}\n\n"
        if len(custom_instructions_text.strip()) > 0
        else ""
    )

    system_message_localize = f"""
You are a reliable document analysis assistant specialized in extracting structured data from utility bills. 

Always follow these rules:
- Respond only in valid JSON when requested.
- Do not include explanations or extra text unless explicitly asked.
- Be accurate and conservative when identifying values — do not guess.
- If multiple entries exist (e.g., meters, accounts), list each one as a separate item in a JSON array.
- When extracting usage, dates, or identifiers, ensure values are clearly supported by the document content.


Please analyze this utility bill and return a dictionary of distinct {type} service entries. 
Each entry represents a unique meter, service reference, or unmetered device group.

1. Determine the bill type(s): electricity, natural gas, or both.
2. Locate the yearly (month-based) usage breakdown for {type} usage:
   -Extract a month-by-month usage table only if a clearly structured table or list of monthly {type} usage values for the last year is present. Set yearly_usage_breakdown.type to "table".
   -If no such table or list exists—for example, if only totals, a single month’s value, or an unlabeled table is provided—set yearly_usage_breakdown to null.
   -Do not infer or fabricate month-by-month data.
   -If both a month-based usage table and a plot/image of historical usage are present, extract only the table and set the type as "table".
   -If on-peak and off-peak breakdowns are shown in separate month-based tables or lists, create separate service entries for each, with usage_period as "on-peak", "off-peak", or "regular" as labeled.

Never extract or invent month-by-month usage values unless they are explicitly shown.
3. Extract these additional fields:
   • {type} unit(s)  (e.g. kWh, Therms, CCF, MMBTU)  
   
   • Account number(s)  
   • Service address(es): Extract from service usage part not foot note  
   • Meter number(s) 
   • Service reference number(s) 
   
4. If supply charge, delivery charge or tax charge are listed based on service entries rather than bill based extract those as well
   
{custom_instructions_text}
For each service entry, return the following fields in this exact JSON format:

{{
  "service_entry_1": {{
    "account_number": "<string or null>",
    "service_reference": "<string or null>",
    "meter_number": "<string or null>",
    "usage": <number>,
    "unit": "<string or null>",
    "service_address": "<string>",
    "usage_period":  "<string>"
    "delivery_charge":        <string> | null,
    "supply_charge":          <string> | null,
    "tax_charge":             <string> | null
    "yearly_usage_breakdown": {{ # month-by-month usage location
      "type": "table" | "text" | "image" | null,
      "usage_period":  "<string or null>"
      "content": "<table text, text excerpt, image path, or null>"
    }}
  }},
  ...
}}

Only include {type} usage. Do not include summaries or unrelated sections.
Monthly breakdown maybe represented in two lines have both of them
If no monthly breakdown is available for a service entry, set the `"yearly_usage_breakdown"` field to `null`.
Respond only with the JSON output.

if bill doesn't include {type} invoice information then:
Output a JSON object like this:
{{ "Pass": "Pass" }}

"""
    return system_message_localize


def get_sytem_message_checking_count(type):

    system_message_localize = f"""
You are a reliable document analysis assistant specialized in extracting structured data from utility bills. 

Always follow these rules:
- Respond only in valid JSON when requested.
- Do not include explanations or extra text unless explicitly asked.
- Be accurate and conservative when identifying values — do not guess.
- If multiple entries exist (e.g., meters, accounts), list each one as a separate item in a JSON array.
- When extracting usage, dates, or identifiers, ensure values are clearly supported by the document content.


Please analyze this utility bill and return a dictionary of distinct {type} service entries. 
Each entry represents a unique meter, service reference, or unmetered device group.

1. Determine the bill type(s): electricity, natural gas, or both.
2. Locate the yearly (month-based) usage breakdown for {type} usage:
   -Extract a month-by-month usage table only if a clearly structured table or list of monthly {type} usage values for the last year is present. Set yearly_usage_breakdown.type to "table".
   -If no such table or list exists—for example, if only totals, a single month’s value, or an unlabeled table is provided—set yearly_usage_breakdown to null.
   -Do not infer or fabricate month-by-month data.
   -If both a month-based usage table and a plot/image of historical usage are present, extract only the table and set the type as "table".
   -If on-peak and off-peak breakdowns are shown in separate month-based tables or lists, create separate service entries for each, with usage_period as "on-peak", "off-peak", or "regular" as labeled.

Never extract or invent month-by-month usage values unless they are explicitly shown.
3. Extract these additional fields:
   • {type} unit(s)  (e.g. kWh, Therms, CCF, MMBTU)  
   
   • Account number(s)  
   • Service address(es): Extract from service usage part not foot note  
   • Meter number(s) 
   • Service reference number(s) 
   
4. If supply charge, delivery charge or tax charge are listed based on service entries rather than bill based extract those as well
   
For each service entry, return the following fields in this exact JSON format:

{{
  "service_entry_1": {{
    "account_number": "<string or null>",
    "service_reference": "<string or null>",
    "meter_number": "<string or null>",
    "usage": <number>,
    "unit": "<string or null>",
    "service_address": "<string>",
    "usage_period":  "<string>"
    "delivery_charge":        <string> | null,
    "supply_charge":          <string> | null,
    "tax_charge":             <string> | null
    "yearly_usage_breakdown": {{ # month-by-month usage location
      "type": "table" | "text" | "image" | null,
      "usage_period":  "<string or null>"
      "content": "<table text, text excerpt, image path, or null>"
    }}
  }},
  ...
}}

Only include {type} usage. Do not include summaries or unrelated sections.
Monthly breakdown maybe represented in two lines have both of them
If no monthly breakdown is available for a service entry, set the `"yearly_usage_breakdown"` field to `null`.
Respond only with the JSON output.

if bill doesn't include {type} invoice information then:
Output a JSON object like this:
{{ "Pass": "Pass" }}

"""
    return system_message_localize


def get_user_prompt_checking_count(md_content):
    user_prompt = f"""
Please extract the needed information from below bill content
-------------------------
BILL CONTENT:
{md_content}
-------------------------


"""
    return user_prompt


def get_service_entry_reasoning_prompt(type):
    return f"""
You are an expert utility bill analyst. For each {type} service entry (location/meter/account), extract the following fields, always giving your reasoning and confidence before the value.

**Fields to extract for each service entry:**
- account_number
- service_reference
- meter_number
- usage (numeric value)
- unit (e.g., kWh, Therms)
- service_address
- usage_period ("on-peak", "off-peak", or "regular" only)
- delivery_charge (if its service entry level)
- supply_charge  (if its service entry level)
- tax_charge  (if its service entry level)
- yearly_usage_breakdown:
    - type ("table", "text", "image", or null)
    - usage_period ("on-peak", "off-peak", "regular", or null)
    - content (the table, text, or image path as found in the bill)
    
**Descriptions**
account_number:
  The unique customer account number associated with this service entry, as labeled in the bill.
  If not present, set to null.

service_reference:
  Any secondary identifier or reference number (sometimes called "service reference", "service ID", "reference number", etc.) specific to this service entry.
  If not present, set to null.

meter_number:
  The meter number associated with this service entry/location.
  If not present, set to null.

usage (numeric value):
  The numeric usage amount for this service entry, for the relevant period, as shown in the bill.
  If multiple values are present, extract the one matching the current usage period and service entry.
  If not present, set to null.

unit (e.g., kWh, Therms):
  The unit for the usage value (e.g., "kWh", "Therms", "CCF", etc.) as stated in the bill.
  If not present, set to null.

service_address:
  The full service address associated with this service entry/location, as shown in the bill (not a billing or mailing address).
  If not present, set to null.

usage_period ("on-peak", "off-peak", or "regular" only):
  The type of usage period this entry represents.
  Use "on-peak", "off-peak", or "regular" as labeled.
  If the bill does not specify, set to "regular" or null as appropriate.

delivery_charge (if service entry level):
  The delivery-related charge for this service entry (e.g., "Delivery Charge", "Distribution Charge"), only if it is clearly listed for this entry/location in the bill (not a bill-level total).
  If not present at service entry level, set to null.

supply_charge (if service entry level):
  The supply-related charge for this service entry (e.g., "Supply Charge", "Generation Charge"), only if it is clearly listed for this entry/location in the bill (not a bill-level total).
  If not present at service entry level, set to null.

tax_charge (if service entry level):
  The tax-related charge for this service entry (e.g., "Tax", "Energy Tax", "Sales Tax"), only if it is clearly listed for this entry/location in the bill (not a bill-level total).
  If not present at service entry level, set to null.

yearly_usage_breakdown:
  type: Indicates the format of the breakdown: "table", "text", "image", or null.
  usage_period: "on-peak", "off-peak", "regular", or null—corresponding to the period for the usage breakdown.
  content: 2. Locate the yearly (month-based) usage breakdown for {type} usage:
   -Extract a month-by-month usage table only if a clearly structured table or list of monthly {type} usage values for the last year is present. Set yearly_usage_breakdown.type to "table".
   -If no such table or list exists—for example, if only totals, a single month’s value, or an unlabeled table is provided—set yearly_usage_breakdown to null.
   -Do not infer or fabricate month-by-month data.
   -If both a month-based usage table and a plot/image of historical usage are present, extract only the table and set the type as "table".
   -If on-peak and off-peak breakdowns are shown in separate month-based tables or lists, create separate service entries for each, with usage_period as "on-peak", "off-peak", or "regular" as labeled.
   - Get only historical usage for total monthly usages do not extract average daily usage


If any of these charges are not present at the service entry level (i.e., only at bill-level), set the value to null and provide reasoning.

**Instructions:**
- Group all findings under each service entry (use a markdown heading for each).
- For every field:
    - **First:** Give concise reasoning (reference bill location/section/table, explain clues, and note your confidence: high/medium/low).
    - **Second:** Output the extracted value (or null), preserving exact tables/blocks for structured fields.
- If a field is ambiguous or missing, explain in the reasoning and return null for value.
- Only extract and reason about service entry-level (location-level) data. Ignore bill-level info.

**Output Format Example:**

### Service Entry: Meter 112312 (10 Main St, Account: 12345)

- **account_number:**  
    - Reasoning: Found in "Account #" column of "Service Details" table, page 1. Confidence: high.  
    - Value: 12345
- **service_reference:**  
    - Reasoning: Labeled as "Service Ref." near meter number in usage table. Confidence: medium.  
    - Value: 87654321
- **meter_number:**  
    - Reasoning: "Meter" column, matches service address. Confidence: high.  
    - Value: 112312
- **usage:**  
    - Reasoning: "Usage" field in monthly table for this entry. Confidence: high.  
    - Value: 1200
- **unit:**  
    - Reasoning: Table header says "kWh". Confidence: high.  
    - Value: kWh
- **service_address:**  
    - Reasoning: Table and service block for Meter 112312. Confidence: high.  
    - Value: 10 Main St
- **usage_period:**  
    - Reasoning: This row is labeled "on-peak" in the usage table for Meter 112312. Confidence: high.  
    - Value: on-peak
- **delivery_charge:**  
    - Reasoning: No delivery charge found at this entry level. Confidence: high.  
    - Value: null
- **supply_charge:**  
    - Reasoning: Found in "Supply Charges" table, row for Meter 112312, labeled as on-peak. Confidence: high.  
    - Value: $32.00
- **tax_charge:**  
    - Reasoning: Not present for this entry. Confidence: high.  
    - Value: null
- **yearly_usage_breakdown:**  
    - Reasoning: "Monthly Usage" table for Meter 112312, covers on-peak period. Confidence: high.  
    - type: table  
    - usage_period: on-peak  
    - content:  
      ```
      | Month   | kWh  | Bill Amount |
      |---------|------|-------------|
      | Jan-24  | 1200 | $120.33     |
      | Feb-24  | 1100 | $110.23     |
      ...
      ```

- **Ambiguities/conflicts:**  
    - Reasoning: None for this entry.  
    - Value: None

---

**For each service entry, use the above structure: Reasoning first, then value.  
usage_period should be "on-peak", "off-peak", or "regular"—never a date or time period. Return null with explanation if not found. Preserve tables/blocks exactly as in bill content.**


"""


def get_sytem_message(type, issuer):
    GENERAL_PROMPT = f"""
You are a smart assistant that parses a utility‐bill Markdown file and extracts {type} information. Your tasks:

1. Determine the bill type(s): electricity, natural gas, or both.
2. Extract the statement issue date. If there is no statement issue date use due date as statement date.
3. Extract these additional fields:
   • Customer (DBA) name  
   • Billed Usage  
   • Rate class (e.g. "0–100 kWh","117") -  Only extract the rate class without prefix like 'delivery rate, distribution rate, rate, etc.'
   • Delivery Charge — if there is no delivery charge label but sum calculations to get that put (aggregated tag near value):
     - Transmission Service
     - Distribution Service
     - Customer Charge
     - Demand Charges (if applicable)
     - Infrastructure, Metering, Grid Access Fees
     These line items are often labeled with words like “delivery,” “distribution,” “transmission,” “customer,” “meter,” or “service.”

   • Supply Charge — if there is no supply charge label but sum calculations to get that put(aggregated tag near value):
     - Generation Charges
     - Energy Supply
     - Electric/Natural Gas Commodity Charges
     - Purchased Power Adjustments (PPA)
     - Supply Riders or Adjustments
     These items often contain terms like “supply,” “generation,” “energy,” “commodity,” or “PPA.”

   • Tax Charge — if there is no tax charge label but sum calculations to get that put(aggregated tag near value):
     - Sales Tax
     - Franchise Fees
     - Regulatory Fees
     These lines typically include the word "tax", "fee", or "surcharge".
     
If multiple line items contribute to a charge (like delivery, supply, or taxes), extract and sum them. Output the total as a string with the dollar symbol (e.g., '$182.99').

Output a JSON object like this:
if bill includes {type} bill information then:

{{
  "bill_type":            ["electricity", "natural gas"], 
  "extracting":           "{type}",
  "statement_date": {{
    "day":     <int> | null,
    "month":   <int> | null,
    "year":    <int> | null
  }},
  "customer_dba_name":      <string> | null,
  "billed_usage":           <float>  | null,
  "rate_class":             <string> | null,
  "delivery_charge":        <string> | null,
  "supply_charge":          <string> | null,
  "tax_charge":             <string> | null
}}



if bill doesn't include {type} bill information then:
Output a JSON object like this:
{{ "Pass": "Pass" }}
"""

    COMED_PROMPT = f"""
You are a smart assistant that parses a utility‐bill Markdown file and extracts {type} information. Your tasks:

1. Determine the bill type(s): electricity, natural gas, or both.
2. Extract the statement issue date. If there is no statement issue date use due date as statement date.
3. Extract these additional fields:
   • Customer (DBA) name  
   • Billed Usage  
   • Rate class (e.g. "0–100 kWh","117") -  Only extract the rate class without prefix like 'delivery rate, distribution rate, rate, etc.'
   • Delivery Charge — The delivery services charges if mentioned in the document.
   • Supply Charge — The supply services fees if mentioned in the document.
   • Tax Charge — The tax charge as mentioned in the bill generally as 'Taxes and Other' or 'Taxes & Fees'.
       
The charges (delivery, supply, or taxes) may be present with total value with their breakdown. So fetch the total value only. 
For example: The text is:
```
**Commercial Hourly - 100 kW to 400 kW**
**$1,219.10**

### Delivery Services - ComEd

Customer Charge 16.87
Standard Metering Charge 6.26
Distribution Facilities Charge 2.20 kW X 8.59000 18.90
IL Electricity Distribution Charge 1,731 kWh X 0.00131 2.27
Meter Lease 5.51
Nonstandard Facilities Charge 1,169.29

### Taxes and Other

$83.45
Environmental Cost Recovery Adj 1,731 kWh X 0.00052 0.90
Renewable Portfolio Standard 1,731 kWh X 0.00502 8.69
Zero Emission Standard 1,731 kWh X 0.00195 3.38
Carbon-Free Energy Resource Adj 1,731 kWh X 0.01241 21.48
Energy Efficiency Programs 1,731 kWh X 0.00461 7.98
Energy Transition Assistance 1,731 kWh X 0.00072 1.25
Franchise Cost $1,214.51 X 2.00700% 24.38
State Tax 5.71
```

Then Delivery Charges = $1,219.10, and Tax-Related Charges = $83.45

Output a JSON object like this:
if bill includes {type} bill information then:

{{
  "bill_type":            ["electricity", "natural gas"], 
  "extracting":           "{type}",
  "statement_date": {{
    "day":     <int> | null,
    "month":   <int> | null,
    "year":    <int> | null
  }},
  "customer_dba_name":      <string> | null,
  "billed_usage":           <float>  | null,
  "rate_class":             <string> | null,
  "delivery_charge":        <string> | null,
  "supply_charge":          <string> | null,
  "tax_charge":             <string> | null
}}



if bill doesn't include {type} bill information then:
Output a JSON object like this:
{{ "Pass": "Pass" }}
"""

    prompts_by_issuer = {
        "COMED": COMED_PROMPT,
    }
    return (prompts_by_issuer.get(issuer) or GENERAL_PROMPT).strip()


def get_sytem_message_pre_bill(type, issuer):
    GENERAL_PROMPT = f"""
You are a smart assistant analyzing a utility-bill in Markdown format. Focus **only** on the **{type}** portion of the bill. For each section below, extract the requested data, explain how you found or classified it, and—for delivery, supply, and tax—list each line item **one by one** and then perform a **step-by-step** sum to avoid arithmetic mistakes.

---

# 🔍 {type.capitalize()} Bill Analysis

## 1. Bill Type  
- **What to extract:** All services on the bill (electricity, natural gas, or both).  
- **Instructions:** State both if present, then confirm you’re focusing on **{type}** (e.g., “kWh” for electricity, “therms/ccf” for gas). Explain how you determined this.

---

## 2. Statement Issue Date  
- **What to extract:** Bill issue date (not due date).  
- **Instructions:** Locate the “Statement Date” label, confirm it applies to **{type}**, and explain where you found it.

---

## 3. Statement Due Date  
- **What to extract:** Bill due date.  
- **Instructions:** Locate the “Due Date” label, confirm it applies to **{type}**, and explain where you found it.

---

## 4. Customer (DBA) Name  
- **What to extract:** The billed customer or business name.  
- **Instructions:** Find the DBA in the mailing block or payment stub and explain how you recognized it.

---

## 5. **Billed Usage**
- **What to extract:** The *total usage* for the current billing period (in {type}), as actually billed.
- **Instructions:**
    - **First**, look for a clear “Usage,” “Billed Usage,” or “Total Usage” field for this period.
    - **If not found**, check explanations/descriptions for supply or delivery charges. If you find text like “This charge is based on X {type} used this period,” extract X as the billed usage and quote the text.
    - **Ignore** any values related to “annual,” “previous,” “average,” “estimated,” or “projected” usage.
    - **If there are multiple possible values,** choose the one that is specifically billed for this period and explain your reasoning.
    - Report both the number and its unit (e.g., “2,345 kWh”).
    - If still not found, write “Not found” and explain why.
---

## 6. Rate Class  
- **What to extract:** Rate class/tariff for **{type}** (e.g., “SG Secondary General”,“117”).  
- **Instructions:** Spot the “Rate:” header in the **{type}** service details and explain your reasoning.

---

## 7. Delivery Charges  
- **What to extract: Extract the {type} delivery services charge only.

- **Instructions:
    * If a **bill-level total delivery charge** is explicitly labeled (e.g., "Total Delivery Charge"), extract it directly.
    * If not, and there are **multiple service entries**, extract the **delivery charge for each service** (if clearly labeled) and **sum them**.
    * Ignore any charges that are delivery-related but have different names (e.g., "Distribution Charge", "Transmission Fee").
    * If no exact match is found, return "not_found".
---

## 8. Supply Charges  
- **Goal:** Extract the {type} supply charge.

- **Instructions:**
    * If a **bill-level total supply charge** is explicitly labeled (e.g., "Total Supply Charge", "Total Energy Charges"), extract it directly.
    * If not, and there are **multiple service entries**, extract the **supply charge for each service** (if clearly labeled) and **sum them**.
    * If no labeled totals exist, look for the **first section** that clearly relates to energy supply (e.g., "Supply Charge", "Energy Charges", "Generation Charges", or supplier sections like "<Issuer> Energy Charges") and **sum the line items** in that section.
    * Do **not include** delivery, distribution, metering, or customer charges.
    * If no valid supply charge is found, return `"not_found"`.


---

## 9. Tax-Related Charges  
- **What to extract:** Extract all charges that represent taxes related to **{type}** usage. This includes any line item with names such as:
  - "tax"
  - "utility tax"
  - "consumption tax"
  - "sales and use surcharge"
  - or other government-imposed surcharges that are applied based on electricity/gas usage.

- **Instructions:**  
  - Match **case-insensitively** and include any item that clearly functions as a **government-imposed tax**, even if not explicitly labeled “tax”.
  - Include city, municipal, or state surcharges if they apply to **{type}** usage.
  - If unsure whether an item is tax, assume it is **unless another utility type (e.g., gas or water) is explicitly mentioned**.
  - List each tax-related charge **one by one**, showing the name and amount.
  - Then calculate a **step-by-step total sum**.
  - If no tax-related charges can be found, write `"not_found"` and explain why.
---

IMPORTANT: If its not about {type} do not extract it

## 10. Summary of {type.capitalize()} Findings

| Field                            | Value            |
|----------------------------------|------------------|
| Bill Type                        |                  |
| Statement Issue Date             |                  |
| Customer (DBA) Name              |                  |
| Billed Usage for {type}          |                  |
| Rate Class for {type}            |                  |
| Total Delivery Charge for {type} |                  |
| Total Supply Charge for {type}   |                  |
| Total Tax Charge for {type}      |                  |

Fill in the table with your extracted and summed values  for {type}. If any item is missing, write “Not found” and explain why.
"""

    COMED_PROMPT = f"""
You are a smart assistant analyzing a utility-bill in Markdown format. Focus **only** on the **{type}** portion of the bill. For each section below, extract the requested data, explain how you found or classified it, and—for delivery, supply, and tax—list each line item **one by one** and then perform a **step-by-step** sum to avoid arithmetic mistakes.

---

# 🔍 {type.capitalize()} Bill Analysis

## 1. Bill Type  
- **What to extract:** All services on the bill (electricity, natural gas, or both).  
- **Instructions:** State both if present, then confirm you’re focusing on **{type}** (e.g., “kWh” for electricity, “therms/ccf” for gas). Explain how you determined this.

---

## 2. Statement Issue Date  
- **What to extract:** Bill issue date (not due date).  
- **Instructions:** Locate the “Statement Date” label, confirm it applies to **{type}**, and explain where you found it.

---

## 3. Statement Due Date  
- **What to extract:** Bill due date.  
- **Instructions:** Locate the “Due Date” label, confirm it applies to **{type}**, and explain where you found it.

---

## 4. Customer (DBA) Name  
- **What to extract:** The billed customer or business name.  
- **Instructions:** Find the DBA in the mailing block or payment stub and explain how you recognized it.

---

## 5. **Billed Usage**
- **What to extract:** The *total usage* for the current billing period (in {type}), as actually billed.
- **Instructions:**
    - **First**, look for a clear “Usage,” “Billed Usage,” or “Total Usage” field for this period.
    - **If not found**, check explanations/descriptions for supply or delivery charges. If you find text like “This charge is based on X {type} used this period,” extract X as the billed usage and quote the text.
    - **Ignore** any values related to “annual,” “previous,” “average,” “estimated,” or “projected” usage.
    - **If there are multiple possible values,** choose the one that is specifically billed for this period and explain your reasoning.
    - Report both the number and its unit (e.g., “2,345 kWh”).
    - If still not found, write “Not found” and explain why.
---

## 6. Rate Class  
- **What to extract:** Rate class/tariff for **{type}** (e.g., “SG Secondary General”,“117”).  
- **Instructions:** Spot the “Rate:” header in the **{type}** service details and explain your reasoning.

---

## 7. Delivery Charges  
- **What to extract: Extract the {type} delivery services only.

- **Instructions:
    * Only extract charges and sum explicitly labeled as "Delivery Charge".
    * Ignore any charges that are delivery-related but have different names (e.g., "Distribution Charge", "Transmission Fee").
    * If no exact match is found, return "not_found".
---

## 8. Supply Charges  
- **What to extract:** Extract the **{type}** supply services only.

- **Instructions:**
  * Only extract the total supply services fees if mentioned.
  * Ignore any charges that are supply-related but have different names (e.g., **"Generation Charge"**, **"Energy Cost"**).
  * If no exact match is found, return **"not_found"**.

---

## 9. Taxes, Fees, and Other
- **What to extract:** Extract the total fees mentioned generally under taxes and fees or taxes and others related to **{type}** usage. 

---

The charges (delivery, supply, or taxes) may be present with total value with their breakdown. So fetch the total value only. 
For example: The text is:
```
$1,219.10

### Delivery Services - ComEd

Customer Charge 16.87
Standard Metering Charge 6.26
Distribution Facilities Charge 2.20 kW X 8.59000 18.90
IL Electricity Distribution Charge 1,731 kWh X 0.00131 2.27
Meter Lease 5.51
Nonstandard Facilities Charge 1,169.29

### Taxes and Other

$83.45
Environmental Cost Recovery Adj 1,731 kWh X 0.00052 0.90
Renewable Portfolio Standard 1,731 kWh X 0.00502 8.69
Zero Emission Standard 1,731 kWh X 0.00195 3.38
Carbon-Free Energy Resource Adj 1,731 kWh X 0.01241 21.48
Energy Efficiency Programs 1,731 kWh X 0.00461 7.98
Energy Transition Assistance 1,731 kWh X 0.00072 1.25
Franchise Cost $1,214.51 X 2.00700% 24.38
State Tax 5.71
```

Then Delivery Charges = $1,219.10, and Tax-Related Charges = $83.45

IMPORTANT: If its not about {type} do not extract it

---

## 10. Summary of {type.capitalize()} Findings

| Field                            | Value            |
|----------------------------------|------------------|
| Bill Type                        |                  |
| Statement Issue Date             |                  |
| Customer (DBA) Name              |                  |
| Billed Usage for {type}          |                  |
| Rate Class for {type}            |                  |
| Total Delivery Charge for {type} |                  |
| Total Supply Charge for {type}   |                  |
| Total Tax Charge for {type}      |                  |

Fill in the table with your extracted and summed values  for {type}. If any item is missing, write “Not found” and explain why.
"""

    prompts_by_issuer = {
        "COMED": COMED_PROMPT,
    }
    return (prompts_by_issuer.get(issuer) or GENERAL_PROMPT).strip()


def get_cls_usr_prompt(md_text):

    usr_msg = f"""
    You are given the full text (or markdown) of a utility bill.
    Classify its structure and data sources.

    Steps:
    1. Count unique account numbers → accountCount.
    2. Count unique service addresses → addressCount.
    3. Count distinct commodities (e.g. electricity, natural_gas) → commodityCount.
    4. Set multipleCommodities to true if commodityCount > 1, else false.
    5. Determine the structuralClass (choose one of):
      - one_to_one
      - one_account_multiple_addresses
      - one_address_multiple_accounts
    6. Determine whether usage is aggregated:
      - If there is only one usage history covering all accounts/addresses, usageAggregated: true
      - Otherwise, usageAggregated: false
    7. Determine the usageSource:
      -  First look at if any markdown table for the usage in months is available or not
      - "table" if usage values come from a table or labeled graph
      - if tehre is no table but a "graph" of usage values than "graph"

    Output only this JSON:
    ```json
    {{
      "structuralClass": "<one_of: one_to_one, one_account_multiple_addresses, one_address_multiple_accounts>",
      "accountCount": <integer>,
      "addressCount": <integer>,
      "commodityCount": <integer>,
      "multipleCommodities": <true|false>,
      "usageAggregated": <true|false>,
      "usageSource": "<table|graph>"
    }}

    Here is the bill text:

    {md_text}

    """

    return usr_msg


gpt_preprocess_prompt = """
You are a highly accurate assistant trained to extract structured utility bill data for energy savings and budget reporting.

You are given a utility bill PDF. Your task is to:

✅ Extract **all relevant billing information**  
❌ Discard irrelevant sections like customer service numbers, advertisements, or general tips.

---

# 🗝 Instructions

If the PDF contains **multiple bills** (e.g. more than one statement or account), split them clearly using:

```markdown
# Bill 1
```

…and increment for each new one.

Inside each bill, preserve the document’s structure:  
⚠️ If it contains multiple pages for different accounts, meter numbers, or service reference numbers, keep them grouped and labeled using subheadings.

---

# 🧹 For Each Bill, Extract:

## ## Basic Information
- Statement Date (or Billing Date)
- Customer DBA Name
- Each **Account Number**
- Corresponding **Service Address**: Extract the exact address from usage part
- Service reference number
- Meter Number
- Commodity type (e.g., electricity, natural gas)
- Rate Class: Only extract the rate class without prefix like 'delivery rate, distribution rate, rate, etc.'
- Unit (e.g., kWh, Therms)

---

## ## Monthly Usage (if available)
If any table or chart showing 12–13 months of usage, extract it as below. Keep the order of months
Use the statement date to understand the year:

```markdown
| Month     | Usage |
|-----------|-------|
| Dec 2023  | 3400  |
| Jan 2024  | 3600  |
| Feb 2024  | 3200  |
...
```

📌 If usage is aggregated across addresses or accounts, make that clear and group accordingly.

---

## ## Current Usage
Pull the usage value billed in the current period.
Label it clearly:

```markdown
**Current Usage**: 5074 kWh
```

---

## ## Charges and Rate Breakdown
- Delivery Charge
- Supply Charge
- Tax Charge
---

## ## Per-Account or Per-Page Structure
If the bill includes **multiple account sections** (e.g., each on its own page), retain this grouping. Use:

```markdown
### Account: <account number>
### Address: <service address>
```

…then include the usage, meter number etc., and charges for that segment.

---

# ⛔️ Ignore
- Energy-saving tips
- Marketing content
- Definitions/glossary unless directly connected to bill charges

---

# ✅ Output Format Example

```markdown
# Bill 1

## Statement Date: May 12, 2024  
## Customer DBA: City of North Haven

### Account: 100023910009  
### Address: 150 Elm St, North Haven, CT  
### Commodity: electricity  
### Unit: kWh  
### Service Referance Number: 405212002
### Meter Number: D007789  
### Rate Class: General Service - 030

#### Usage (13-month summary)
| Month     | Usage |
|-----------|-------|
| May 2023  | 3400  |
| Jun 2023  | 3600  |
...

#### Current Usage: 3410 kWh

#### Charges
- Delivery: $145.76  
- Supply: $380.10  
- Tax: $12.23  
---
# Bill 2
...
```

Please extract the data ***exactly same characters*** from related parts of the pdf. If any field is missing, label it as `_Missing_`. Format your output as clean, readable Markdown using the instructions above.

"""


gpt_preprocess_prompt2 = """
You are a highly accurate assistant trained to extract structured utility bill data for energy savings and budget reporting.

You are given a utility bill PDF. Your task is to:

✅ Extract **all relevant billing information**  
❌ Discard irrelevant sections like customer service numbers, advertisements, or general tips.

---

# 🗝 Instructions

If the PDF contains **multiple bills** (e.g. more than one statement or account), split them clearly using:

```markdown
# Bill 1
```

…and increment for each new one.

Inside each bill, preserve the document’s structure:  
⚠️ If it contains multiple pages for different accounts, meter numbers, or service reference numbers, keep them grouped and labeled using subheadings.

---

# 🧹 For Each Bill, Extract:

## ## Basic Information
- Statement Date (or Billing Date)
- Customer DBA Name
- Each **Account Number**
- Corresponding **Service Address**: Extract the exact address from usage part
- Service reference number
- Meter Number
- Commodity type (e.g., electricity, natural gas)
- Rate Class: Only extract the rate class without prefix like 'delivery rate, distribution rate, rate, etc.'
- Unit (e.g., kWh, Therms)

---

## Monthly Usage (if available)
Extract the monthly usage exactly as shown in the PDF table or chart. Maintain the original month sequence. The latest month should always match the statement month. Clearly verify month-to-usage accuracy directly from the PDF.

- If the year is explicitly mentioned, include it as below:

```markdown
| Month     | Usage |
|-----------|-------|
| Dec 2022  | 3400  |
| Jan 2023  | 3600  |
| Feb 2023  | 3200  |
...
```

- If the year is **not** explicitly mentioned, keep the month order as its and add 2022 and 2023 years based on months.
- The top months should be 2022 if there is following january it should become 2023:

```markdown
| Month     | Usage |
|-----------|-------|
| Dec 2022  | 3400  |
| Jan 2023  | 3600  |
| Feb 2023  | 3200  |
...
```

**Important:** The last month in the table must align exactly with the statement month indicated in the bill. Carefully verify each month and usage value exactly as presented in the PDF without assumptions or rearrangements.

---




📌 If usage is aggregated across addresses or accounts, make that clear and group accordingly.

---

## ## Current Usage
Pull the usage value billed in the current period.  
Label it clearly:

```markdown
**Current Usage**: 5074 kWh
```

---

## ## Charges and Rate Breakdown
- Delivery Charge
- Supply Charge
- Tax Charge

---

## ## Per-Account or Per-Page Structure
If the bill includes **multiple account sections** (e.g., each on its own page), retain this grouping. Use:

```markdown
### Account: <account number>
### Address: <service address>
```

…then include the usage, meter number etc., and charges for that segment.

---

# ⛔️ Ignore
- Energy-saving tips
- Marketing content
- Definitions/glossary unless directly connected to bill charges

---

# ✅ Output Format Example

```markdown
# Bill 1

## Statement Date: May 12, 2024  
## Customer DBA: City of North Haven

### Account: 100023910009  
### Address: 150 Elm St, North Haven, CT  
### Commodity: electricity  
### Unit: kWh  
### Service Reference Number: 405212002  
### Meter Number: D007789  
### Rate Class: General Service - 030

#### Usage (13-month summary)
| Month     | Usage |
|-----------|-------|
| Dec 2022  | 3400  |
| Jan 2023  | 3600  |
| Feb 2023  | 3200  |
...

#### Current Usage: 3410 kWh

#### Charges
- Delivery: $145.76  
- Supply: $380.10  
- Tax: $12.23  

---
# Bill 2
...
```

Please extract the data ***exactly same characters*** from related parts of the PDF. If any field is missing, label it as `_Missing_`. Format your output as clean, readable Markdown using the instructions above.
"""
gpt_preprocess_prompt3 = """
You are an accurate assistant trained to extract structured data from utility bill PDFs for energy savings and budget reporting.

**Task:** Extract all relevant billing information from the PDF. Ignore customer service contacts, advertisements, general tips, and glossary definitions unless directly linked to charges.

## Instructions

- If multiple bills appear, clearly separate each:
```markdown
# Bill 1
```
Increment the number for each bill.

- Maintain original document structure. Group and label multiple accounts, meters, or service references with subheadings.

## Data to Extract per Bill

### Basic Information
- Statement (Billing) Date
- Customer DBA Name
- Account Number
- Service Address (exact address from usage details)
- Service Reference Number
- Meter Number
- Commodity Type (electricity, natural gas)
- Rate Class (exclude prefixes like "delivery rate")
- Unit (e.g., kWh, Therms)

### Monthly Usage
Extract exactly as in PDF. Maintain month sequence; the latest month must match statement month.

- If the year is mentioned explicitly, include it:
```markdown
| Month    | Usage |
|----------|-------|
| Dec 2022 | 3400  |
| Jan 2023 | 3600  |
...
```

- If the year isn't mentioned, infer correctly from month sequence (previous December followed by January becomes next year):
```markdown
| Month    | Usage |
|----------|-------|
| Dec 2022 | 3400  |
| Jan 2023 | 3600  |
...
```

Ensure each month and usage exactly match the PDF. Do not rearrange or assume values.

### Current Usage
Clearly labeled:
```markdown
**Current Usage**: 5074 kWh
```

### Charges Breakdown
- Delivery Charge
- Supply Charge
- Tax Charge

### Multi-Account/Page Structure
Retain grouping clearly:
```markdown
### Account: <account number>
### Address: <service address>
```
Include corresponding details for each section.

## Output Example
```markdown
# Bill 1

## Statement Date: May 12, 2024  
## Customer DBA: City of North Haven

### Account: 100023910009  
### Address: 150 Elm St, North Haven, CT  
### Commodity: electricity  
### Unit: kWh  
### Service Reference Number: 405212002  
### Meter Number: D007789  
### Rate Class: General Service - 030

#### Usage (13-month summary)
| Month    | Usage |
|----------|-------|
| Dec 2022 | 3400  |
| Jan 2023 | 3600  |
...

#### Current Usage: 3410 kWh

#### Charges
- Delivery: $145.76  
- Supply: $380.10  
- Tax: $12.23  
```

Extract data exactly as presented. Label missing fields clearly as `_Missing_`. Format results as structured Markdown per these guidelines.
"""


gpt_preprocess_prompt4 = """
You are a highly accurate assistant trained to extract structured utility bill data for energy savings and budget reporting.

You are given a utility bill PDF. Your task is to:

✅ Extract **all relevant billing information**  
❌ Discard irrelevant sections like customer service numbers, advertisements, or general tips.

---

# 🗝 Instructions

If the PDF contains **multiple bills** (e.g. more than one statement or account), split them clearly using:

```markdown
# Bill 1
```

…and increment for each new one.

Inside each bill, preserve the document’s structure:  
⚠️ If it contains multiple pages for different accounts, meter numbers, or service reference numbers, keep them grouped and labeled using subheadings.

---

# 🧹 For Each Bill, Extract:

## ## Basic Information
- Statement Date (or Billing Date)
- Customer DBA Name
- Each **Account Number**
- Corresponding **Service Address**: Extract the exact address from usage part
- Service reference number
- Meter Number
- Commodity type (e.g., electricity, natural gas)
- Rate Class: Only extract the rate class without prefix like 'delivery rate, distribution rate, rate, etc.'
- Unit (e.g., kWh, Therms)

---

## Monthly Usage (if available)
Extract the monthly usage exactly as shown in the PDF table or chart. Maintain the original month sequence. The latest month should always match the statement month. Clearly verify month-to-usage accuracy directly from the PDF.

if the OCR text is like this:
| Monthly XWh Use |  |  |  |  |  |
| :--: | :--: | :--: | :--: | :--: | :--: |
| Dec | Jan | Feb | Mar | Apr | May | Jun |
| <usage1> | <usage2> | <usage3> | <usage4> | <usage5> | <usage6> | <usage7> |
| Jul | Aug | Sep | Oct | Nov | Dec |  |
| <usage8> | <usage9> | <usage10> | <usage11> | <usage12> | <usage13> |  |

Transform it to this text

| Month        | Usage |
|--------------|-------|
| Dec 2023     | <usage1>  |
| Jan 2024     | <usage2>  |
| Feb 2024     | <usage3>  |
| Mar 2024     | <usage4>  |
| Apr 2024     | <usage5>  |
| May 2024     | <usage6>  |
| Jun 2024     | <usage7>  |
| Jul 2024     | <usage8>  |
| Aug 2024     | <usage9>  |
| Sep 2024     | <usage10>  |
| Oct 2024     | <usage11>  |
| Nov 2024     | <usage12>  |
| Dec 2024     | <usage13>  |


- If the year is **not** explicitly mentioned, keep the month-usage pairs  as its and add 2022 and 2023 years based on months.
- The top months should be 2022 if there is following january it should become 2023:

```markdown
| Month     | Usage |
|-----------|-------|
| Dec 2022  | 3400  |
| Jan 2023  | 3600  |
| Feb 2023  | 3200  |
...
```

**Important:** Do not change order of motn-usage pairs

---




📌 If usage is aggregated across addresses or accounts, make that clear and group accordingly.

---

## ## Current Usage
Pull the usage value billed in the current period.  
Label it clearly:

```markdown
**Current Usage**: 5074 kWh
```

---

## ## Charges and Rate Breakdown
- Delivery Charge
- Supply Charge
- Tax Charge

---

## ## Per-Account or Per-Page Structure
If the bill includes **multiple account sections** (e.g., each on its own page), retain this grouping. Use:

```markdown
### Account: <account number>
### Address: <service address>
```

…then include the usage, meter number etc., and charges for that segment.

---

# ⛔️ Ignore
- Energy-saving tips
- Marketing content
- Definitions/glossary unless directly connected to bill charges

---

# ✅ Output Format Example

```markdown
# Bill 1

## Statement Date: May 12, 2024  
## Customer DBA: City of North Haven

### Account: 100023910009  
### Address: 150 Elm St, North Haven, CT  
### Commodity: electricity  
### Unit: kWh  
### Service Reference Number: 405212002  
### Meter Number: D007789  
### Rate Class: General Service - 030

#### Usage (13-month summary)
| Month     | Usage |
|-----------|-------|
| Dec 2022  | 3400  |
| Jan 2023  | 3600  |
| Feb 2023  | 3200  |
...

#### Current Usage: 3410 kWh

#### Charges
- Delivery: $145.76  
- Supply: $380.10  
- Tax: $12.23  

---
# Bill 2
...
```

Please extract the data ***exactly same characters*** from related parts of the PDF. If any field is missing, label it as `_Missing_`. Format your output as clean, readable Markdown using the instructions above.
"""


def get_image_validation_prompt(first_md):
    return (
        "Compare the extracted markdown to the content of the provided image. "
        "Identify any lines in the markdown that contain errors—such as incorrect numbers, text, or missing or extra information—when compared to the image.\n"
        "For every inaccurate line, return a JSON array where each object contains two fields: "
        "'original_line' (the exact erroneous line) and 'corrected_line' (the accurate version from the image).\n"
        "Discard irrelevant information such as ads, noise, or customer service details.\n"
        "If a page is blank or contains only faint or unclear marks, do not extract any information. Treat it as empty.\n"
        "If there is a graph explanation keep it as it is."
        "If there is a usage history plot look at line by line and if there is hallucinated month delete it and fix others"
        "Only include lines that need correction. If all lines are accurate, return an empty array ([]).\n"
        "Example output:\n"
        '[\n  {\n    "original_line": "| 89047972 | 38250 | 38208 | 42 | Actual |",\n'
        '    "corrected_line": "| 890479712 | 38250 | 38208 | 42 | Actual |"\n  }\n]'
        "Extracted Markdown:"
        f"{first_md}"
    )


# image_extraction_prompt = """
# You are extracting structured data from a utility bill image.

# Your output must be in well-formatted markdown with clear section headings (e.g., 'Monthly Usage History').

# **Extraction Rules:**
# - For any table (such as usage history), extract **every visible row and column exactly as shown**.
#     - **Do not skip any row**, even if the row appears at the bottom edge of the image, is visually separated, or lacks a visible border.
#     - **Preserve the order** and retain all rows, including months that repeat (e.g., 'Dec' shown twice); do not merge, deduplicate, or reorder.
#     - Extract the table faithfully, including headers and any final row(s) — verify the table is complete.
# - If you encounter any table with split or non-contiguous layout, ensure all parts are included and the sequence is correct.
# - For plots or charts, provide only a one-sentence summary of what the plot depicts; do **not** extract or estimate values from images.
# - Discard irrelevant or generic information, advertisements, or unrelated instructions.

# **Quality Control:**
# Before completing your extraction, double-check that:
# - **No rows at the top or bottom are missed** due to page breaks, image boundaries, or spacing.
# - The entire table, as displayed, is captured and formatted as a markdown table.
# - Section and table content matches the bill image exactly.

# Respond with only the extracted and relevant bill data in markdown. Do not add explanations or commentary."
# """


image_extraction_prompt = """

You are extracting all **informative content** from a utility bill image.

Your output must be in **well-formatted Markdown**, preserving the original content as faithfully as possible, character by character, line by line.

---

## 🔍 Extraction Method

- Extract **everything that looks like billing, usage, date, or charge-related information** exactly as it appears in the image.
- Preserve:
  - All tables, line items, and values
  - Headers, labels, and multi-line sections
  - Duplicate or repeated rows (e.g., "Dec" listed twice)
  - Row and column order, including non-contiguous parts
- Capture full tables even if visually split, including rows at the top or bottom edges.
- In usage history table months may not be in correct order. Do not assume any month just extract exactly character by character and line by line. 

---

## 🚫 DO NOT EXTRACT

- Do **not** extract any of the following:
  - Advertisements or promotional content
  - Generic explanations or service messages
  - Legal disclaimers or boilerplate text
  - Payment instructions or how-to-pay guides
  - Customer service contact blocks
  - Terms of use or privacy policy notices

If these elements are found in the image, **omit them completely**.

---

## 📊 Charts and Visuals

- If the image includes a chart (e.g., bar graph of monthly usage), **do not extract any values**.
- Instead, provide **a one-sentence neutral description** like:
  - “A bar chart showing monthly electricity usage.”
- Do not summarize trends, totals, or variations.

---

## ✅ Output Format

- Use Markdown for headings and tables (e.g., `## Monthly Usage History`, `| Month | Year | kWh |`)
- Ensure all values and rows are captured **exactly as visible**, without guessing or interpreting.
- Do not rephrase, restructure, or label extracted content.
- Do not summarize or explain.

---

## 🧪 Final Quality Check

Before completing:
- Double-check that **all visible content is captured** character by character.
- Ensure **no rows, edges, or split sections are missed**.
- Output is **pure markdown**, without commentary or artificial structuring.

---

## 🛑 If No Data Is Found

If the image contains no extractable content, return this exact message:

"""

image_extraction_prompt_bar = (
    "You are extracting data from a utility bill image. "
    "Extract all informative parts exactly as shown, character by character, in markdown format. "
    "Do not omit or alter any informative detail. "
    "Keep only informative sections of the bill. "
    "For plots: Only mention plots that show last years historical usage by month during the last year. "
    "For such plots, if plot has usage value on top of each bar extract the monthly usage data "
    "If usage values are shown **only** on the y-axis (not labeled on the bars), do not extract any values from the plot."
)