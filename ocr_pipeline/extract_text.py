from agentic_doc.parse import parse_documents
from pathlib import Path

def extract_chunks(pdf_path):
    results = parse_documents([str(pdf_path)])
    return results[0].chunks  # list of page-aware text chunks
