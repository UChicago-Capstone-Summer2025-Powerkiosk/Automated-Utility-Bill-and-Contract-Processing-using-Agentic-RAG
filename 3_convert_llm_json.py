import os
import json
import openai

# Configuration
GENERIC_JSON_DIR = "generic_json_outputs/"
FINAL_JSON_DIR = "final_pdf_json_outputs/"

if __name__ == "__main__":
    print("--- Starting Generic-JSON to Final-JSON Conversion ---")

    if 'OPENAI_API_KEY' not in os.environ:
        print("\n--- ERROR: OPENAI_API_KEY environment variable not set. ---")
        exit()

    os.makedirs(FINAL_JSON_DIR, exist_ok=True)

    try:
        with open("master_prompt.txt", "r", encoding='utf-8') as f:
            master_prompt_template = f.read()
    except FileNotFoundError:
        print("master_prompt.txt not found. Please create it first.")
        exit()

    client = openai.OpenAI()
    
    json_files = [f for f in os.listdir(GENERIC_JSON_DIR) if f.endswith('.json')]

    if not json_files:
        print(f"No generic JSON files found in '{GENERIC_JSON_DIR}'.")
        print("Please run 'run_pdf_to_generic_json.py' first.")
    else:
        for filename in json_files:
            print(f"\nProcessing generic JSON: {filename}")
            
            with open(os.path.join(GENERIC_JSON_DIR, filename), 'r') as f:
                generic_json_content = f.read()

            doc_id = filename.replace('.json', '')
            
            prompt = master_prompt_template.replace("{{generic_json_content}}", generic_json_content)
            prompt = prompt.replace("{{document_id_placeholder}}", doc_id)

            try:
                print("  - Sending to LLM for final conversion...")
                response = client.chat.completions.create(
                    model="gpt-4o", 
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )
                final_json_str = response.choices[0].message.content
                
                # Validate and save the final JSON
                parsed_json = json.loads(final_json_str)
                output_path = os.path.join(FINAL_JSON_DIR, filename)
                with open(output_path, 'w') as f:
                    json.dump(parsed_json, f, indent=2)
                print(f"  ✅ Successfully created final JSON: {output_path}")

            except Exception as e:
                print(f"  --- ❌ An error occurred for {filename} ---")
                print(f"  Error: {e}")

    print("\n--- Final JSON Conversion Complete ---")