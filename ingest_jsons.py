# In rag_system/ingest_jsons.py (Corrected Version)

import os
import json
import chromadb
from langchain_community.document_loaders import JSONLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
# ADD THIS NEW IMPORT
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

# --- Configuration ---
JSON_SOURCE_DIR = "../final_json_output/"
DB_DIR = "./vector_db"
COLLECTION_NAME = "utility_docs"

def load_and_split_documents(source_dir):
    """Loads all JSON files and splits them into manageable chunks."""
    all_docs = []
    print(f"Loading JSON files from: {source_dir}")

    json_files = [f for f in os.listdir(source_dir) if f.endswith('.json')]
    if not json_files:
        print("No JSON files found in the source directory.")
        return []

    for filename in json_files:
        file_path = os.path.join(source_dir, filename)
        jq_schema = '.. | select(type == "string" or type == "number")'
        loader = JSONLoader(file_path=file_path, jq_schema=jq_schema, text_content=False)
        data = loader.load()
        for doc in data:
            doc.metadata['source'] = filename
        all_docs.extend(data)

    print(f"Loaded {len(json_files)} files, created {len(all_docs)} initial document objects.")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    split_docs = text_splitter.split_documents(all_docs)
    print(f"Split documents into {len(split_docs)} chunks.")
    return split_docs

def create_and_populate_db(documents):
    """Initializes the vector DB and populates it with the document chunks."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")

    print("Initializing ChromaDB-native OpenAI Embedding Function...")
    # Use the ChromaDB utility for compatibility
    embedding_function = OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name="text-embedding-3-small"
    )
    
    print(f"Initializing ChromaDB in directory: {DB_DIR}")
    client = chromadb.PersistentClient(path=DB_DIR)

    print(f"Getting or creating collection: {COLLECTION_NAME}")
    vector_store = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function
    )
    
    print("Manually embedding document chunks for ChromaDB...")
    langchain_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    # Check if there are documents to embed
    if not documents:
        print("No documents to embed. Exiting.")
        return

    page_contents = [doc.page_content for doc in documents]
    embedded_docs = langchain_embeddings.embed_documents(page_contents)

    print(f"Populating database. This may take a few minutes for {len(documents)} chunks...")
    
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i:i + batch_size]
        batch_embeddings = embedded_docs[i:i + batch_size]
        
        vector_store.add(
            ids=[f"doc_{i+j}" for j in range(len(batch_docs))],
            embeddings=batch_embeddings,
            documents=[doc.page_content for doc in batch_docs],
            metadatas=[doc.metadata for doc in batch_docs]
        )
        print(f"  - Added batch {i//batch_size + 1}/{(len(documents)//batch_size) + 1}")

    print("\n--- Database creation and population complete! ---")
    print(f"Total chunks in DB: {vector_store.count()}")

if __name__ == "__main__":
    docs_to_ingest = load_and_split_documents(JSON_SOURCE_DIR)
    if docs_to_ingest:
        create_and_populate_db(docs_to_ingest)
    else:
        print("No documents found to ingest. Please check the JSON_SOURCE_DIR path.")