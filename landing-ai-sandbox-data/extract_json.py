# In extract_json.py

import os
import json
import openai

# --- Configuration ---
PROCESSED_DATA_DIR = "processed_data/"
FINAL_JSON_DIR = "final_json_output/"

# Ensure the final output directory exists
os.makedirs(FINAL_JSON_DIR, exist_ok=True)

# Load the API key from environment variables
api_key = "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"
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set. Please set it before running.")

client = openai.OpenAI(api_key=api_key)

# Load the master prompt from the text file
try:
    with open("master_prompt.txt", "r", encoding='utf-8') as f:
        master_prompt_template = f.read()
except FileNotFoundError:
    raise FileNotFoundError("master_prompt.txt not found. Please create it in the same directory.")

def process_document_folder(doc_folder_path):
    """Processes a single document folder from the processed_data directory."""
    
    folder_name = os.path.basename(doc_folder_path)
    print(f"\nProcessing folder: {folder_name}")

    md_file_path = None
    csv_files = {}

    # 1. Find the markdown and csv files
    for filename in os.listdir(doc_folder_path):
        full_path = os.path.join(doc_folder_path, filename)
        if filename.endswith(".md"):
            md_file_path = full_path
        elif filename.endswith(".csv"):
            with open(full_path, 'r', encoding='utf-8') as f:
                csv_files[filename] = f.read()

    if not md_file_path:
        print(f"  - Skipping {folder_name}, no .md file found.")
        return

    with open(md_file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # 2. Construct the full prompt for the LLM
    prompt = master_prompt_template.replace("{{md_filename}}", os.path.basename(md_file_path))
    prompt = prompt.replace("{{markdown_content}}", md_content)
    
    csv_data_string = ""
    if csv_files:
        for name, content in csv_files.items():
            csv_data_string += f"--- START OF FILE {name} ---\n{content}\n--- END OF FILE {name} ---\n\n"
    else:
        csv_data_string = "No CSV files were extracted for this document."

    prompt = prompt.replace("{{csv_data_string}}", csv_data_string)
    
    # 3. Call the LLM API
    try:
        print(f"  - Sending {folder_name} to LLM...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        json_output_str = response.choices[0].message.content

        # 4. Validate and Save
        parsed_json = json.loads(json_output_str) # Ensures the LLM returned valid JSON
        output_filename = os.path.join(FINAL_JSON_DIR, folder_name + ".json")
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(parsed_json, f, indent=2)
        print(f"  - ✅ Successfully created {output_filename}")

    except Exception as e:
        print(f"  - ❌ ERROR processing {folder_name}: {e}")
        error_file = os.path.join(FINAL_JSON_DIR, folder_name + ".error.txt")
        with open(error_file, "w", encoding='utf-8') as f:
            f.write(f"Error: {e}\n\n--- PROMPT SENT ---\n{prompt}")
        print(f"  - Wrote error details to {error_file}")

# --- Main Execution Logic ---
if __name__ == "__main__":
    print("--- Starting LLM JSON Extraction ---")
    
    doc_folders = [os.path.join(PROCESSED_DATA_DIR, d) for d in os.listdir(PROCESSED_DATA_DIR) if os.path.isdir(os.path.join(PROCESSED_DATA_DIR, d))]
    
    if not doc_folders:
        print("No processed document folders found in 'processed_data'. Did you run 'preprocess_tables.py' first?")
    else:
        for folder_path in doc_folders:
            process_document_folder(folder_path)
        
    print("\n--- LLM Extraction Complete ---")