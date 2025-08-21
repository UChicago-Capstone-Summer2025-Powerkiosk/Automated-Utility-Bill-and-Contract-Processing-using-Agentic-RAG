# In app.py (Final Polished and Functional Version)

import streamlit as st
import os
import json
import pandas as pd
import shutil

# Import our consolidated backend logic
from pipeline import process_single_pdf, update_knowledge_base
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

# This CSS block is highly specific to override Streamlit's default dark theme.
st.markdown("""
<style>
    /* Force a light background on the main container */
    [data-testid="stAppViewContainer"] {
        background-color: #FFFFFF !important; /* Pure white main area */
    }

    /* Force a dark text color on all text elements */
    h1, h2, h3, h4, h5, h6, p, li, label, .st-emotion-cache-16idsys p {
        color: #1d1d1f !important;
    }

    /* Clean up the info box for high contrast */
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


# --- RAG QUERY FUNCTIONS ---
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

# --- HELPER FUNCTIONS ---
def cleanup_intermediate_folders():
    """Wipes and recreates temporary directories for a clean run."""
    st.write("Preparing a clean workspace...")
    dirs_to_clean = ["source_pdfs", "corrected_pdfs", "generic_json_outputs"]
    for directory in dirs_to_clean:
        if os.path.isdir(directory):
            shutil.rmtree(directory)
        os.makedirs(directory)
    st.write("Workspace is clean.")

# --- STREAMLIT APP ---
st.title("Document Intelligence Pipeline")
st.write("An end-to-end solution for ingesting, structuring, and querying utility documents.")

if 'OPENAI_API_KEY' not in os.environ or 'VISION_AGENT_API_KEY' not in os.environ:
    st.error("FATAL ERROR: One or more API keys (OPENAI_API_KEY, VISION_AGENT_API_KEY) are not set.")
    st.stop()

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
    uploaded_files = st.file_uploader("Choose PDF files to add to the knowledge base", type="pdf", accept_multiple_files=True)

    if st.button("Process Uploaded Files"):
        if uploaded_files:
            cleanup_intermediate_folders()
            
            saved_file_paths = []
            for uploaded_file in uploaded_files:
                file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                saved_file_paths.append(file_path)

            st.session_state.processed_data = []
            processed_json_list = []
            progress_bar = st.progress(0, text="Starting pipeline...")
            status_text = st.empty()

            for i, file_path in enumerate(saved_file_paths):
                filename = os.path.basename(file_path)
                progress_percentage = (i) / len(saved_file_paths)
                progress_bar.progress(progress_percentage, text=f"Processing file {i+1}/{len(saved_file_paths)}: {filename}")
                def status_callback(message):
                    status_text.info(f"File: {filename} - {message}")
                final_json = process_single_pdf(file_path, status_callback)
                processed_json_list.append(final_json)

            status_text.info("All files processed. Updating knowledge base...")
            progress_bar.progress(95, text="Updating knowledge base...")
            update_knowledge_base(processed_json_list)
            
            st.session_state.processed_data = processed_json_list
            progress_bar.progress(100, text="Pipeline complete!")
            status_text.success("Pipeline complete! The knowledge base has been updated.")
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