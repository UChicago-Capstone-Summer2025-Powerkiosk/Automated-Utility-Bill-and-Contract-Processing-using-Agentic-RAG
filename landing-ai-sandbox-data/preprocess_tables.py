# In preprocess_tables.py

import os
import re
import csv
from pathlib import Path

# --- Configuration ---
# We'll use relative paths to make it easy to run
BASE_SOURCE_FOLDER = "input_data/"
BASE_DESTINATION_FOLDER = "processed_data/"

# --- Utility Functions (from your notebook) ---

def get_files_one_by_one(directory: str):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".md"):
                yield os.path.join(root, file)

def get_file_paths(directory: str) -> list:
    return list(get_files_one_by_one(directory))

def get_file_name_and_parent_folder(file_path: str) -> (str, str):
    file_name = os.path.basename(file_path)
    parent_folder = os.path.basename(os.path.dirname(file_path))
    return parent_folder, file_name

def is_alignment_line(line: str) -> bool:
    return bool(re.match(r'^\s*\|?(\s*:?-+:?\s*\|)+\s*$', line))

def extract_markdown_tables(md_path: str) -> list:
    tables = []
    inside_table = False
    current_table = []
    start_index = None

    with open(md_path, 'r', encoding='utf-8') as md_file:
        lines = md_file.readlines()

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped: # Skip blank lines when checking for table end
            if inside_table:
                # End of table if a blank line is found
                if current_table:
                    tables.append({
                        "start": start_index,
                        "end": current_table[-1][0],
                        "lines": current_table
                    })
                inside_table = False
                current_table = []
                start_index = None
            continue

        if is_alignment_line(stripped) and not inside_table:
            # Start of a new table
            inside_table = True
            current_table = []
            
            # Look for a header line immediately above
            if i > 0 and lines[i-1].strip().startswith('|'):
                current_table.append((i-1, lines[i-1]))
                start_index = i-1
            else:
                start_index = i
            
            current_table.append((i, line))
        
        elif inside_table and stripped.startswith('|'):
            current_table.append((i, line))
        
        elif inside_table: # No longer a table line
            if current_table:
                tables.append({
                    "start": start_index,
                    "end": current_table[-1][0],
                    "lines": current_table
                })
            inside_table = False
            current_table = []
            start_index = None

    if inside_table and current_table: # Catch table at end of file
        tables.append({
            "start": start_index,
            "end": current_table[-1][0],
            "lines": current_table
        })

    return tables

def table_to_rows(table_text: str) -> list:
    table_lines = table_text.strip().splitlines()
    if len(table_lines) <= 1: # Header and alignment line minimum
        return []

    rows = []
    for table_line in table_lines:
        if is_alignment_line(table_line):
            continue
        cleaned_row = [cell.strip() for cell in table_line.strip().strip('|').split('|')]
        if any(cleaned_row): # Add row if it's not completely empty
            rows.append(cleaned_row)
    
    # Condition from your email: only extract tables with > 15 rows
    # Note: This includes the header, so 1 header + 15 data rows = 16. Adjust if needed.
    min_rows = 15
    if len(rows) > min_rows:
        return rows
    else:
        return [] # Don't extract smaller tables

def write_rows_to_csv(rows: list, destination: str):
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerows(rows)
    print(f"    ✅ Large table extracted to {destination}")

def read_md(md_path: str) -> str:
    with open(md_path, 'r', encoding='utf-8') as file:
        return file.read()

def save_new_md(md_content: str, destination: str):
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    Path(destination).write_text(md_content, encoding='utf-8')
    print(f"    ✅ New markdown saved to {destination}")

def replace_tables_with_placeholders(md_path: str, list_of_tables: list) -> str:
    md_lines = read_md(md_path).splitlines()
    parent_folder, _ = get_file_name_and_parent_folder(md_path)
    
    # Replace from bottom up to preserve line indices
    for i, table in reversed(list(enumerate(list_of_tables))):
        start = table["start"]
        end = table["end"]
        
        table_content = "".join([line_content for _, line_content in table['lines']])
        
        rows = table_to_rows(table_content)
        
        # Only process if it's a valid, large table
        if rows:
            csv_filename = f"table-{i}.csv"
            destination_csv_path = Path(BASE_DESTINATION_FOLDER) / parent_folder / csv_filename
            write_rows_to_csv(rows, destination_csv_path)
            
            tag = f"{{{{table_data: {csv_filename}}}}}"
            md_lines[start:end+1] = [tag]

    return "\n".join(md_lines)

# --- Main Execution Logic ---
if __name__ == "__main__":
    print("--- Starting Pre-processing Step ---")
    list_of_md_files = get_file_paths(BASE_SOURCE_FOLDER)
    
    if not list_of_md_files:
        print("No markdown files found in the 'input_data' directory. Please copy some sample documents there.")
    else:
        print(f"Found {len(list_of_md_files)} markdown files to process.")

    for md_path in list_of_md_files:
        print(f"\nProcessing: {md_path}")
        parent_folder, file_name = get_file_name_and_parent_folder(md_path)
        
        # Extract tables
        tables = extract_markdown_tables(md_path)
        
        # Replace large tables with placeholders and save CSVs
        if tables:
            new_md_content = replace_tables_with_placeholders(md_path, tables)
            
            # Define where the new .md file will be saved
            destination_md_path = Path(BASE_DESTINATION_FOLDER) / parent_folder / file_name
            save_new_md(new_md_content, destination_md_path)
        else:
            # If no tables, just copy the file over as-is
            destination_md_path = Path(BASE_DESTINATION_FOLDER) / parent_folder / file_name
            os.makedirs(os.path.dirname(destination_md_path), exist_ok=True)
            Path(destination_md_path).write_text(read_md(md_path), encoding='utf-8')
            print(f"    No large tables found. Copied file to {destination_md_path}")

    print("\n--- Pre-processing Complete ---")