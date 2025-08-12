# In pipeline.py

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

def run_end_to_end_pipeline(list_of_pdf_paths, status_callback):
    """
    Runs the entire 1-5 pipeline on a given list of PDF file paths.
    Uses a callback function to report status back to the Streamlit UI.
    """
    final_json_objects = []

    # --- 1. Rotation Fix ---
    status_callback("Step 1/5: Fixing PDF rotations...")
    corrected_pdf_paths = []
    os.makedirs(CORRECTED_PDF_DIR, exist_ok=True)
    for pdf_path in list_of_pdf_paths:
        filename = os.path.basename(pdf_path)
        corrected_path = os.path.join(CORRECTED_PDF_DIR, filename)
        try:
            ocrmypdf.ocr(pdf_path, corrected_path, deskew=True, rotate_pages=True, clean=True, force_ocr=True)
            corrected_pdf_paths.append(corrected_path)
        except Exception as e:
            print(f"Rotation fix failed for {filename}: {e}. Copying original.")
            shutil.copy(pdf_path, corrected_path) # Fallback
            corrected_pdf_paths.append(corrected_path)
    
    # --- 2. PDF -> Generic JSON ---
    status_callback("Step 2/5: Converting PDFs to Generic JSON (AgenticDoc)...")
    os.makedirs(GENERIC_JSON_DIR, exist_ok=True)
    results = parse(corrected_pdf_paths, include_marginalia=False, include_metadata_in_markdown=False)
    for source_path, parsed_doc in zip(corrected_pdf_paths, results):
        base_name = os.path.splitext(os.path.basename(source_path))[0]
        output_json_path = os.path.join(GENERIC_JSON_DIR, f"{base_name}.json")
        chunks_data = [chunk.dict() for chunk in parsed_doc.chunks]
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(chunks_data, f, indent=2)

    # --- 3. Generic JSON -> Final JSON ---
    status_callback("Step 3/5: Converting Generic JSON to Final JSON (OpenAI)...")
    os.makedirs(FINAL_JSON_DIR, exist_ok=True)
    with open("master_prompt.txt", "r") as f:
        master_prompt_template = f.read()
    client = OpenAI()
    for filename in os.listdir(GENERIC_JSON_DIR):
        if filename.endswith('.json'):
            with open(os.path.join(GENERIC_JSON_DIR, filename), 'r') as f:
                content = f.read()
            doc_id = filename.replace('.json', '')
            prompt = master_prompt_template.replace("{{generic_json_content}}", content)
            prompt = prompt.replace("{{document_id_placeholder}}", doc_id)
            response = client.chat.completions.create(
                model="gpt-4o", messages=[{"role": "user", "content": prompt}],
                temperature=0.0, response_format={"type": "json_object"}
            )
            final_json_str = response.choices[0].message.content
            final_json_obj = json.loads(final_json_str)
            final_json_objects.append(final_json_obj) # Store for later display
            with open(os.path.join(FINAL_JSON_DIR, filename), 'w') as f:
                json.dump(final_json_obj, f, indent=2)

    # --- 4. QC Flagging ---
    status_callback("Step 4/5: Running QC checks and flagging files...")
    os.makedirs(REVIEW_DIR, exist_ok=True)
    for final_json in final_json_objects:
        if final_json.get('_qc_flag') is True:
            doc_id = final_json.get('documentId')
            original_pdf_path = os.path.join(SOURCE_PDF_DIR, f"{doc_id}.pdf")
            destination_path = os.path.join(REVIEW_DIR, f"{doc_id}.pdf")
            if os.path.exists(original_pdf_path):
                shutil.move(original_pdf_path, destination_path)

    # --- 5. Build Knowledge Base ---
    status_callback("Step 5/5: Updating RAG knowledge base...")
    if not final_json_objects:
        return [] # Nothing to add
        
    db_client = chromadb.PersistentClient(path=DB_DIR)
    embedding_function = OpenAIEmbeddingFunction(api_key=os.getenv("OPENAI_API_KEY"), model_name="text-embedding-3-small")
    collection = db_client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=embedding_function)
    
    # Create LangChain documents to be ingested
    docs_to_ingest = []
    for final_json in final_json_objects:
        doc = Document(
            page_content=json.dumps(final_json, indent=2),
            metadata={"source": f"{final_json.get('documentId')}.json"}
        )
        docs_to_ingest.append(doc)

    # Ingest into ChromaDB
    if docs_to_ingest:
        langchain_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        page_contents = [doc.page_content for doc in docs_to_ingest]
        embeddings = langchain_embeddings.embed_documents(page_contents)
        
        # Create unique IDs
        current_count = collection.count()
        ids = [f"doc_{current_count + i}" for i in range(len(docs_to_ingest))]

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=[doc.page_content for doc in docs_to_ingest],
            metadatas=[doc.metadata for doc in docs_to_ingest]
        )
    
    return final_json_objects