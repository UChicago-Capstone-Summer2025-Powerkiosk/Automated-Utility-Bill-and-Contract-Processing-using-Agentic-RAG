import os
import json
import base64
import inspect
import datetime
import mimetypes
import regex as re
# from google import genai
from pathlib import Path
from openai import OpenAI
from pdf2image import convert_from_path
from json_repair import repair_json as js
from fix_busted_json import repair_json as fbj
from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from typing import get_origin, get_args, Type, Union, List, Literal, Optional, Dict, Any

from prompts import get_image_validation_prompt
from models import adapter_im2txt, loose_adapter_im2txt
from config import logger, ONEDRIVE_PATH, POPPLER_PATH, ONEDRIVE_PATH_WIN

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def send_query(system_message, user_message, file_path=None, logger=None):
    input_messages = [
        {
            "role": "system",
            "content": [{"type": "input_text", "text": system_message}],
        }
    ]

    file_content = []

    if file_path:
        path = Path(file_path)
        mime_type, _ = mimetypes.guess_type(path)
        ext = path.suffix.lower()

        if ext == ".pdf" or mime_type == "application/pdf":
            # Upload PDF to assistant file store
            uploaded_file = client.files.create(
                file=open(path, "rb"), purpose="assistants"
            )

            file_content.append({"type": "input_file", "file_id": uploaded_file.id})
        elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
            # Encode image to base64
            with open(path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
            file_content.append(
                {
                    "type": "input_image",
                    "image_url": f"data:{mime_type};base64,{encoded_image}",
                }
            )
        else:
            raise ValueError("Unsupported file type. Must be PDF or image.")

    # Add user message and any attached content (PDF or image)
    input_messages.append(
        {
            "role": "user",
            "content": [{"type": "input_text", "text": user_message}] + file_content,
        }
    )
    if logger:
        logger.log_prompt(
            step="send_query",
            system=system_message,
            user=user_message,
            output=None,
            meta={"file_path": file_path},
        )
    # Send to API
    response_obj = client.responses.create(
        model="gpt-4.1-mini",
        input=input_messages,
        text={"format": {"type": "text"}},
        reasoning={},
        tools=[],
        temperature=0.2,
        max_output_tokens=2048,
        top_p=1,
        store=True,
    )

    response = response_obj.output[0].content[0].text
    return response, response_obj


def fix_with_llm(
    raw_input: Union[str, dict],
    error: Union[ValidationError, str],
    model: Type[BaseModel],
) -> str:
    """
    Uses LLM to fix a raw JSON-like input to match a given Pydantic schema.
    Parameters:
        raw_input: str or dict — LLM's raw JSON or Python object
        error: a Pydantic ValidationError or string describing the error
        model: the Pydantic model class to conform to

    Returns:
        A fixed JSON string (can be parsed/validated again)
    """

    # Serialize raw input
    if isinstance(raw_input, dict):
        data_str = json.dumps(raw_input, indent=2)
    else:
        data_str = raw_input.strip()

    # Normalize error
    error_str = str(error)
    # Generate full schema description
    schema_str = describe_model_fields(model)

    # Build prompt
    prompt = f"""
You are a JSON-fixing assistant.

Your task is to correct the following JSON object so it matches this schema.

Schema:
{schema_str}

Validation errors:
{error_str}

Original data:
{data_str}

Return only corrected JSON. No explanation. No commentary. Just valid JSON.

Important formatting rules:

- You must return only valid JSON. No Markdown formatting, no explanation.
- Do not wrap the JSON in triple backticks (```).
- Use double quotes for all keys and string values.
- Do not include comments.
- Do not leave trailing commas.
- Ensure arrays and objects are properly closed.
- Do not add any prefix or suffix — return the JSON object directly.
- Do not generate or infer any values not present in the source. Only extract explicit values. Leave missing or unavailable fields empty.

Example of valid JSON:
{{ "example": "value", "list": [1, 2, 3] }}
"""

    # Send to LLM (assuming send_query is defined elsewhere)
    response, _ = send_query(
        system_message="You fix and clean JSON data to match strict schemas.",
        user_message=prompt,
        file_path=None,
    )

    return response


def describe_model_fields(model: Type, depth: int = 0) -> str:
    if isinstance(model, TypeAdapter):
        return describe_model_fields(model._type, depth)
    lines = []
    origin = get_origin(model)

    # Handle Dict[str, Union[...]]
    if origin in {dict, Dict}:
        value_type = get_args(model)[1]
        return describe_model_fields(value_type, depth)

    # Handle Union[ModelA, ModelB, ...]
    if origin is Union:
        for t in get_args(model):
            if inspect.isclass(t) and issubclass(t, BaseModel):
                lines.append(
                    f"{t.__name__}:\n{indent(describe_model_fields(t, depth + 1), '  ')}"
                )
        return "\n\n".join(lines)

    # Handle actual BaseModel
    if inspect.isclass(model) and issubclass(model, BaseModel):
        for field_name, field_info in model.model_fields.items():
            field_type = field_info.annotation
            origin = get_origin(field_type)
            args = get_args(field_type)

            base_model_types = [
                t
                for t in [field_type, *args]
                if inspect.isclass(t) and issubclass(t, BaseModel)
            ]

            if base_model_types and depth < 1:
                nested_model = base_model_types[0]
                nested = describe_model_fields(nested_model, depth + 1)
                lines.append(
                    f"- {field_name}: object with fields:\n{indent(nested, '    ')}"
                )
            else:
                type_str = format_type(field_type)
                lines.append(f"- {field_name}: {type_str}")

        return "\n".join(lines)

    return f"Unsupported type: {model}"


def format_type(t) -> str:
    """Render a type hint as a clean string."""
    origin = get_origin(t)
    args = get_args(t)

    if origin is Union:
        return " or ".join(format_type(a) for a in args)
    elif origin in (list, List):
        return f"list[{format_type(args[0])}]" if args else "list"
    elif origin is Literal:
        return f"Literal[{', '.join(repr(a) for a in args)}]"
    elif inspect.isclass(t):
        return t.__name__
    else:
        return str(t).replace("typing.", "").replace("NoneType", "null")


def indent(text: str, prefix: str) -> str:
    return "\n".join(
        prefix + line if line.strip() else line for line in text.splitlines()
    )


def generate_json_fix_prompt(
    original_prompt: str,
    schema_str: str,
    error_str: str,
    original_text: str,
) -> str:
    return f"""
You are a JSON-fixing assistant.

The following prompt was originally used to generate this data:
---
{original_prompt.strip()}
---

Now, your task is to correct the output to match this schema:

Schema:
{schema_str}

Validation errors:
{error_str}

Original output from the first LLM:
{original_text.strip()}

⚠️ Structural rules:
- Each key in the top-level JSON object must map to one of the schema-compliant values.
- Do not nest under type names like "ServiceEntry" or "PassResponse".
- Use simple keys like "entry_1", "entry_2", etc.

Return valid JSON only. No explanations. No markdown. No trailing commas. No wrapping.
"""


def llm_fix_with_original_text(
    original_prompt, original_text: str, error: ValidationError, model: Type[BaseModel]
) -> str:
    """
    Smarter fallback: fix only the specific fields that failed validation,
    using the original text for context.
    """

    schema_str = describe_model_fields(model)
    error_items = error.errors()

    # Build readable list of error paths
    broken_fields = "\n".join(
        f"- Field path: {'.'.join(map(str, err['loc']))} — Error: {err['msg']}"
        for err in error_items
    )

    prompt = generate_json_fix_prompt(
        original_prompt, schema_str, broken_fields, original_text
    )
    # #print("prompt of llm_original:", prompt)
    response, _ = send_query(
        system_message="You are a JSON repair assistant. Fix only the broken fields based on schema.",
        user_message=prompt,
        file_path=None,
    )

    return response


def fix_llm_json(llm_response):
    try:
        response_clear = re.sub("```json|```|\n", "", llm_response)
    except:
        response_clear = llm_response
    if response_clear == '{"Pass"}':
        return {"Pass": "Pass"}
    else:
        responce_dict = json.loads(response_clear)
        return responce_dict


def normalize_null_strings(value):
    if isinstance(value, dict):
        return {k: normalize_null_strings(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [normalize_null_strings(v) for v in value]
    elif isinstance(value, str) and (
        value.strip() == "" or value.strip().lower() == "null"
    ):
        return None
    else:
        return value


def fix_json_algo(broken_json):
    try:
        fixed_json_str = js(broken_json)
        parsed = json.loads(fixed_json_str)

    except Exception:
        fixed_json_str = fbj(broken_json)
        parsed = json.loads(fixed_json_str)

    return parsed


import re
import json
from copy import deepcopy
from typing import List, Dict, Union


class CustomJSONDecoder(json.JSONDecoder):
    def __init__(self, *args, process_func=None, **kwargs):
        super().__init__(*args, **kwargs, object_hook=self.object_hook)
        self.process_func = process_func

    def object_hook(self, dct):

        # Apply processing function to string values in dictionaries
        return {k: self.process_values(v) for k, v in dct.items()}

    def process_values(self, value):
        if isinstance(value, dict):
            return {k: self.process_values(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.process_values(item) for item in value]
        elif isinstance(value, str):
            return value.replace(" " * 100, "\n")
        else:
            return value


def convert_string_to_json(string_to_convert):
    # Remove any non-printable characters except newlines and tabs
    cleaned_string = re.sub(r"[^\x20-\x7E]", " " * 100, string_to_convert)

    # Escape newline characters within the string
    fixed_string = re.sub(r"(?<!\\)\n", r"\\n", cleaned_string)

    try:
        # Loading JSON
        return json.loads(fixed_string, cls=CustomJSONDecoder)
    except:
        # Managing double quotes
        quotes_managed = deepcopy(fixed_string)
        matches = re.finditer(r"(\".*\"\s*:\s*)\"(.*)\",?\s*\n", quotes_managed)
        for match in matches:
            if '"' in match.groups()[1]:
                start = match.start()
                end = match.end()
                quotes_managed = (
                    quotes_managed[:start]
                    + match.groups()[0]
                    + '"'
                    + match.groups()[1].replace('"', r"\"")
                    + '"'
                    + quotes_managed[end:]
                )

        # Loading JSON
        return json.loads(quotes_managed, cls=CustomJSONDecoder)


def llm_response_to_json(llm_response: str) -> Union[List, Dict]:
    # Clearing extra text if any
    llm_response = re.sub(r"^[^\[\{]*", "", llm_response)
    llm_response = re.sub(r"[^\]\}]*$", "", llm_response)

    try:
        return convert_string_to_json(llm_response)
    except:
        print(f"Response:\n{llm_response}")
        raise SyntaxError(f"Could not convert the LLM response to JSON format.")


from PIL import Image
import imagehash
import os
from collections import defaultdict


def delete_duplicated_images(folder_path):

    # Load and hash images
    hash_groups = defaultdict(list)
    image_paths = sorted([f for f in os.listdir(folder_path) if f.endswith(".png")])

    # Compare each image's hash
    for file in image_paths:
        path = os.path.join(folder_path, file)
        img = Image.open(path).convert("RGB")
        h = imagehash.phash(img)

        # Try to group by near-duplicate (distance ≤ 3)
        matched = False
        for existing_hash in hash_groups:
            if h - imagehash.hex_to_hash(existing_hash) <= 3:
                hash_groups[existing_hash].append(path)
                matched = True
                break
        if not matched:
            hash_groups[str(h)].append(path)

    # Print and optionally delete duplicates
    for h, files in hash_groups.items():
        if len(files) > 1:
            print("\nDuplicate group:")
            for f in files:
                print(f" - {f}")
            print(f"Removing last one: {files[-1]}")
            os.remove(files[-1])  # Comment this out to just print