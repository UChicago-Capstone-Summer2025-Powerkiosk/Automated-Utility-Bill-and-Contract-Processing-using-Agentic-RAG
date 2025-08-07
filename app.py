
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
if 'OPENAI_API_KEY' not in os.environ:
    st.error("FATAL ERROR: The OPENAI_API_KEY environment variable is not set.")
    st.stop()

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