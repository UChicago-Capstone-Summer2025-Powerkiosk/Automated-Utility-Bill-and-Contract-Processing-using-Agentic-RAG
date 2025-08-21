import os
import fitz
import json
import base64
from PIL import Image
from tqdm import tqdm
from io import BytesIO
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from utils import llm_response_to_json

llm = ChatOpenAI(
    model="gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.5,
)

system_message_by_similar_page = """
You are an expert in understanding images and matching 2 images by template matching.

We have a document with multiple bills attached in a single document.
We want to detect when a new bill starts in the document for which we will compare the first page of the document (definitely the first page of a bill) with each page of the document one by one.
Determine if the template of the pages match without considering the text present in the image.
You will be given the images of such two pages.

Your task is to determine if the 2 pages are same as per the template and things/tables/charts contained within them thus representing the start of a new bill. 
The bills may be of multiple pages thus if the template matches, we say the new bill has started else we say that the same is continuing.

Output Schema:
Your response should be JSON serializable in the schema mentioned below:
```
{{
    "do_the_pages_match" : (bool) <'true' if the template matched and new bill has started else 'false'>
}}
```

No talk, Just go.
""".strip()


def read_json(path):
    with open(path, "r") as file:
        data = json.load(file)
    return data


def get_bill_pages(pdf_path: Path):
    # Load PDF and LLM
    doc = fitz.open(pdf_path)

    outputs = {}
    page_images = []
    for i, page in tqdm(list(enumerate(doc))):
        pix = page.get_pixmap(dpi=170)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        b64_image = base64.b64encode(buffer.getvalue()).decode()
        page_images.append(b64_image)

    pages = [[1, len(page_images)]]
    for ind in tqdm(range(1, len(page_images))):
        response = llm_response_to_json(
            llm.invoke(
                [
                    SystemMessage(content=system_message_by_similar_page),
                    HumanMessage(
                        content=[
                            {
                                "type": "text",
                                "text": f"Image of the first page of the document.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{page_images[0]}"
                                },
                            },
                            {"type": "text", "text": f"Image of other page."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{page_images[ind]}"
                                },
                            },
                        ]
                    ),
                ]
            ).content
        )
        print(f"{ind+1} : {response}")
        if response["do_the_pages_match"]:
            pages[-1][1] = ind
            pages.append([ind + 1, len(page_images)])

    print()
    print(pages)
    return pages


def split_pdf(input_pdf_path: Path, output_specs):
    if len(output_specs) == 1:
        return [input_pdf_path]

    final_paths = []
    doc = fitz.open(input_pdf_path)
    for idx, (start, end) in enumerate(output_specs):
        sub_doc = fitz.open()
        for page_num in range(start - 1, end):  # PyMuPDF uses 0-based indexing
            sub_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

        split_pdf_path = Path(
            ".".join(str(input_pdf_path).split(".")[:-1]) + f"_{start}_{end}.pdf"
        )
        sub_doc.save(split_pdf_path)
        final_paths.append(split_pdf_path)
        sub_doc.close()
    doc.close()

    return final_paths
