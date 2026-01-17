"""Zone detection using OpenCV for identifying page regions."""

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from hymn_ocr.models import PageType


@dataclass
class Zone:
    """A rectangular zone in an image."""

    y_start: int
    y_end: int
    x_start: int = 0
    x_end: Optional[int] = None

    def to_slice(self) -> tuple[slice, slice]:
        """Convert to numpy array slices."""
        x_end = self.x_end if self.x_end is not None else None
        return (slice(self.y_start, self.y_end), slice(self.x_start, x_end))


@dataclass
class PageZones:
    """All detected zones in a page."""

    header: Optional[Zone] = None
    metadata: Optional[Zone] = None
    body: Optional[Zone] = None
    footer: Optional[Zone] = None
    is_cover: bool = False


# OpenCV parameters
CANNY_THRESHOLD_LOW = 50
CANNY_THRESHOLD_HIGH = 150
HOUGH_THRESHOLD = 100
HOUGH_MIN_LINE_LENGTH = 200
HOUGH_MAX_LINE_GAP = 10
FOOTER_START_PERCENT = 0.80
HEADER_END_PERCENT = 0.15
METADATA_HEIGHT = 80  # pixels after header line


def pil_to_cv2(image: Image.Image) -> np.ndarray:
    """Convert PIL Image to OpenCV format (BGR)."""
    # Convert to RGB first (PIL might be RGBA or other)
    rgb = image.convert("RGB")
    # Convert to numpy array
    arr = np.array(rgb)
    # Convert RGB to BGR (OpenCV format)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def cv2_to_pil(image: np.ndarray) -> Image.Image:
    """Convert OpenCV image (BGR) to PIL Image."""
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def detect_horizontal_lines(
    gray: np.ndarray,
    min_length: int = HOUGH_MIN_LINE_LENGTH,
) -> list[int]:
    """
    Detect horizontal lines in a grayscale image.

    Args:
        gray: Grayscale image as numpy array.
        min_length: Minimum line length to detect.

    Returns:
        List of y-coordinates of detected horizontal lines, sorted.
    """
    # Apply edge detection
    edges = cv2.Canny(gray, CANNY_THRESHOLD_LOW, CANNY_THRESHOLD_HIGH, apertureSize=3)

    # Detect lines with Hough Transform
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=HOUGH_THRESHOLD,
        minLineLength=min_length,
        maxLineGap=HOUGH_MAX_LINE_GAP,
    )

    if lines is None:
        return []

    horizontal_ys = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        # Is it horizontal? (difference in y < 5 pixels)
        if abs(y1 - y2) < 5:
            horizontal_ys.append((y1 + y2) // 2)

    # Remove duplicates (lines close together)
    if not horizontal_ys:
        return []

    horizontal_ys.sort()
    unique_ys = [horizontal_ys[0]]
    for y in horizontal_ys[1:]:
        if y - unique_ys[-1] > 20:  # Minimum 20px apart
            unique_ys.append(y)

    return unique_ys


def is_cover_page(image: np.ndarray) -> bool:
    """
    Detect if an image is a cover page.

    Cover pages typically have:
    - More visual complexity (background images)
    - Higher color variance
    - Less white space

    Args:
        image: BGR image as numpy array.

    Returns:
        True if the image appears to be a cover page.
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Calculate histogram
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])

    # Normalize
    hist = hist.flatten() / hist.sum()

    # Cover pages have less white (high values) and more mid-tones
    # Regular pages are mostly white (values > 240)
    white_ratio = hist[240:].sum()

    # Cover pages typically have < 50% white pixels
    # Regular hymn pages have > 80% white pixels
    return white_ratio < 0.5


def detect_zones(image: np.ndarray) -> PageZones:
    """
    Detect zones in a hymn page image.

    Zones:
    - header: Title and number (above first horizontal line)
    - metadata: Offered to, style (below header line)
    - body: Lyrics
    - footer: Symbol and date (bottom 20%)

    Args:
        image: BGR image as numpy array.

    Returns:
        PageZones with detected regions.
    """
    height, width = image.shape[:2]

    # Check if it's a cover page
    if is_cover_page(image):
        return PageZones(is_cover=True)

    # Convert to grayscale for line detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Detect horizontal lines
    horizontal_lines = detect_horizontal_lines(gray)

    zones = PageZones()

    # Find the header separator line (should be in top 15% of page)
    header_max_y = int(height * HEADER_END_PERCENT)
    header_line_y = None

    for y in horizontal_lines:
        if y < header_max_y:
            header_line_y = y
            break

    if header_line_y is not None:
        # Header zone: from top to the line
        zones.header = Zone(y_start=0, y_end=header_line_y)

        # Metadata zone: just below the line
        metadata_end = min(header_line_y + METADATA_HEIGHT, int(height * 0.25))
        zones.metadata = Zone(y_start=header_line_y, y_end=metadata_end)

        # Body zone: from metadata to footer
        footer_start = int(height * FOOTER_START_PERCENT)
        zones.body = Zone(y_start=metadata_end, y_end=footer_start)

        # Footer zone: bottom 20%
        zones.footer = Zone(y_start=footer_start, y_end=height)
    else:
        # No header line found - this might be a continuation page
        # or the line detection failed

        # Check if there's text at the top that looks like a header
        # For continuation pages, just use body zone
        footer_start = int(height * FOOTER_START_PERCENT)
        zones.body = Zone(y_start=0, y_end=footer_start)
        zones.footer = Zone(y_start=footer_start, y_end=height)

    return zones


def extract_zone(image: np.ndarray, zone: Zone) -> np.ndarray:
    """
    Extract a zone from an image.

    Args:
        image: Full image as numpy array.
        zone: Zone to extract.

    Returns:
        Cropped image of the zone.
    """
    y_slice, x_slice = zone.to_slice()
    return image[y_slice, x_slice]


def classify_page(image: np.ndarray, ocr_text: Optional[str] = None) -> PageType:
    """
    Classify a page type based on image analysis and optional OCR text.

    Args:
        image: BGR image as numpy array.
        ocr_text: Optional OCR text from the page.

    Returns:
        PageType enum value.
    """
    import re

    # Check if it's a cover page
    if is_cover_page(image):
        return PageType.COVER

    # If we have OCR text, use it for classification
    if ocr_text:
        # Look for header pattern at the start
        header_match = re.match(r"^\s*(\d+)\.\s+", ocr_text)
        if header_match:
            return PageType.NEW_HYMN

        # Look for date/symbol at the end (indicates end of hymn)
        has_ending = re.search(r"\(\d{2}/\d{2}/\d{4}\)", ocr_text)
        if not has_ending and len(ocr_text.strip()) > 50:
            return PageType.CONTINUATION

    # Image-based classification
    zones = detect_zones(image)

    # If no header zone was detected, likely a continuation
    if zones.header is None and zones.body is not None:
        return PageType.CONTINUATION

    # If header zone exists, it's a new hymn
    if zones.header is not None:
        return PageType.NEW_HYMN

    return PageType.BLANK


def visualize_zones(image: np.ndarray, zones: PageZones) -> np.ndarray:
    """
    Draw zone boundaries on an image for debugging.

    Args:
        image: BGR image as numpy array.
        zones: Detected zones.

    Returns:
        Image with zone boundaries drawn.
    """
    debug_image = image.copy()
    height, width = debug_image.shape[:2]

    colors = {
        "header": (0, 255, 0),  # Green
        "metadata": (255, 165, 0),  # Orange
        "body": (255, 0, 0),  # Blue
        "footer": (0, 0, 255),  # Red
    }

    for name, zone in [
        ("header", zones.header),
        ("metadata", zones.metadata),
        ("body", zones.body),
        ("footer", zones.footer),
    ]:
        if zone:
            x_end = zone.x_end if zone.x_end else width
            cv2.rectangle(
                debug_image,
                (zone.x_start, zone.y_start),
                (x_end, zone.y_end),
                colors[name],
                2,
            )
            cv2.putText(
                debug_image,
                name,
                (zone.x_start + 10, zone.y_start + 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                colors[name],
                2,
            )

    return debug_image
