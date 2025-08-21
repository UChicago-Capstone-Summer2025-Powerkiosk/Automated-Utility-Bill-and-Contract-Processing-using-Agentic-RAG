# In pipeline.py (The Correct, Refactored Version)

import os
import json
import shutil
import ocrmypdf
from agentic_doc.parse import parse
from openai import OpenAI
import chromadb
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

# --- Configuration ---
SOURCE_PDF_DIR = "source_pdfs/"
CORRECTED_PDF_DIR = "corrected_pdfs/"
GENERIC_JSON_DIR = "generic_json_outputs/"
FINAL_JSON_DIR = "final_json_outputs/"
REVIEW_DIR = "manual_review_needed/"
DB_DIR = "vector_db/"
COLLECTION_NAME = "utility_docs"

# --- FUNCTION 1: PROCESSES A SINGLE FILE ---
def process_single_pdf(pdf_path, status_callback):
    """
    Runs stages 1-4 of the pipeline for a SINGLE PDF file.
    Returns the final JSON object for that file.
    """
    filename = os.path.basename(pdf_path)
    base_name = os.path.splitext(filename)[0]

    # Stage 1: Rotation Fix
    status_callback(f"Fixing rotation for {filename}...")
    corrected_path = os.path.join(CORRECTED_PDF_DIR, filename)
    os.makedirs(CORRECTED_PDF_DIR, exist_ok=True)
    try:
        ocrmypdf.ocr(pdf_path, corrected_path, deskew=True, rotate_pages=True, clean=True, force_ocr=True)
    except Exception as e:
        print(f"Rotation fix failed for {filename}: {e}. Copying original.")
        shutil.copy(pdf_path, corrected_path)

    # Stage 2: PDF -> Generic JSON
    status_callback(f"Running AgenticDoc for {filename}...")
    os.makedirs(GENERIC_JSON_DIR, exist_ok=True)
    results = parse([corrected_path], include_marginalia=False, include_metadata_in_markdown=False)
    output_generic_json_path = os.path.join(GENERIC_JSON_DIR, f"{base_name}.json")
    chunks_data = [chunk.dict() for chunk in results[0].chunks]
    with open(output_generic_json_path, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, indent=2)

    # Stage 3: Generic JSON -> Final JSON
    status_callback(f"Structuring data with OpenAI for {filename}...")
    os.makedirs(FINAL_JSON_DIR, exist_ok=True)
    with open("master_prompt_final.txt", "r") as f:
        master_prompt_template = f.read()
    client = OpenAI()
    with open(output_generic_json_path, 'r') as f:
        content = f.read()
    prompt = master_prompt_template.replace("{{generic_json_content}}", content)
    prompt = prompt.replace("{{document_id_placeholder}}", base_name)
    response = client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": prompt}],
        temperature=0.0, response_format={"type": "json_object"}
    )
    final_json_obj = json.loads(response.choices[0].message.content)
    with open(os.path.join(FINAL_JSON_DIR, f"{base_name}.json"), 'w') as f:
        json.dump(final_json_obj, f, indent=2)

    # Stage 4: QC Flagging
    status_callback(f"Running QC check for {filename}...")
    os.makedirs(REVIEW_DIR, exist_ok=True)
    if final_json_obj.get('_qc_flag') is True:
        # We need the original source path for the move operation
        original_uncorrected_path = os.path.join(SOURCE_PDF_DIR, filename)
        destination_path = os.path.join(REVIEW_DIR, filename)
        if os.path.exists(original_uncorrected_path):
            shutil.move(original_uncorrected_path, destination_path)
            
    return final_json_obj

# --- FUNCTION 2: UPDATES THE KNOWLEDGE BASE ---
def update_knowledge_base(list_of_final_json):
    """
    Takes a list of final JSON objects and ingests them into the RAG knowledge base.
    """
    if not list_of_final_json:
        print("No new documents to add to the knowledge base.")
        return
        
    db_client = chromadb.PersistentClient(path=DB_DIR)
    embedding_function = OpenAIEmbeddingFunction(api_key=os.getenv("OPENAI_API_KEY"), model_name="text-embedding-3-small")
    collection = db_client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=embedding_function)
    
    docs_to_ingest = []
    for final_json in list_of_final_json:
        doc = Document(
            page_content=json.dumps(final_json, indent=2),
            metadata={"source": f"{final_json.get('documentId')}.json"}
        )
        docs_to_ingest.append(doc)

    if docs_to_ingest:
        langchain_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        page_contents = [doc.page_content for doc in docs_to_ingest]
        embeddings = langchain_embeddings.embed_documents(page_contents)
        
        current_count = collection.count()
        ids = [f"doc_{current_count + i}" for i in range(len(docs_to_ingest))]

        collection.add(ids=ids, embeddings=embeddings, documents=[doc.page_content for doc in docs_to_ingest], metadatas=[doc.metadata for doc in docs_to_ingest])
    
    print(f"Successfully added {len(docs_to_ingest)} new document(s) to the knowledge base.")