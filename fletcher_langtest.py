import logging

logging.basicConfig(level=logging.DEBUG)

import os
import json
import requests
from langsmith import traceable
# , add_tags, set_custom_metadata

@traceable(name="Landing AI PDF Schema Extraction")
def extract_schema_from_pdf(pdf_path: str, schema_path: str) -> dict:
    # Load Landing AI key from env
    landing_ai_api_key = os.environ["LANDING_AI_API_KEY"]

    headers = {"Authorization": f"Basic {landing_ai_api_key}"}
    url = "https://api.va.landing.ai/v1/tools/agentic-document-analysis"

    pdf_name = os.path.basename(pdf_path)
    schema_name = os.path.basename(schema_path)
    
    print(pdf_name)
    print(schema_name)

    # Add tags and metadata for trace
    # add_tags(["landing-ai", "pdf", "schema-extraction"])
    # set_custom_metadata({
    #     "pdf_name": pdf_name,
    #     "schema_name": schema_name,
    #     "pdf_size_bytes": os.path.getsize(pdf_path)
    # })

    # Load schema JSON
    with open(schema_path, "r") as f:
        schema = json.load(f)

    # Prepare files and payload
    files = [
        ("pdf", (pdf_name, open(pdf_path, "rb"), "application/pdf")),
    ]
    payload = {"fields_schema": json.dumps(schema)}

    # Make the request
    response = requests.post(url, headers=headers, files=files, data=payload)
    response.raise_for_status()

    # Extract and return result
    print(response.json()["data"])
    output_data = response.json()["data"]
    return output_data["extracted_schema"]

# === Usage ===
if __name__ == "__main__":
    pdf_path = "../landing-ai-sandbox-data/input/test_pdfs/document_0.pdf"
    schema_path = "../schema/main_usage_schema.json"

    extracted_info = extract_schema_from_pdf(pdf_path, schema_path)
    print(json.dumps(extracted_info, indent=2))