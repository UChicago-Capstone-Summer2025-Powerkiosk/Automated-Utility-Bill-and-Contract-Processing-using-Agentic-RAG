import os
import re
import chromadb
import argparse
import openai
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

# --- Configuration ---
DB_DIR = "./vector_db"
COLLECTION_NAME = "utility_docs"

def extract_document_id(query_text):
    """
    Uses regex to find patterns like 'document_123' or 'document 123' in a query.
    Returns the formatted document ID (e.g., 'document_123.json') if found.
    """
    # This regex looks for "document" followed by an optional space or underscore, and then digits.
    match = re.search(r'document[_\s]?(\d+)', query_text, re.IGNORECASE)
    if match:
        doc_number = match.group(1)
        # Return the canonical filename we expect in the metadata
        return f"document_{doc_number}.json"
    return None

def retrieve_relevant_documents(query_text, n_results=15):
    """
    Stage 1: Retrieve relevant documents.
    If a specific document ID is mentioned in the query, it uses metadata filtering.
    Otherwise, it performs a broad semantic search.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")

    embedding_function = OpenAIEmbeddingFunction(api_key=api_key, model_name="text-embedding-3-small")

    print(f"Connecting to ChromaDB at: {DB_DIR}")
    client = chromadb.PersistentClient(path=DB_DIR)
    
    try:
        collection = client.get_collection(name=COLLECTION_NAME, embedding_function=embedding_function)
    except ValueError:
        print(f"Error: Collection '{COLLECTION_NAME}' not found. Run ingest_jsons.py first.")
        return None

    # THE NEW LOGIC STARTS HERE
    filter_dict = None
    document_id = extract_document_id(query_text)

    if document_id:
        print(f"\n1. Detected request for a specific document: '{document_id}'. Applying metadata filter.")
        # This 'where' clause is the metadata filter. It's extremely powerful.
        filter_dict = {"source": document_id}
    else:
        print(f"\n1. No specific document ID detected. Performing a broad semantic search.")

    print(f"   Querying for: '{query_text}'...")
    
    # The 'where' parameter applies the filter before the search
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        where=filter_dict # This will be None for broad searches, or a filter dict for specific ones
    )
    
    return results['documents'][0] if results and results.get('documents') else []

def generate_final_answer(query_text, retrieved_docs):
    """
    Stage 2: Use a powerful LLM to read the retrieved documents and synthesize a final answer.
    """
    if not retrieved_docs:
        # Provide a more helpful message if filtering was used
        document_id = extract_document_id(query_text)
        if document_id:
            return f"I found the knowledge base, but I could not find a document with the source ID '{document_id}'. Please check if the document exists."
        return "I couldn't find any relevant documents in the knowledge base to answer your question."

    client = openai.OpenAI()
    context_str = "\n\n---\n\n".join(retrieved_docs)

    system_prompt = """
    You are an expert Q&A system. You are given a user's question and a set of context documents.
    Your task is to answer the user's question based ONLY on the information provided in the context documents.
    If the answer is not available in the provided context, you must state that clearly.
    Do not use any outside knowledge. Be concise and precise.
    """

    user_prompt = f"""
    CONTEXT DOCUMENTS:
    {context_str}

    USER'S QUESTION:
    {query_text}

    ANSWER:
    """

    print("\n2. Synthesizing final answer with LLM...")

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"An error occurred while generating the final answer: {e}"

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query the utility documents knowledge base.")
    parser.add_argument("query_text", type=str, help="The question you want to ask.")
    args = parser.parse_args()

    # Stage 1: Retrieve relevant documents (now with filtering!)
    documents = retrieve_relevant_documents(args.query_text)

    # Stage 2: Synthesize the final answer
    final_answer = generate_final_answer(args.query_text, documents)

    print("\n" + "="*50)
    print("      Final Answer")
    print("="*50 + "\n")
    print(final_answer)
    print("\n" + "="*50)