import os
import json
from pathlib import Path
from google import genai
from typing import Any, List
from pdf2image import convert_from_path
from pydantic import ValidationError, TypeAdapter

from prompts import get_image_validation_prompt
from config import ONEDRIVE_PATH, ONEDRIVE_PATH_WIN, POPPLER_PATH
from models import LineCorrection, adapter_im2txt, loose_adapter_im2txt
from utils import fix_llm_json, normalize_null_strings, logger, fix_json_algo


google_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# "models/gemini-2.5-flash-preview-05-20"
def send_gemini_query(
    prompt, image_path, model="models/gemini-2.5-flash-preview-05-20", logger=None
):

    my_file = google_client.files.upload(
        file=image_path,
    )

    response = google_client.models.generate_content(
        model=model,
        contents=[my_file, prompt],
    )
    if logger:
        logger.log_prompt(
            step="gemini_image_query",
            system=f"Gemini model: {model}",
            user=prompt,
            output=response.text,
            meta={"image_path": image_path},
        )

    return response.text


def llm_fix_with_image_and_text(
    llm_raw: str,
    error: Exception,
    extracted_md: str,
    image_path: str,
) -> str:
    """
    Attempts to repair invalid JSON corrections using LLM with image and markdown context.
    Returns a string (expected to be JSON) from the LLM.
    """
    user_prompt = (
        "You are an expert at validating OCR markdown extraction from images. "
        "Given a markdown table, its corresponding image, and a possibly invalid correction JSON, "
        "your job is to return a corrected JSON that lists any lines in the markdown with mistakes, "
        "as shown in the image. Use the schema: "
        '[{"original_line": <string>, "corrected_line": <string>}, ...]. '
        "If all lines are correct, return []."
        f"\n\nHere is the extracted markdown:\n\n{extracted_md}\n\n"
        f"Here is the previous correction JSON (may be invalid or incomplete):\n{llm_raw}\n\n"
        f"The error message from the last validation was: {str(error)}\n\n"
        "Please cross-check each markdown line with the provided image and return the corrected JSON."
    )
    response = send_gemini_query(user_prompt, image_path)
    return response


def fix_with_llm_image(
    extracted_md: str,
    image_path: str,
    error: Exception,
) -> str:
    """
    Final LLM repair using both markdown and image context, regardless of previous JSON.
    Returns a string (expected to be JSON) from the LLM.
    """
    user_prompt = (
        f"Task: Given the following markdown extracted from an image, and the image itself, "
        "produce a JSON array listing any lines in the markdown that are incorrect when compared to the image. "
        "Each object in the array should have 'original_line' and 'corrected_line'. "
        "If all lines are correct, return an empty array ([]).\n\n"
        f"The error message from the last validation was: {str(error)}\n\n"
        f"Markdown:\n{extracted_md}\n"
    )
    response = send_gemini_query(user_prompt, image_path)
    return response


def im2txt(
    pdf_folder_path, pdf_path: Path, image_prprocess_prompt, logger=None, model=None
):
    image_folder = os.path.join(
        pdf_folder_path, f"images_{pdf_path.with_suffix('').name}"
    )

    # --- Ensure output folder exists ---

    os.makedirs(image_folder, exist_ok=True)
    # logger.info("Converting PDF to images for: {}", pdf_folder_path)

    # --- 1. PDF -> Images ---
    try:
        if ONEDRIVE_PATH == ONEDRIVE_PATH_WIN:
            try:
                pages = convert_from_path(
                    pdf_path=pdf_path,
                    dpi=600,
                    poppler_path=POPPLER_PATH,
                )
                print("dpi=600")
            except:
                try:
                    pages = convert_from_path(
                        pdf_path=pdf_path,
                        dpi=400,
                        poppler_path=POPPLER_PATH,
                    )
                    print("dpi=400")
                except:
                    try:
                        pages = convert_from_path(
                            pdf_path=pdf_path,
                            dpi=300,
                            poppler_path=POPPLER_PATH,
                        )
                        print("dpi=300")
                    except:
                        pages = convert_from_path(
                            pdf_path=pdf_path,
                            dpi=200,
                            poppler_path=POPPLER_PATH,
                        )
                        print("dpi=200")

        else:
            try:
                pages = convert_from_path(
                    pdf_path=pdf_path,
                    dpi=600,
                )
            except:
                try:
                    pages = convert_from_path(
                        pdf_path=pdf_path,
                        dpi=400,
                    )
                except:
                    try:
                        pages = convert_from_path(
                            pdf_path=pdf_path,
                            dpi=300,
                        )
                        print("dpi=300")
                    except:
                        pages = convert_from_path(
                            pdf_path=pdf_path,
                            dpi=200,
                        )
                        print("dpi=200")

        image_paths = []

        # delete_duplicated_images(image_folder)

        for idx, page in enumerate(pages, start=1):
            img_path = os.path.join(image_folder, f"image_{idx}.png")
            page.save(img_path, "PNG")
            print("image saved")
            image_paths.append(img_path)
        # logger.success("Saved all images for document {}", number)
    # --- 2. Extract from each image ---
    except Exception as e:
        # logger.error("Failed to convert PDF to images: {}", e)
        raise
    # logger.info("Extracting from images for document {}", number)
    md_outputs = []
    # models/gemini-2.5-flash-preview-05-20
    # "models/gemini-2.5-pro-preview-06-05"
    for i, img_path in enumerate(image_paths, start=1):
        # Replace this with your real send_query implementation
        if model:
            model_ = model

        else:
            model_ = "models/gemini-2.5-flash-preview-05-20"
        md_text = send_gemini_query(image_prprocess_prompt, img_path, model_)
        if logger:
            logger.log_step(
                step=f"image_processing_{i}",
                status="error",
                input={
                    "image_prprocess_prompt": str(image_prprocess_prompt),
                    "image_path": img_path,
                },
                output=md_text,
            )
        validation_prompt = get_image_validation_prompt(md_text)
        fixed_md = get_validated_im2md(
            validation_prompt,
            img_path,
            adapter_im2txt,
            loose_adapter_im2txt,
            md_text,
            logger,
            i,
        )

        if logger:
            logger.log_step(
                step=f"image_validation_{i}",
                status="error",
                input={
                    "validation_prompt": str(validation_prompt),
                    "image_path": img_path,
                },
                output=fixed_md,
            )
        md_outputs.append(f"## Page {i}\n\n{fixed_md}\n")

    # --- 3. Combine ---

    final_md = "\n".join(md_outputs)

    # Optionally, save or #print
    with open(pdf_path.with_suffix(".md"), "w", encoding="utf-8") as f:
        f.write(final_md)
    # logger.info("Successfully generated markdown extraction for {}", number)
    return final_md


def get_image_validation(
    llm_raw: str,
    strict_adapter: TypeAdapter[Any],
    loose_adapter: TypeAdapter[Any],
    extracted_md: str,
    image_path: str,  # Could also be image bytes, etc.
) -> Any:
    """
    1) Parse & normalize JSON → strict_adapter.validate_python
    2) On failure → llm_fix_with_image_and_text → strict_adapter.validate_python
    3) On failure → fix_with_llm_image → loose_adapter.validate_python
    4) On ultimate failure → return raw dict
    """
    clean_json = None

    try:
        clean_json = fix_llm_json(llm_raw)

        if isinstance(clean_json, dict) and clean_json.get("Pass") == "Pass":
            return clean_json

        clean_json = normalize_null_strings(clean_json)
        parsed = strict_adapter.validate_python(clean_json)
        return parsed

    except (json.JSONDecodeError, ValidationError) as e1:
        try:
            # First, attempt to repair using all context
            corrected = llm_fix_with_image_and_text(
                llm_raw, e1, extracted_md, image_path
            )
            clean_json = fix_llm_json(corrected)
            clean_json = normalize_null_strings(clean_json)
            parsed = strict_adapter.validate_python(clean_json)
            return parsed

        except Exception as e2:
            try:
                # Final fallback: fresh attempt using just markdown & image
                fallback_fixed = fix_with_llm_image(extracted_md, image_path, e2)
                clean_json = fix_llm_json(fallback_fixed)
                clean_json = normalize_null_strings(clean_json)
                parsed = loose_adapter.validate_python(clean_json)
                return parsed

            except Exception as e3:
                if isinstance(clean_json, dict):
                    return clean_json
                try:
                    raw_dict = json.loads(llm_raw or "{}")
                    return raw_dict
                except Exception as e4:
                    try:
                        raw_dict = fix_json_algo(llm_raw)
                        return raw_dict
                    except Exception as e5:
                        print(
                            f"Any of validation method didnt work for this '{llm_raw}' we return empty list"
                        )
                        return []


def get_validated_im2md(
    validation_prompt, img_path, strict_adapter, loose_adapter, first_md, logger, i
):
    def patch_markdown(md_text: str, corrections: List[LineCorrection]) -> str:
        lines = md_text.splitlines()
        corrections_map = {c.original_line: c.corrected_line for c in corrections}
        fixed_lines = [corrections_map.get(line, line) for line in lines]
        return "\n".join(fixed_lines)

    corrections_json = send_gemini_query(validation_prompt, img_path)
    if logger:
        logger.log_step(
            step=f"image_correction_{i}",
            status="error",
            input={
                "validation_prompt": validation_prompt,
                "image_path": img_path,
            },
            output=corrections_json,
        )
    if not corrections_json:
        fixed_md = ""
    else:
        print(corrections_json)
        validated_corrections = get_image_validation(
            llm_raw=corrections_json,  # Your LLM’s raw output
            strict_adapter=strict_adapter,
            loose_adapter=loose_adapter,
            extracted_md=first_md,  # Can be ""
            image_path=img_path,
        )

        try:
            fixed_md = patch_markdown(first_md, validated_corrections)
        except:
            fixed_md = first_md
    return fixed_md