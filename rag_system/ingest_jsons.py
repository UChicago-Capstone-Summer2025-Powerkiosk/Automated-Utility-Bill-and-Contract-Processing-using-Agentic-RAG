import os
import json
import chromadb
from langchain_community.document_loaders import JSONLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

# --- Configuration ---
JSON_SOURCE_DIR = "../final_json_output/" # Point to the folder with your 1143 JSONs
DB_DIR = "./vector_db" # Where the local vector database will be stored
COLLECTION_NAME = "utility_docs" # Name for our data collection in the DB

def load_and_split_documents(source_dir):
    """Loads all JSON files and splits them into manageable chunks."""
    all_docs = []
    print(f"Loading JSON files from: {source_dir}")

    for filename in os.listdir(source_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(source_dir, filename)
            
            # The JSONLoader needs a specific jq schema to know what to index.
            # We'll tell it to extract text from all key fields.
            jq_schema = '.. | select(type == "string" or type == "number")'

            loader = JSONLoader(
                file_path=file_path,
                jq_schema=jq_schema,
                text_content=False # We want to index the raw values
            )
            data = loader.load()
            
            # Add the source filename to the metadata of each document chunk
            for doc in data:
                doc.metadata['source'] = filename
            all_docs.extend(data)

    print(f"Loaded {len(os.listdir(source_dir))} files, created {len(all_docs)} initial document objects.")

    # Now, split the documents into smaller chunks for better search results
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    split_docs = text_splitter.split_documents(all_docs)
    
    print(f"Split documents into {len(split_docs)} chunks.")
    return split_docs

def create_and_populate_db(documents):
    """Initializes the vector DB and populates it with the document chunks."""
    print("Initializing embedding model (OpenAI)...")
    embedding_function = OpenAIEmbeddings(model="text-embedding-3-small")
    
    print(f"Initializing ChromaDB in directory: {DB_DIR}")
    # The 'persistent' client saves the DB to disk
    client = chromadb.PersistentClient(path=DB_DIR)

    # Create or load the collection (like a table in a traditional DB)
    vector_store = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function # This is how ChromaDB will create embeddings
    )

    print(f"Populating database. This may take a few minutes for {len(documents)} chunks...")
    
    # Add documents to the database in batches to be efficient
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i:i + batch_size]
        
        vector_store.add(
            ids=[f"doc_{i+j}" for j in range(len(batch_docs))], # Unique ID for each chunk
            documents=[doc.page_content for doc in batch_docs],
            metadatas=[doc.metadata for doc in batch_docs]
        )
        print(f"  - Added batch {i//batch_size + 1}/{(len(documents)//batch_size) + 1}")

    print("\n--- Database creation and population complete! ---")
    print(f"Total chunks in DB: {vector_store.count()}")

# --- Main Execution ---
if __name__ == "__main__":
    # 1. Load and split the documents
    docs_to_ingest = load_and_split_documents(JSON_SOURCE_DIR)
    
    # 2. Create the vector database and populate it
    if docs_to_ingest:
        create_and_populate_db(docs_to_ingest)
    else:
        print("No documents found to ingest. Please check the JSON_SOURCE_DIR path.")