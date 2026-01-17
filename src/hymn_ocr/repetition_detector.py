"""Detection of repetition bars (vertical lines) in hymn images."""

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from hymn_ocr.zone_detector import Zone, extract_zone


# Detection parameters
CANNY_THRESHOLD_LOW = 50
CANNY_THRESHOLD_HIGH = 150
HOUGH_THRESHOLD = 50
HOUGH_MIN_LINE_LENGTH = 30
HOUGH_MAX_LINE_GAP = 10
LEFT_MARGIN_PERCENT = 0.15
VERTICAL_TOLERANCE = 10  # Max horizontal deviation for a line to be considered vertical


@dataclass
class VerticalSegment:
    """A vertical line segment."""

    x: int
    y_start: int
    y_end: int


@dataclass
class RepetitionBar:
    """A detected repetition bar with line mappings."""

    y_start: int
    y_end: int
    start_line: Optional[int] = None
    end_line: Optional[int] = None


def detect_vertical_lines(
    image: np.ndarray,
    left_margin_percent: float = LEFT_MARGIN_PERCENT,
) -> list[VerticalSegment]:
    """
    Detect vertical lines in the left margin of an image.

    Args:
        image: BGR image as numpy array.
        left_margin_percent: Percentage of image width to consider as left margin.

    Returns:
        List of VerticalSegment objects.
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape

    # Apply edge detection
    edges = cv2.Canny(gray, CANNY_THRESHOLD_LOW, CANNY_THRESHOLD_HIGH, apertureSize=3)

    # Detect lines with Hough Transform
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=HOUGH_THRESHOLD,
        minLineLength=HOUGH_MIN_LINE_LENGTH,
        maxLineGap=HOUGH_MAX_LINE_GAP,
    )

    if lines is None:
        return []

    # Filter for vertical lines in left margin
    left_margin = width * left_margin_percent
    vertical_segments = []

    for line in lines:
        x1, y1, x2, y2 = line[0]

        # Is it vertical? (horizontal deviation < tolerance)
        if abs(x1 - x2) < VERTICAL_TOLERANCE:
            # Is it in the left margin?
            avg_x = (x1 + x2) // 2
            if avg_x < left_margin:
                y_min, y_max = min(y1, y2), max(y1, y2)
                vertical_segments.append(
                    VerticalSegment(x=avg_x, y_start=y_min, y_end=y_max)
                )

    return vertical_segments


def merge_overlapping_segments(segments: list[VerticalSegment]) -> list[VerticalSegment]:
    """
    Merge overlapping or adjacent vertical segments.

    Segments that are close together vertically and at similar x positions
    are merged into a single segment.

    Args:
        segments: List of vertical segments.

    Returns:
        List of merged segments.
    """
    if not segments:
        return []

    # Sort by y_start
    segments = sorted(segments, key=lambda s: s.y_start)

    merged = []
    current = segments[0]

    for segment in segments[1:]:
        # Check if segments are close enough to merge
        # Same x position (within tolerance) and overlapping/adjacent y ranges
        x_close = abs(segment.x - current.x) < 20
        y_overlaps = segment.y_start <= current.y_end + 20

        if x_close and y_overlaps:
            # Merge: extend current segment
            current = VerticalSegment(
                x=(current.x + segment.x) // 2,
                y_start=min(current.y_start, segment.y_start),
                y_end=max(current.y_end, segment.y_end),
            )
        else:
            # No merge: save current and start new
            merged.append(current)
            current = segment

    merged.append(current)
    return merged


def find_line_at_y(
    text_lines: list[tuple[int, int, str]],
    y_coord: int,
    tolerance: int = 20,
) -> Optional[int]:
    """
    Find which text line number corresponds to a y coordinate.

    Args:
        text_lines: List of (y_start, y_end, text) tuples from OCR.
        y_coord: Y coordinate to look up.
        tolerance: Tolerance for matching.

    Returns:
        1-indexed line number, or None if not found.
    """
    for i, (y_start, y_end, _) in enumerate(text_lines, start=1):
        # Check if y_coord is within or near this line
        if y_start - tolerance <= y_coord <= y_end + tolerance:
            return i
        # Check if y_coord is between previous and this line
        if y_coord < y_start:
            return i

    # If y_coord is below all lines, return last line
    if text_lines:
        return len(text_lines)

    return None


def detect_repetition_bars(
    image: np.ndarray,
    text_lines: Optional[list[tuple[int, int, str]]] = None,
    zone: Optional[Zone] = None,
) -> Optional[str]:
    """
    Detect repetition bars in an image and map them to line numbers.

    Args:
        image: BGR image as numpy array.
        text_lines: Optional list of (y_start, y_end, text) tuples for mapping.
        zone: Optional zone to analyze. If provided, uses only this zone.

    Returns:
        String in format "1-4, 5-8" or None if no bars detected.
    """
    # Extract zone if provided
    if zone is not None:
        image = extract_zone(image, zone)

    # Detect vertical lines
    segments = detect_vertical_lines(image)

    if not segments:
        return None

    # Merge overlapping segments
    merged = merge_overlapping_segments(segments)

    if not merged:
        return None

    # Map to line numbers if text_lines provided
    repetitions = []
    for segment in merged:
        if text_lines:
            start_line = find_line_at_y(text_lines, segment.y_start)
            end_line = find_line_at_y(text_lines, segment.y_end)

            if start_line and end_line:
                repetitions.append(f"{start_line}-{end_line}")
            else:
                # Fallback: use y coordinates
                repetitions.append(f"y{segment.y_start}-{segment.y_end}")
        else:
            # No text lines: use y coordinates as placeholder
            repetitions.append(f"y{segment.y_start}-{segment.y_end}")

    return ", ".join(repetitions) if repetitions else None


def visualize_repetition_bars(
    image: np.ndarray,
    segments: list[VerticalSegment],
) -> np.ndarray:
    """
    Draw detected repetition bars on an image for debugging.

    Args:
        image: BGR image as numpy array.
        segments: List of detected vertical segments.

    Returns:
        Image with bars highlighted.
    """
    debug_image = image.copy()

    for segment in segments:
        cv2.line(
            debug_image,
            (segment.x, segment.y_start),
            (segment.x, segment.y_end),
            (0, 255, 0),  # Green
            3,
        )
        # Add markers at start and end
        cv2.circle(debug_image, (segment.x, segment.y_start), 5, (0, 0, 255), -1)
        cv2.circle(debug_image, (segment.x, segment.y_end), 5, (0, 0, 255), -1)

    return debug_image


def adjust_repetition_numbers(
    prev_repetitions: Optional[str],
    new_repetitions: Optional[str],
    combined_text: str,
) -> Optional[str]:
    """
    Adjust repetition line numbers when merging multi-page hymns.

    When a hymn spans multiple pages, the repetition bar line numbers
    from the second page need to be offset by the number of lines
    from the first page.

    Args:
        prev_repetitions: Repetitions from previous page(s).
        new_repetitions: Repetitions from the new page.
        combined_text: Combined text from all pages.

    Returns:
        Combined repetitions string with adjusted line numbers.
    """
    if not new_repetitions:
        return prev_repetitions

    if not prev_repetitions:
        return new_repetitions

    # Count lines in previous text to determine offset
    # This is approximate - we count double newlines as stanza breaks
    prev_lines_count = combined_text.count("\n") + 1

    # Parse new repetitions and offset them
    import re

    adjusted_parts = []

    for part in new_repetitions.split(","):
        part = part.strip()
        match = re.match(r"(\d+)-(\d+)", part)
        if match:
            start = int(match.group(1)) + prev_lines_count
            end = int(match.group(2)) + prev_lines_count
            adjusted_parts.append(f"{start}-{end}")
        else:
            # Keep as-is if can't parse
            adjusted_parts.append(part)

    # Combine with previous
    return f"{prev_repetitions}, {', '.join(adjusted_parts)}"
