import cv2
import time
import numpy as np
from PIL import Image
from ultralytics import YOLO
import matplotlib.pyplot as plt
from collections import defaultdict
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes

from utils import send_query
from config import logger, client_ocr


def extract_bars_from_image(img, impath):
    # Reapply padding
    # Example 8 (Sample Bill)/images/2_1.png'
    # Example 1 (Sample Bill)/images/1_1.png'
    # Example 3 (Sample Bill)/images/1_2.png'
    # Example 6 (Sample Bill)/images/3_1.png'
    # Example 7 (Sample Bill)/images/1_1.png'

    # impath = r'C:/Users/benan/OneDrive/000_AKTIF_PROJELER/UTKU_HOCA/extraction/bos-doc-to-md-service/outputs/Example 7 (Sample Bill)/images/1_1.png'
    model = YOLO(
        "C:/Users/benan/OneDrive/000_AKTIF_PROJELER/UTKU_HOCA/extraction/train_model/runs/detect/train11/weights/best.pt"
    )
    results = model.predict(source=impath, save=False)
    print("model prediction done!")

    final_bars = []  # List to store (x, y, w, h) as Python ints

    for r in results:
        for box in r.boxes:
            # Convert tensor to regular Python ints
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            x = x1
            y = y1
            w = x2 - x1
            h = y2 - y1
            final_bars.append((x, y, w, h))

        # Draw bounding boxes and pixel heights on the original image
    for idx, (x, y, w, h) in enumerate(final_bars):
        # Draw rectangle

        # Put pixel height label above the bar
        label = f"{h}px"
        max_width = w - 4  # Small margin inside the bar
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1  # Thinner text for clarity

        # Adjust font scale to fit within the bar width
        (text_width, text_height), _ = cv2.getTextSize(
            label, font, font_scale, thickness
        )
        while text_width > max_width and font_scale > 0.1:
            font_scale -= 0.05
            (text_width, text_height), _ = cv2.getTextSize(
                label, font, font_scale, thickness
            )

        # Text position: centered above the bar
        label_x = x + (w - text_width) // 2
        label_y = y - 5 if y - 5 > text_height else y + text_height + 5

        # Draw white rectangle background for clarity
        # --- Draw green bounding box exactly on the bar ---
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # --- Prepare pixel height label ---
        label = f"{h}px"
        max_width = w - 4  # Margin inside the bar width
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.3
        thickness = 1  # Keep it thin but not too faint

        # Measure text size
        (text_width, text_height), _ = cv2.getTextSize(
            label, font, font_scale, thickness
        )
        while text_width > max_width and font_scale > 0.1:
            font_scale -= 0.05
            (text_width, text_height), _ = cv2.getTextSize(
                label, font, font_scale, thickness
            )

        # Position text above the bar
        label_x = x + (w - text_width) // 2
        label_y = y - 5 if y - 5 > text_height + 4 else y + text_height + 5

        # Background padding
        pad_x = 4
        pad_y = 3

        # Draw white background rectangle for text
        cv2.rectangle(
            img,
            (label_x - pad_x, label_y - text_height - pad_y),
            (label_x + text_width + pad_x, label_y + pad_y),
            (255, 255, 255),
            cv2.FILLED,
        )

        # Draw the text in black
        cv2.putText(
            img,
            label,
            (label_x, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,  # around 0.4–0.5
            (0, 0, 0),  # black
            1,  # thickness = 1 for thinner text
            cv2.LINE_AA,  # anti-aliasing for smooth look
        )

    crop_padding = 10
    imgname = "_".join(str(impath).split("\\")[-3:])
    # Get x-coordinates of the outermost bars
    if final_bars:
        leftmost_x = min(x for (x, _, _, _) in final_bars)
        rightmost_x_plus_w = max(x + w for (x, _, w, _) in final_bars)

        # Add padding while ensuring we stay within image bounds
        crop_x1 = max(leftmost_x - crop_padding, 0)
        crop_x2 = min(rightmost_x_plus_w + crop_padding, img.shape[1])

        # Crop the image horizontally only (preserve full height)
        cropped_img = img[:, crop_x1:crop_x2]

        # Show cropped image
        plt.figure(figsize=(12, 6))
        # plt.imshow(cv2.cvtColor(cropped_img, cv2.COLOR_BGR2RGB))
        plt.axis("off")
        plt.title("Cropped Image Based on Bar Boundaries with Padding")
        cv2.imwrite(
            f"./cropped_images/{imgname}_output_bars_cropped_with_padding.png",
            cropped_img,
        )

        # plt.show(block=False)

    else:
        cropped_img = img.copy()  # fallback
    # Now extract bar heights from final filtered bars
    bar_heights_px = {}

    # Sort final bars left to right (optional, for consistent order)
    final_bars.sort(key=lambda b: b[0])

    # Assign a sequential key like "Bar 1", "Bar 2", etc., or just use x position
    for idx, (x, y, w, h) in enumerate(final_bars):
        bar_heights_px[f"bar_{idx+1}"] = h
    print("bar_heights_px extracted", bar_heights_px)
    cv2.imwrite(f"./cropped_images/{imgname}_output_bars_cropped.png", cropped_img)

    return bar_heights_px


def crop_bar_chart_above_month_axis(file_path):
    """
    Crops the upper part of a bar chart image based on month labels detected via Azure OCR.

    If no valid month line is found (at least 2 months with the same Y bottom-right),
    returns the original image.

    Parameters:
        file_path (str): Path to the input image file.
        endpoint (str): Azure Computer Vision endpoint.
        key (str): Azure Computer Vision API key.

    Returns:
        PIL.Image: Cropped image (or original if no crop applied).
    """
    # --- Run OCR ---

    img_response = send_query(
        """Given an image and its OCR output (text and bounding boxes), determine if month names (e.g., "Jan", "February", "Mar") are being used as labels for the bars in a bar plot.

Return "True" if the months are directly labeling the bars (typically along the horizontal axis).

Return "False" if the months appear elsewhere (e.g., on the side) and are not directly labeling the bars.
Return "False" if the months names are just letters or numbers  (e.g., "J", "F", "1", "12/1")
Return only "True" or "False" — nothing else.
""",
        f"""Here is the image of bar plot""",
        file_path,
    )
    image = cv2.imread(str(file_path))
    if "true" in img_response[0].lower():

        with open(file_path, "rb") as image_stream:
            read_response = client_ocr.read_in_stream(image_stream, raw=True)
        operation_id = read_response.headers["Operation-Location"].split("/")[-1]

        while True:
            result = client_ocr.get_read_result(operation_id)
            if result.status not in ["notStarted", "running"]:
                break
            time.sleep(1)

        word_boxes = []
        if result.status == OperationStatusCodes.succeeded:
            for page in result.analyze_result.read_results:
                for line in page.lines:
                    for word in line.words:
                        word_boxes.append({"text": word.text, "box": word.bounding_box})

        # --- Find Month Labels and Group by Y bottom-right ---
        valid_months = {
            "jan",
            "feb",
            "mar",
            "apr",
            "may",
            "jun",
            "jul",
            "aug",
            "sep",
            "oct",
            "nov",
            "dec",
        }
        y_groups = defaultdict(list)

        for item in word_boxes:
            text = item["text"].strip().lower()
            if text[:3] in valid_months:
                y_bottom_right = round(item["box"][5])
                y_groups[y_bottom_right].append(item["box"])

        # --- Filter and Pick Best Y ---
        filtered_y_groups = {
            y: boxes for y, boxes in y_groups.items() if len(boxes) >= 2
        }
        # NumPy array (H x W x C)

        if not filtered_y_groups:
            return image  # Return original image if no valid month line

        # Get best y-coordinate from grouped lines
        best_y = max(filtered_y_groups.items(), key=lambda x: len(x[1]))[0]
        bottom_crop = best_y + 5

        # Crop image using NumPy slicing: [start_y:end_y, start_x:end_x]
        cropped_image = image[0:bottom_crop, 0 : image.shape[1]]

        # Show the cropped image using matplotlib (convert BGR to RGB)
        plt.figure(figsize=(12, 6))
        # plt.imshow(cv2.cvtColor(cropped_image, cv2.COLOR_BGR2RGB))
        plt.axis("off")
        plt.title("Cropped Image Based on Azure OCR")
        plt.show(block=False)
    else:
        cropped_image = image
    return cropped_image
