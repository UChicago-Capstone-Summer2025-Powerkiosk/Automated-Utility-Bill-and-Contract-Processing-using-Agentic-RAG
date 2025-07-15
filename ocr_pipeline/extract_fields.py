import openai
PROMPT = Path("prompts/extract_prompt.txt").read_text()

def extract(doc_type, doc_text):
    prompt = PROMPT.replace("<<DOC_TYPE>>", doc_type).replace("<<DOC_TEXT>>", doc_text)
    resp = openai.ChatCompletion.create(…)
    return resp.choices[0].message.content  # JSON string
