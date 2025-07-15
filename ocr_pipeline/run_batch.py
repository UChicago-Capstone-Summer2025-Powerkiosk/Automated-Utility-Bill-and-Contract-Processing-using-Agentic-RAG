from pipeline.extract_text import extract_chunks
from pipeline.classify_doc import classify
from pipeline.extract_fields import extract
from pathlib import Path
import json, logging

def run_batch(batch_folder, batch_size=100):
    out = []
    for pdf in Path(batch_folder).glob("*.pdf")[:batch_size]:
        chunks = extract_chunks(pdf)
        text = "\n".join(c.text for c in chunks)
        doc_type = classify(text)
        data = extract(doc_type, text)
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            logging.warning(f"Malformed JSON for {pdf.name}")
            parsed = {"_incomplete": True, "raw": data}
        parsed["_file"] = pdf.name
        out.append(parsed)
    with open("data/output_json/batch.json","w") as f:
        json.dump(out, f, indent=2)
