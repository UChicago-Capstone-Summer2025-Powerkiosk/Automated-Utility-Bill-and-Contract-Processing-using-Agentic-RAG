import openai
PROMPT = Path("prompts/classify_prompt.txt").read_text()

def classify(doc_text):
    resp = openai.ChatCompletion.create(…)
    return resp.choices[0].message.content.strip()  # “contract” or “bill”
