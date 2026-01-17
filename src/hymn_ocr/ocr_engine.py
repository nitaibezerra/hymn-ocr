"""OCR engine using Tesseract for text extraction."""

from typing import Optional

import cv2
import numpy as np
import pytesseract
from PIL import Image

from hymn_ocr.zone_detector import Zone, extract_zone, pil_to_cv2


# Tesseract configuration
# PSM 6 = Assume a single uniform block of text
# OEM 3 = Default, based on what is available
TESSERACT_CONFIG = "--psm 6 --oem 3"
TESSERACT_LANG = "por"  # Portuguese


def preprocess_for_ocr(image: np.ndarray) -> np.ndarray:
    """
    Preprocess image for better OCR results.

    Args:
        image: BGR image as numpy array.

    Returns:
        Preprocessed grayscale image.
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply slight Gaussian blur to reduce noise
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # Apply adaptive thresholding for better text contrast
    # This helps with varying lighting conditions
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2,
    )

    return binary


def ocr_image(
    image: np.ndarray,
    lang: str = TESSERACT_LANG,
    config: str = TESSERACT_CONFIG,
    preprocess: bool = True,
) -> str:
    """
    Perform OCR on an image.

    Args:
        image: BGR image as numpy array.
        lang: Tesseract language code.
        config: Tesseract configuration string.
        preprocess: Whether to preprocess the image.

    Returns:
        Extracted text as string.
    """
    if preprocess:
        processed = preprocess_for_ocr(image)
    else:
        processed = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Convert to PIL for pytesseract
    pil_image = Image.fromarray(processed)

    text = pytesseract.image_to_string(pil_image, lang=lang, config=config)

    return text.strip()


def ocr_zone(
    image: np.ndarray,
    zone: Optional[Zone],
    lang: str = TESSERACT_LANG,
    config: str = TESSERACT_CONFIG,
) -> str:
    """
    Perform OCR on a specific zone of an image.

    Args:
        image: Full BGR image as numpy array.
        zone: Zone to OCR. If None, returns empty string.
        lang: Tesseract language code.
        config: Tesseract configuration string.

    Returns:
        Extracted text from the zone.
    """
    if zone is None:
        return ""

    zone_image = extract_zone(image, zone)

    # Skip if zone is too small
    if zone_image.shape[0] < 10 or zone_image.shape[1] < 10:
        return ""

    return ocr_image(zone_image, lang=lang, config=config)


def ocr_pil_image(
    image: Image.Image,
    lang: str = TESSERACT_LANG,
    config: str = TESSERACT_CONFIG,
) -> str:
    """
    Perform OCR on a PIL Image.

    Args:
        image: PIL Image.
        lang: Tesseract language code.
        config: Tesseract configuration string.

    Returns:
        Extracted text as string.
    """
    cv2_image = pil_to_cv2(image)
    return ocr_image(cv2_image, lang=lang, config=config)


def get_text_line_positions(
    image: np.ndarray,
    zone: Optional[Zone] = None,
) -> list[tuple[int, int, str]]:
    """
    Get positions of text lines in an image.

    Uses Tesseract's detailed output to get line positions.

    Args:
        image: BGR image as numpy array.
        zone: Optional zone to analyze. If None, uses full image.

    Returns:
        List of (y_start, y_end, text) tuples for each line.
    """
    if zone is not None:
        image = extract_zone(image, zone)

    # Preprocess
    processed = preprocess_for_ocr(image)
    pil_image = Image.fromarray(processed)

    # Get detailed data from Tesseract
    data = pytesseract.image_to_data(
        pil_image,
        lang=TESSERACT_LANG,
        config=TESSERACT_CONFIG,
        output_type=pytesseract.Output.DICT,
    )

    # Group words by line number
    lines = {}
    for i in range(len(data["text"])):
        if data["text"][i].strip():
            line_num = data["line_num"][i]
            block_num = data["block_num"][i]
            key = (block_num, line_num)

            if key not in lines:
                lines[key] = {
                    "y_start": data["top"][i],
                    "y_end": data["top"][i] + data["height"][i],
                    "words": [],
                }

            lines[key]["words"].append(data["text"][i])
            # Update y bounds
            y_top = data["top"][i]
            y_bottom = data["top"][i] + data["height"][i]
            lines[key]["y_start"] = min(lines[key]["y_start"], y_top)
            lines[key]["y_end"] = max(lines[key]["y_end"], y_bottom)

    # Sort by y position and format output
    result = []
    for key in sorted(lines.keys(), key=lambda k: lines[k]["y_start"]):
        line_data = lines[key]
        text = " ".join(line_data["words"])
        result.append((line_data["y_start"], line_data["y_end"], text))

    return result


def clean_ocr_text(text: str) -> str:
    """
    Clean OCR output text.

    - Remove extra whitespace
    - Fix common OCR errors for Portuguese text
    - Normalize line endings

    Args:
        text: Raw OCR text.

    Returns:
        Cleaned text.
    """
    if not text:
        return ""

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove multiple consecutive blank lines
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")

    # Remove leading/trailing whitespace on each line
    lines = [line.strip() for line in text.split("\n")]

    # Remove empty lines at start and end
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()

    return "\n".join(lines)
