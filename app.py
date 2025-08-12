<<<<<<< HEAD
import streamlit as st
import os
import json
import pandas as pd

# Import our consolidated backend logic
from pipeline import run_end_to_end_pipeline
# Import our RAG query logic
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from openai import OpenAI

# --- STYLING (The Bulletproof "Forced Light" Theme) ---
st.set_page_config(
    layout="wide",
    page_title="Document Intelligence Pipeline",
    page_icon="🤖"
)

# This CSS block is much more specific and forceful. It targets Streamlit's
# internal component names to override the default dark theme completely.
st.markdown("""
<style>
    /* Force a light background on the main container and sidebar */
    [data-testid="stAppViewContainer"] {
        background-color: #FFFFFF !important; /* Pure white main area */
    }
    [data-testid="stSidebar"] {
        background-color: #F0F2F6 !important; /* Light grey sidebar */
    }

    /* Force a dark text color on all text elements, overriding the theme */
    h1, h2, h3, h4, h5, h6, p, li, label, .st-emotion-cache-16idsys p {
        color: #1d1d1f !important;
    }

    /* Style the header bar */
    [data-testid="stHeader"] {
        background-color: #FFFFFF;
        border-bottom: 1px solid #d2d2d7;
    }

    /* Clean up the info box to have high contrast */
    [data-testid="stInfo"] {
        background-color: #e9f5ff;
        border-radius: 10px;
        border: 1px solid #cce5ff;
    }
    [data-testid="stInfo"] p {
        color: #004085 !important; /* Dark blue text on light blue background */
    }

    /* Style the text input box */
    [data-testid="stTextInput"] input {
        background-color: #FFFFFF !important;
        color: #1d1d1f !important;
        border: 1px solid #d2d2d7 !important;
        border-radius: 8px !important;
    }

    /* Style the tabs */
    [data-testid="stTabs"] button {
        color: #888888;
    }
    [data-testid="stTabs"] button[aria-selected="true"] {
        color: #0071e3;
        border-bottom: 2px solid #0071e3;
    }

    /* Style the main button */
    .stButton>button {
        border-radius: 8px;
        border: 1px solid #0071e3;
        background-color: #0071e3;
        color: #ffffff !important; /* Force white text on the button */
    }
</style>
""", unsafe_allow_html=True)

def cleanup_intermediate_folders():
    """
    Wipes and recreates all temporary directories to ensure a clean run.
    This prevents processing leftover files from previous runs.
    """
    st.write("Preparing a clean workspace...")
    dirs_to_clean = [
        "source_pdfs", 
        "corrected_pdfs", 
        "generic_json_outputs", 
        # We don't clean final_json_outputs so the user can see the last run's output
        # We also don't clean manual_review_needed or vector_db
    ]
    for directory in dirs_to_clean:
        if os.path.isdir(directory):
            shutil.rmtree(directory) # Delete the entire folder and its contents
        os.makedirs(directory) # Recreate the empty folder
    st.write("Workspace is clean.")

# --- RAG QUERY FUNCTIONS (No changes needed) ---
def retrieve_relevant_documents(query_text, n_results=15):
    embedding_function = OpenAIEmbeddingFunction(api_key=os.getenv("OPENAI_API_KEY"), model_name="text-embedding-3-small")
    client = chromadb.PersistentClient(path="vector_db/")
    collection = client.get_collection(name="utility_docs", embedding_function=embedding_function)
    results = collection.query(query_texts=[query_text], n_results=n_results)
    return results['documents'][0] if results and results.get('documents') else []

def generate_final_answer(query_text, retrieved_docs):
    if not retrieved_docs:
        return "I couldn't find any relevant documents to answer that."
    client = OpenAI()
    context_str = "\n\n---\n\n".join(retrieved_docs)
    system_prompt = "You are an expert Q&A system. Answer the user's question based ONLY on the provided context documents. If the answer isn't in the context, say so."
    user_prompt = f"CONTEXT DOCUMENTS:\n{context_str}\n\nUSER'S QUESTION:\n{query_text}\n\nANSWER:"
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.0
    )
    return response.choices[0].message.content

# --- STREAMLIT APP (No functional changes needed) ---
st.title("Document Intelligence Pipeline")
st.write("An end-to-end solution for ingesting, structuring, and querying utility documents.")

=======

import streamlit as st
import os

from query_rag import retrieve_relevant_documents, generate_final_answer

# --- Page Configuration ---
st.set_page_config(
    page_title="PowerKiosk Utility Bill RAG System",
    layout="centered"
)

# --- Main App UI ---
st.title("PowerKiosk Utility Document Query Agent")
st.write("This tool uses a Retrieval-Augmented Generation (RAG) system to answer questions about your indexed utility documents.")

# Check for API key at the start
>>>>>>> 10c696eb12ea562d1154cfa5b2a7ec9b848a3fe1
if 'OPENAI_API_KEY' not in os.environ:
    st.error("FATAL ERROR: The OPENAI_API_KEY environment variable is not set.")
    st.stop()

<<<<<<< HEAD
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = []

tab1, tab2 = st.tabs(["Query Knowledge Base", "Add New Documents"])

with tab1:
    st.header("Ask a Question")
    st.info("The knowledge base is ready. Ask any question about the ingested documents.")
    query = st.text_input("Enter your question:", key="rag_query")
    if query:
        with st.spinner("Searching..."):
            retrieved = retrieve_relevant_documents(query)
            answer = generate_final_answer(query, retrieved)
            st.success("Answer:")
            st.markdown(answer)

with tab2:
    st.header("Upload and Process New PDFs")
    UPLOAD_DIR = "source_pdfs/"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    uploaded_files = st.file_uploader("Choose PDF files", type="pdf", accept_multiple_files=True)
    if st.button("Process Uploaded Files"):
        if uploaded_files:
            # (The rest of the file processing logic is the same)
            # ...
            saved_file_paths = []
            for uploaded_file in uploaded_files:
                file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                saved_file_paths.append(file_path)

            progress_bar = st.progress(0, text="Starting Pipeline...")
            status_text = st.empty()
            def update_status(message):
                status_text.info(message)
                if "1/5" in message: progress_bar.progress(20, text="Fixing Rotations...")
                if "2/5" in message: progress_bar.progress(40, text="Converting to Generic JSON...")
                if "3/5" in message: progress_bar.progress(60, text="Creating Final JSON...")
                if "4/5" in message: progress_bar.progress(80, text="Running QC Flags...")
                if "5/5" in message: progress_bar.progress(100, text="Updating Knowledge Base...")

            with st.spinner("Running full ingestion pipeline... This may take several minutes."):
                processed_json = run_end_to_end_pipeline(saved_file_paths, update_status)
            
            st.session_state.processed_data = processed_json
            st.success("Pipeline complete! The knowledge base has been updated.")
            st.balloons()
            
        else:
            st.warning("Please upload at least one PDF file.")

    if st.session_state.processed_data:
        st.divider()
        st.header("Extracted Information from Last Run")
        
        for item in st.session_state.processed_data:
            with st.expander(f"**{item.get('documentId')}** - Issuer: {item.get('issuer')}"):
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Customer", item.get('customerName', 'N/A'))
                col2.metric("Statement Date", item.get('statementDate', 'N/A'))
                col3.metric("Total Usage", f"{item.get('totalUsage', 0)} {item.get('unit', '')}")
                
                if item.get('_qc_flag'):
                    col4.error(f"QC Flag: {item.get('_qc_reason')}")
                else:
                    col4.success("QC Passed")

                st.write("**Usage History:**")
                if item.get('usageHistory'):
                    df = pd.DataFrame(item['usageHistory'])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.write("No usage history found.")
                
                with st.popover("View Full Extracted JSON"):
                    st.json(item)
=======
# Create a text input box for the user's question
query = st.text_input(
    "**Ask a question about your documents:**",
    placeholder="e.g., What is the total usage for document_1124?"
)

with st.expander("Example Questions to Try"):
    st.markdown("""
    *   What is the customer name for document_999?
    *   List all account numbers in document_119.
    *   Show me contracts with service addresses in Philadelphia, PA
    """)

# --- Backend Logic ---
if query:
    with st.spinner("Searching knowledge base and synthesizing answer..."):
        try:
            retrieved_docs = retrieve_relevant_documents(query)
            final_answer = generate_final_answer(query, retrieved_docs)

            st.divider()
            st.markdown("### Answer:")
            st.markdown(final_answer)

        except Exception as e:
            st.error(f"An error occurred: {e}")
>>>>>>> 10c696eb12ea562d1154cfa5b2a7ec9b848a3fe1
