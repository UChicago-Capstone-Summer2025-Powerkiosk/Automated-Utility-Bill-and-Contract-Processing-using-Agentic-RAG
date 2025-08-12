import os
import json
import chromadb
from langchain_community.document_loaders import JSONLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

# --- Configuration ---
JSON_SOURCE_DIR = "final_json_outputs/"
DB_DIR = "vector_db"
COLLECTION_NAME = "utility_docs"

def load_and_split_documents(source_dir):
    """
    Loads each JSON file as a SINGLE document, preserving its full content.
    This maintains the context between keys and values.
    """
    from langchain_core.documents import Document

    all_docs = []
    print(f"Loading JSON files from: {source_dir}")

    json_files = [f for f in os.listdir(source_dir) if f.endswith('.json')]
    if not json_files:
        print("No JSON files found in the source directory.")
        return []

    for filename in json_files:
        file_path = os.path.join(source_dir, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                # Load the entire JSON object
                data = json.load(f)
                content_string = json.dumps(data, indent=2)

                # Create a single LangChain Document object for the entire file
                doc = Document(
                    page_content=content_string,
                    metadata={"source": filename}
                )
                all_docs.append(doc)

            except json.JSONDecodeError:
                print(f"  - Warning: Could not decode JSON from {filename}. Skipping.")

    print(f"Loaded and created {len(all_docs)} document objects (one per file).")
    return all_docs

def create_and_populate_db(documents):
    """Initializes the vector DB and populates it with the document chunks in batches."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")

    print("Initializing ChromaDB-native OpenAI Embedding Function...")
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
    
    # Initialize the LangChain embeddings object to use for batch processing
    langchain_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    if not documents:
        print("No documents to embed. Exiting.")
        return

    print(f"Populating database in batches. Total documents: {len(documents)}")
    
    # Define a batch size. A size of 100-200 is usually safe and efficient.
    batch_size = 100 
    for i in range(0, len(documents), batch_size):
        # 1. Get a small batch of documents
        batch_docs = documents[i:i + batch_size]
        print(f"  - Processing batch {i//batch_size + 1}/{(len(documents)//batch_size) + 1}...")

        # 2. Get the text content for the current batch
        page_contents = [doc.page_content for doc in batch_docs]
        
        # 3. Embed ONLY this small batch
        print("    - Embedding batch...")
        batch_embeddings = langchain_embeddings.embed_documents(page_contents)

        # 4. Add the batch to the vector store
        print("    - Adding to ChromaDB...")
        vector_store.add(
            ids=[f"doc_{i+j}" for j in range(len(batch_docs))],
            embeddings=batch_embeddings,
            documents=[doc.page_content for doc in batch_docs],
            metadatas=[doc.metadata for doc in batch_docs]
        )

    print("\n--- Database creation and population complete! ---")
    print(f"Total documents in DB: {vector_store.count()}")

if __name__ == "__main__":
    docs_to_ingest = load_and_split_documents(JSON_SOURCE_DIR)
    if docs_to_ingest:
        create_and_populate_db(docs_to_ingest)
    else:
        print("No documents found to ingest. Please check the JSON_SOURCE_DIR path.")