# In retry_failures.py

import os
import json
import time
import openai

# --- Configuration ---
# Point to the same directories as your main script
PROCESSED_DATA_DIR = "processed_data/"
FINAL_JSON_DIR = "final_json_output/"

# Load the API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set. Please set it before running.")

client = openai.OpenAI(api_key=api_key)

# Load the master prompt from the text file
try:
    with open("master_prompt.txt", "r", encoding='utf-8') as f:
        master_prompt_template = f.read()
except FileNotFoundError:
    raise FileNotFoundError("master_prompt.txt not found. Please create it in the same directory.")

def process_single_failed_document(doc_folder_path):
    """
    This is the exact same processing function from extract_json.py.
    It takes a single document folder path and tries to process it.
    """
    folder_name = os.path.basename(doc_folder_path)
    print(f"\nRetrying failed document: {folder_name}")

    md_file_path = None
    csv_files = {}

    for filename in os.listdir(doc_folder_path):
        full_path = os.path.join(doc_folder_path, filename)
        if filename.endswith(".md"):
            md_file_path = full_path
        elif filename.endswith(".csv"):
            with open(full_path, 'r', encoding='utf-8') as f:
                csv_files[filename] = f.read()

    if not md_file_path:
        print(f"  - Skipping {folder_name}, no .md file found.")
        return False # Indicate failure

    with open(md_file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    prompt = master_prompt_template.replace("{{md_filename}}", os.path.basename(md_file_path))
    prompt = prompt.replace("{{markdown_content}}", md_content)
    
    csv_data_string = ""
    if csv_files:
        for name, content in csv_files.items():
            csv_data_string += f"--- START OF FILE {name} ---\n{content}\n--- END OF FILE {name} ---\n\n"
    else:
        csv_data_string = "No CSV files were extracted for this document."

    prompt = prompt.replace("{{csv_data_string}}", csv_data_string)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"  - Sending {folder_name} to LLM (Attempt {attempt + 1}/{max_retries})...")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            json_output_str = response.choices[0].message.content
            parsed_json = json.loads(json_output_str)
            output_filename = os.path.join(FINAL_JSON_DIR, folder_name + ".json")
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(parsed_json, f, indent=2)
            print(f"  - ✅ Successfully created {output_filename}")
            return True # Indicate success

        except openai.RateLimitError as e:
            wait_time = (attempt + 1) * 10 # Wait longer: 10s, 20s, 30s
            print(f"  - ⏳ Rate limit hit. Waiting for {wait_time} seconds...")
            time.sleep(wait_time)
        except Exception as e:
            print(f"  - ❌ An unexpected error occurred: {e}")
            break
            
    print(f"  - ❌ FAILED to process {folder_name} again.")
    return False # Indicate failure

# --- Main Execution Logic for Retrying Failures ---
if __name__ == "__main__":
    print("--- Starting Retry Script for Failed Documents ---")

    failed_doc_names = []
    # 1. Find all .error.txt files to identify which documents failed.
    for filename in os.listdir(FINAL_JSON_DIR):
        if filename.endswith(".error.txt"):
            # Extract the base name, e.g., "document_591" from "document_591.error.txt"
            base_name = filename.replace(".error.txt", "")
            failed_doc_names.append(base_name)

    if not failed_doc_names:
        print("No failed documents found (.error.txt files). All clear!")
    else:
        print(f"Found {len(failed_doc_names)} failed documents to retry: {failed_doc_names}")

        for doc_name in failed_doc_names:
            doc_folder_path = os.path.join(PROCESSED_DATA_DIR, doc_name)
            
            if not os.path.isdir(doc_folder_path):
                print(f"  - Warning: Could not find processed folder for {doc_name}. Skipping.")
                continue

            # 2. Attempt to process the failed document.
            success = process_single_failed_document(doc_folder_path)

            # 3. If successful, clean up the old error file.
            if success:
                error_file_path = os.path.join(FINAL_JSON_DIR, doc_name + ".error.txt")
                if os.path.exists(error_file_path):
                    os.remove(error_file_path)
                    print(f"  - ✅ Cleaned up {error_file_path}")
            
            # Add a longer, more polite delay between each retry attempt.
            time.sleep(5) 

    print("\n--- Retry Script Finished ---")