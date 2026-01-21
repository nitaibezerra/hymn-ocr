"""Detection of repetition bars using vertical projection profile.

This module implements a simpler and more reliable approach to detect
repetition bars in hymn images, based on reverse engineering of the
hymn_pdf_generator rendering logic.

Key insight: Bars are always in the left margin (first ~15% of width),
so we can use a vertical projection profile to detect them instead of
Hough Transform which detects all lines indiscriminately.

v2.1: Added multi-column analysis for nested bar detection (e.g., "1-2, 3-4, 1-4")
"""

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
import pytesseract
from scipy.ndimage import label

from hymn_ocr.zone_detector import Zone, extract_zone


# Detection parameters
BAR_REGION_PERCENT = 0.15  # Analyze leftmost 15% of page (includes margin + bar area)
DETECTION_THRESHOLD = 0.15  # Minimum intensity relative to max
MIN_SEGMENT_HEIGHT_PERCENT = 0.05  # Filter out segments shorter than 5% of height
BINARY_THRESHOLD = 240  # Threshold for binary conversion
NUM_COLUMNS = 3  # Number of columns to divide the bar region into
GAP_DETECTION_THRESHOLD = 0.5  # Relative threshold for detecting gaps within segments
MIN_GAP_HEIGHT_PERCENT = 0.015  # Minimum gap height (1.5% of body height)


@dataclass
class BarSegment:
    """A detected vertical bar segment."""

    y_start: int
    y_end: int
    intensity: float  # Average intensity (for debugging)
    column: int = 0  # Which column this segment was found in (0=leftmost/external)
    is_internal: bool = True  # Whether this is an internal bar (from gap splitting)


def detect_gaps_in_segment(
    profile: np.ndarray,
    segment: BarSegment,
    gap_threshold: float = GAP_DETECTION_THRESHOLD,
    min_gap_height: int = 10,
) -> list[BarSegment]:
    """
    Detect gaps within a segment that indicate nested bars.

    For nested bars like "1-2, 3-4, 1-4":
    - The external bar (1-4) is continuous
    - The internal bars (1-2, 3-4) have a gap between them

    The profile shows higher intensity where BOTH bars overlap,
    and lower intensity where only the external bar exists.

    Args:
        profile: Vertical projection profile.
        segment: The segment to analyze.
        gap_threshold: Relative threshold for gap detection (0-1).
        min_gap_height: Minimum gap height in pixels.

    Returns:
        List of BarSegment objects (split if gaps found, or original if not).
    """
    # Extract the profile portion for this segment
    seg_profile = profile[segment.y_start:segment.y_end]

    if len(seg_profile) < min_gap_height * 3:
        # Segment too short to have meaningful gaps
        return [segment]

    # Find the max and min within the segment
    max_val = np.max(seg_profile)
    if max_val == 0:
        return [segment]

    # Normalize the segment profile
    normalized = seg_profile / max_val

    # Look for valleys (dips below threshold relative to max)
    is_valley = normalized < gap_threshold

    # Find continuous valley regions
    diff = np.diff(is_valley.astype(int), prepend=0, append=0)
    valley_starts = np.where(diff == 1)[0]
    valley_ends = np.where(diff == -1)[0]

    # Filter valleys by minimum height
    valid_valleys = []
    for v_start, v_end in zip(valley_starts, valley_ends):
        valley_height = v_end - v_start
        if valley_height >= min_gap_height:
            valid_valleys.append((v_start, v_end))

    if not valid_valleys:
        # No significant gaps found
        return [segment]

    # Split the segment at the valleys
    # This creates internal bar segments
    result = []
    prev_end = 0

    for valley_start, valley_end in valid_valleys:
        # Add the segment before this valley (if substantial)
        if valley_start - prev_end >= min_gap_height:
            result.append(BarSegment(
                y_start=segment.y_start + prev_end,
                y_end=segment.y_start + valley_start,
                intensity=np.mean(normalized[prev_end:valley_start]),
                column=segment.column,
                is_internal=True,
            ))
        prev_end = valley_end

    # Add the final segment after the last valley
    if len(seg_profile) - prev_end >= min_gap_height:
        result.append(BarSegment(
            y_start=segment.y_start + prev_end,
            y_end=segment.y_end,
            intensity=np.mean(normalized[prev_end:]),
            column=segment.column,
            is_internal=True,
        ))

    # Filter out very small internal segments
    # Internal bars should cover at least ~2 lines (15% of segment height)
    min_internal_height = max(20, int(len(seg_profile) * 0.15))
    result = [s for s in result if (s.y_end - s.y_start) >= min_internal_height]

    # If we found at least 2 meaningful internal bars, also keep the original as external
    if len(result) >= 2:
        external = BarSegment(
            y_start=segment.y_start,
            y_end=segment.y_end,
            intensity=segment.intensity,
            column=segment.column - 1,  # External bar is "more left"
            is_internal=False,
        )
        result.append(external)
        return result

    # If gap detection didn't produce meaningful splits, return original
    return [segment]


def analyze_bar_columns(
    bar_region: np.ndarray,
    num_columns: int = NUM_COLUMNS,
) -> list[tuple[np.ndarray, int, int]]:
    """
    Divide the bar region into columns and compute profile for each.

    This allows detecting nested bars where:
    - Internal bars (level 1, closer to text) are in rightmost columns
    - External bars (level 2+, further from text) are in leftmost columns

    Args:
        bar_region: BGR image of the left margin region.
        num_columns: Number of columns to divide into.

    Returns:
        List of (profile, col_start, col_end) tuples, from left to right.
    """
    if bar_region is None or bar_region.size == 0:
        return []

    h, w = bar_region.shape[:2]
    column_width = w // num_columns

    results = []
    for i in range(num_columns):
        col_start = i * column_width
        col_end = (i + 1) * column_width if i < num_columns - 1 else w

        column = bar_region[:, col_start:col_end]
        profile = compute_vertical_profile(column)

        if profile is not None:
            results.append((profile, col_start, col_end))

    return results


def detect_repetition_bars_v2(
    image: np.ndarray,
    body_zone: Zone,
    body_text: str,
    margin_percent: float = BAR_REGION_PERCENT,
    threshold: float = DETECTION_THRESHOLD,
) -> Optional[str]:
    """
    Detect repetition bars using vertical projection profile.

    This approach:
    1. Extracts the left margin of the FULL PAGE (where bars are in the margin)
    2. Analyzes only the Y range corresponding to the body zone
    3. Computes a vertical projection profile (sum of dark pixels per row)
    4. Finds contiguous segments where the profile exceeds a threshold
    5. Maps Y coordinates to line numbers using proportional mapping

    Args:
        image: BGR image of the full page.
        body_zone: Zone containing the hymn body text.
        body_text: OCR text from the body (used for line counting).
        margin_percent: Percentage of PAGE width to analyze for bars.
        threshold: Minimum intensity relative to max to detect bar.

    Returns:
        String in format "1-4, 5-8" or None if no bars detected.
    """
    if body_zone is None or not body_text:
        return None

    page_h, page_w = image.shape[:2]

    # 1. Extract left margin of FULL PAGE (bars are in page margin, not body margin)
    bar_width = max(10, int(page_w * margin_percent))
    page_left_margin = image[:, :bar_width]

    # 2. Crop to body zone Y range (bars only appear next to body text)
    body_y_start = body_zone.y_start
    body_y_end = body_zone.y_end
    body_height = body_y_end - body_y_start

    if body_height < 10:
        return None

    bar_region = page_left_margin[body_y_start:body_y_end, :]

    # 2.5. Extract body image and get Tesseract line boundaries for precise mapping
    body_image = image[body_y_start:body_y_end, :]
    line_boundaries = get_line_boundaries_tesseract(body_image)

    # 3. Compute vertical profile for the entire bar region
    profile = compute_vertical_profile(bar_region)

    if profile is None or len(profile) == 0:
        return None

    # 4. Find initial bar segments
    initial_segments = find_bar_segments(profile, threshold, body_height)

    if not initial_segments:
        return None

    # 4.5. NEW: Try per-line horizontal analysis for asymmetric patterns
    # This approach counts how many vertical bars exist at each line's Y position
    # Enables detection of patterns like "3-4, 1-4" where lines 3-4 have 2 bars
    # ONLY use when:
    # - Single segment detected (potential asymmetric pattern hidden in one segment)
    # - Segment covers enough lines (at least 3) to potentially have internal bars
    # - Clear variation in bar counts within the segment
    if len(line_boundaries) >= 3 and len(initial_segments) == 1:
        segment = initial_segments[0]
        segment_height = segment.y_end - segment.y_start

        # Only apply if segment is large enough to contain multiple bar levels
        # (e.g., 4 lines = ~25% of body for 16-line hymns, or ~50% for 8-line hymns)
        segment_percent = segment_height / body_height
        if segment_percent >= 0.15:
            # Filter line_boundaries to only include lines within/near the segment
            # This prevents noise detection on lines far from the actual bars
            segment_line_boundaries = []
            for i, (y_min, y_max) in enumerate(line_boundaries):
                line_center = (y_min + y_max) / 2
                # Line overlaps with segment if center is within segment bounds (with margin)
                margin = (y_max - y_min) / 2  # Half line height as margin
                if segment.y_start - margin <= line_center <= segment.y_end + margin:
                    segment_line_boundaries.append((y_min, y_max))

            # Need at least 3 lines within segment for asymmetric detection
            if len(segment_line_boundaries) >= 3:
                bar_counts = count_bars_per_line(bar_region, segment_line_boundaries)
                max_bars = max(bar_counts) if bar_counts else 0
                min_bars = min(bar_counts) if bar_counts else 0

                # Only use if there's CLEAR variation: some lines with 2+ bars, some with 1
                if max_bars >= 2 and min_bars >= 1 and min_bars < max_bars:
                    # Find lines with max bars (internal) vs any bars (external)
                    internal_lines = [i + 1 for i, c in enumerate(bar_counts) if c == max_bars]
                    external_lines = [i + 1 for i, c in enumerate(bar_counts) if c >= 1]

                    # Validate the pattern makes sense:
                    # 1. Internal lines should be contiguous
                    # 2. Internal should be a proper subset of external
                    if (internal_lines and external_lines and
                        internal_lines != external_lines and
                        max(internal_lines) - min(internal_lines) + 1 == len(internal_lines)):
                        result = deduce_repetitions_from_bar_counts(bar_counts)
                        if result:
                            return result

    # 5. Apply gap detection ONLY for potential nested bars
    # Conditions for gap detection:
    # - Only ONE initial segment was found
    # - The segment spans a significant portion (> 15% of body height)
    # This avoids false positives from normal profile variations
    min_gap_height = max(10, int(body_height * MIN_GAP_HEIGHT_PERCENT))
    all_segments = []

    if len(initial_segments) == 1:
        segment = initial_segments[0]
        segment_height = segment.y_end - segment.y_start
        segment_percent = segment_height / body_height

        # Only apply gap detection for large single segments
        if segment_percent > 0.15:
            split_segments = detect_gaps_in_segment(
                profile, segment, GAP_DETECTION_THRESHOLD, min_gap_height
            )
            # Only use split if we got meaningful results (2+ internal bars)
            internal_bars = [s for s in split_segments if s.is_internal]

            # Additional check: each internal bar should cover at least 2 lines
            # Use proportional mapping to estimate line coverage
            if len(internal_bars) >= 2:
                all_valid = True
                for bar in internal_bars:
                    bar_height = bar.y_end - bar.y_start
                    # Estimate how many lines this bar covers
                    # Use the segment height as reference (segment covers known lines)
                    lines_covered = (bar_height / segment_height) * 4  # Assume segment ~ 4 lines
                    if lines_covered < 1.5:  # Less than ~2 lines
                        all_valid = False
                        break

                if all_valid and len(internal_bars) == 2:
                    # Also check that the two internal bars are roughly equal
                    heights = [b.y_end - b.y_start for b in internal_bars]
                    ratio = min(heights) / max(heights) if max(heights) > 0 else 0
                    if ratio < 0.5:  # One bar is less than half the other
                        all_valid = False

                if all_valid:
                    all_segments = split_segments
                else:
                    all_segments = [segment]
            else:
                all_segments = [segment]
        else:
            all_segments = [segment]
    else:
        # Multiple segments - no gap detection needed
        all_segments = initial_segments

    if not all_segments:
        return None

    # Use all segments for further processing
    segments = all_segments

    # 5. Count text lines (excluding blank lines and artifacts)
    text_lines = []
    for line in body_text.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Remove leading "|" that OCR sometimes captures from repetition bars
        while line.startswith('|'):
            line = line[1:].strip()

        if not line:
            continue

        # Filter out common OCR artifacts
        line_upper = line.upper().replace(' ', '')
        # Short uppercase-only lines (likely artifacts like "XX", "WC", "CX")
        # Also catches mixed case like "WC x" by checking normalized length
        if len(line_upper) <= 4:
            # Check if it's all letters (likely artifact, not real hymn text)
            if line_upper.isalpha():
                continue
            # Check for known artifact patterns
            if line_upper in ['XX', 'X', 'WC', 'WCX', 'CC', 'CLX', 'CX', 'SDS', 'PO']:
                continue
        # Dates like (18/01/2020)
        if line.startswith('(') and '/' in line and line.endswith(')'):
            continue

        text_lines.append(line)

    num_lines = len(text_lines)


    if num_lines == 0:
        return None

    # 6. Group segments by column and analyze patterns
    # Column 0 = external (left), Column NUM_COLUMNS-1 = internal (right, near text)
    segments_by_column: dict[int, list[BarSegment]] = {}
    for seg in segments:
        if seg.column not in segments_by_column:
            segments_by_column[seg.column] = []
        segments_by_column[seg.column].append(seg)

    # Find the rightmost column with segments (internal bars)
    # This helps estimate line height from the most granular bars
    rightmost_col = max(segments_by_column.keys()) if segments_by_column else 0
    internal_segments = segments_by_column.get(rightmost_col, [])

    # Calculate bar span from ALL segments
    all_y_starts = [seg.y_start for seg in segments]
    all_y_ends = [seg.y_end for seg in segments]
    first_bar_start = min(all_y_starts)
    last_bar_end = max(all_y_ends)
    total_bar_span = last_bar_end - first_bar_start

    # Estimate line height based on internal segments (most granular)
    # If internal column has multiple segments, they likely cover 2 lines each
    # If only 1 segment in internal column, check if there are external bars
    if len(internal_segments) >= 2:
        # Multiple internal segments = likely "1-2, 3-4" pattern (2 lines each)
        estimated_lines_with_bars = len(internal_segments) * 2
    elif len(internal_segments) == 1:
        # Single internal segment - check if there are other columns with segments
        other_columns = [c for c in segments_by_column.keys() if c != rightmost_col]
        if other_columns:
            # There are external bars, so internal might be partial (2 lines)
            # But the total span should guide us
            estimated_lines_with_bars = 4
        else:
            # Only one segment total, assume 4 lines
            estimated_lines_with_bars = 4
    else:
        estimated_lines_with_bars = 4

    if estimated_lines_with_bars > 0 and total_bar_span > 0:
        estimated_line_height = total_bar_span / estimated_lines_with_bars
    else:
        estimated_text_height_from_body = body_height * 0.45
        estimated_line_height = estimated_text_height_from_body / num_lines

    # 7. Map segments to line numbers
    # Sort: internal bars first (is_internal=True), then by y_start
    # This ensures "1-2, 3-4, 1-4" order (internal bars first, external last)
    sorted_segments = sorted(segments, key=lambda s: (not s.is_internal, s.y_start))

    # Use Tesseract-based mapping if we have valid line boundaries,
    # otherwise fallback to estimated line height
    use_tesseract = len(line_boundaries) >= 2  # Need at least 2 lines for meaningful mapping
    tesseract_num_lines = len(line_boundaries) if use_tesseract else num_lines

    repetitions = []
    for segment in sorted_segments:
        if use_tesseract:
            # Use precise Tesseract positions
            start_line = map_y_to_line_tesseract(
                segment.y_start, line_boundaries, is_end=False
            )
            end_line = map_y_to_line_tesseract(
                segment.y_end, line_boundaries, is_end=True
            )
            effective_num_lines = tesseract_num_lines
        else:
            # Fallback to estimated line height
            start_line = map_y_to_line_v3(
                segment.y_start, first_bar_start, estimated_line_height, num_lines, is_end=False
            )
            end_line = map_y_to_line_v3(
                segment.y_end, first_bar_start, estimated_line_height, num_lines, is_end=True
            )
            effective_num_lines = num_lines

        if start_line <= end_line and start_line >= 1 and end_line <= effective_num_lines:
            rep = f"{start_line}-{end_line}"
            repetitions.append(rep)

    # Remove duplicates while preserving order (internal bars first)
    seen = set()
    unique_reps = []
    for rep in repetitions:
        if rep not in seen:
            seen.add(rep)
            unique_reps.append(rep)

    return ", ".join(unique_reps) if unique_reps else None


def compute_vertical_profile(bar_region: np.ndarray) -> Optional[np.ndarray]:
    """
    Compute vertical projection profile of a region.

    For each row (Y coordinate), detect the presence of vertical edges.
    Uses Sobel edge detection followed by morphological operations.

    Args:
        bar_region: BGR image of the left margin region.

    Returns:
        1D numpy array with edge intensity for each row, or None on error.
    """
    if bar_region is None or bar_region.size == 0:
        return None

    # Convert to grayscale
    if len(bar_region.shape) == 3:
        gray = cv2.cvtColor(bar_region, cv2.COLOR_BGR2GRAY)
    else:
        gray = bar_region.copy()

    # Apply Gaussian blur to reduce noise
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # Detect vertical edges using Sobel (dx=1, dy=0)
    # This highlights vertical lines (like repetition bars)
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    edges = np.abs(sobel_x).astype(np.uint8)

    # Apply threshold to get binary edge map
    _, edges_binary = cv2.threshold(edges, 20, 255, cv2.THRESH_BINARY)

    # Morphological closing to connect broken edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5))
    edges_closed = cv2.morphologyEx(edges_binary, cv2.MORPH_CLOSE, kernel)

    # Sum horizontally - each row gets an "edge presence score"
    profile = np.sum(edges_closed, axis=1).astype(float)

    return profile


def compute_horizontal_profile(slice_region: np.ndarray) -> np.ndarray:
    """
    Compute horizontal profile (sum along Y axis) of a horizontal slice.

    Vertical bars appear as valleys (dark regions) in the horizontal profile.
    We use inverted binary threshold to detect dark bar regions.

    Args:
        slice_region: BGR image of a horizontal slice from the bar region.

    Returns:
        1D numpy array with "bar presence" for each column (X position).
        Higher values indicate darker (bar) regions.
        Empty array if input is invalid.
    """
    if slice_region is None or slice_region.size == 0:
        return np.array([])

    # Convert to grayscale
    if len(slice_region.shape) == 3:
        gray = cv2.cvtColor(slice_region, cv2.COLOR_BGR2GRAY)
    else:
        gray = slice_region.copy()

    # Threshold to find dark regions (bars are dark)
    # Invert so bars become white (high values)
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    # Sum vertically - each X gets a "dark region presence score"
    profile = np.sum(binary, axis=0).astype(float)

    return profile


def count_peaks_in_profile(
    profile: np.ndarray,
    threshold_ratio: float = 0.3,
    min_width: int = 3,
) -> int:
    """
    Count the number of significant peaks (bars) in a horizontal profile.

    Each peak represents a vertical bar. Peaks are found by thresholding
    the profile and counting connected regions above the threshold.

    Args:
        profile: 1D array from compute_horizontal_profile().
        threshold_ratio: Minimum intensity relative to max to be considered a peak.
        min_width: Minimum width in pixels for a region to count as a bar.

    Returns:
        Number of peaks (bars) detected.
    """
    if len(profile) == 0:
        return 0

    max_val = np.max(profile)
    if max_val == 0:
        return 0

    # Normalize and threshold
    normalized = profile / max_val
    is_peak = normalized > threshold_ratio

    # Find connected regions
    labeled_array, num_features = label(is_peak)

    # Filter by minimum width
    valid_bars = 0
    for region_id in range(1, num_features + 1):
        region_mask = labeled_array == region_id
        region_width = np.sum(region_mask)
        if region_width >= min_width:
            valid_bars += 1

    return valid_bars


def count_bars_per_line(
    bar_region: np.ndarray,
    line_boundaries: list[tuple[int, int]],
    slice_margin: int = 5,
) -> list[int]:
    """
    Count how many vertical bars exist at each text line's Y position.

    For each line of text, takes a horizontal slice at that line's center
    and counts the number of vertical bar edges detected.

    This enables detection of asymmetric patterns like "3-4, 1-4" where
    lines 3-4 have 2 bars (internal + external) while lines 1-2 have 1 bar.

    Args:
        bar_region: BGR image of the left margin (bar) region.
        line_boundaries: List of (y_min, y_max) for each text line.
        slice_margin: Pixels above/below line center to include in slice.

    Returns:
        List of bar counts, one per line. E.g., [1, 1, 2, 2] means
        lines 1-2 have 1 bar each, lines 3-4 have 2 bars each.
    """
    if bar_region is None or bar_region.size == 0:
        return []

    if not line_boundaries:
        return []

    bar_counts = []
    region_height = bar_region.shape[0]

    for y_min, y_max in line_boundaries:
        # Take a horizontal slice at the center of this line
        y_center = (y_min + y_max) // 2
        slice_y_start = max(0, y_center - slice_margin)
        slice_y_end = min(region_height, y_center + slice_margin)

        # Skip if slice is too small
        if slice_y_end <= slice_y_start:
            bar_counts.append(0)
            continue

        horizontal_slice = bar_region[slice_y_start:slice_y_end, :]

        # Compute horizontal profile for this slice
        h_profile = compute_horizontal_profile(horizontal_slice)

        # Count peaks (bars) in the profile
        num_bars = count_peaks_in_profile(h_profile)
        bar_counts.append(num_bars)

    return bar_counts


def deduce_repetitions_from_bar_counts(bar_counts: list[int]) -> Optional[str]:
    """
    Deduce repetition patterns from per-line bar counts.

    Logic:
    - Lines with max_bars = covered by ALL bars (internal + external)
    - Lines with >= 1 bar = covered by the outermost bar

    Example:
    - bar_counts = [1, 1, 2, 2] (4 lines)
    - max_bars = 2
    - internal_lines = [3, 4] (where count == max_bars)
    - external_lines = [1, 2, 3, 4] (where count >= 1)
    - Result: "3-4, 1-4"

    Args:
        bar_counts: List of bar counts per line from count_bars_per_line().

    Returns:
        Repetition string like "3-4, 1-4" or None if no bars detected.
    """
    if not bar_counts:
        return None

    max_bars = max(bar_counts)
    if max_bars == 0:
        return None

    # Find lines covered by the external bar (any bar presence)
    external_lines = [i + 1 for i, c in enumerate(bar_counts) if c >= 1]

    # Find lines covered by internal bars (maximum bar count)
    internal_lines = []
    if max_bars > 1:
        internal_lines = [i + 1 for i, c in enumerate(bar_counts) if c == max_bars]

    if not external_lines:
        return None

    result = []

    # Add internal bars first (if different from external)
    if internal_lines and internal_lines != external_lines:
        # Only add if internal covers a contiguous subset
        internal_start = min(internal_lines)
        internal_end = max(internal_lines)
        result.append(f"{internal_start}-{internal_end}")

    # Add external bar
    external_start = min(external_lines)
    external_end = max(external_lines)
    result.append(f"{external_start}-{external_end}")

    return ", ".join(result) if result else None


def find_bar_segments(
    profile: np.ndarray,
    threshold: float,
    image_height: int,
) -> list[BarSegment]:
    """
    Find contiguous segments in the profile that indicate bars.

    Args:
        profile: Vertical projection profile.
        threshold: Minimum intensity relative to max (0.0-1.0).
        image_height: Height of the image (for min segment calculation).

    Returns:
        List of BarSegment objects.
    """
    if profile is None or len(profile) == 0:
        return []

    max_val = np.max(profile)
    if max_val == 0:
        return []

    # Normalize profile
    normalized = profile / max_val

    # Find rows where intensity exceeds threshold
    is_bar = (normalized > threshold).astype(int)

    # Find transitions (start and end of each segment)
    diff = np.diff(is_bar, prepend=0, append=0)
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]

    # Filter segments
    min_height = int(image_height * MIN_SEGMENT_HEIGHT_PERCENT)
    segments = []

    for start, end in zip(starts, ends):
        height = end - start

        # Skip segments that are too short (noise)
        if height < min_height:
            continue

        # Calculate average intensity for this segment
        intensity = np.mean(normalized[start:end])

        segments.append(BarSegment(
            y_start=start,
            y_end=end,
            intensity=intensity,
        ))

    return segments


def get_line_boundaries_tesseract(
    body_image: np.ndarray,
) -> list[tuple[int, int]]:
    """
    Get the Y boundaries of each text line using Tesseract OCR.

    This provides ACTUAL line positions instead of estimated ones,
    which is critical for accurate Y-to-line mapping.

    Args:
        body_image: BGR image of the body zone.

    Returns:
        List of (y_min, y_max) tuples for each line, sorted by y_min.
        Empty list if OCR fails or no text detected.
    """
    if body_image is None or body_image.size == 0:
        return []

    # Convert to RGB for Tesseract (expects RGB, not BGR)
    if len(body_image.shape) == 3:
        rgb_image = cv2.cvtColor(body_image, cv2.COLOR_BGR2RGB)
    else:
        rgb_image = body_image

    try:
        # Get detailed OCR data with word bounding boxes
        data = pytesseract.image_to_data(
            rgb_image,
            output_type=pytesseract.Output.DICT,
            lang='por',  # Portuguese
        )
    except Exception:
        return []

    # Group words by line (using block_num, par_num, line_num as key)
    lines: dict[tuple[int, int, int], dict[str, int]] = {}

    for i, text in enumerate(data['text']):
        # Skip empty or whitespace-only entries
        if not text or not text.strip():
            continue

        # Filter out OCR artifacts (same logic as in main function)
        text_stripped = text.strip()
        text_upper = text_stripped.upper().replace(' ', '')

        # Skip short artifact patterns
        if len(text_upper) <= 4:
            if text_upper.isalpha():
                # Single letters or short codes are often artifacts
                if text_upper in ['XX', 'X', 'WC', 'WCX', 'CC', 'CLX', 'CX', 'SDS', 'PO', 'I', 'II']:
                    continue
            # Dates like (18/01/2020)
            if text_stripped.startswith('(') and '/' in text_stripped:
                continue

        # Skip leading "|" from bar detection
        if text_stripped == '|':
            continue

        line_key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
        y = data['top'][i]
        h = data['height'][i]

        if line_key not in lines:
            lines[line_key] = {'y_min': y, 'y_max': y + h, 'text': text_stripped}
        else:
            lines[line_key]['y_min'] = min(lines[line_key]['y_min'], y)
            lines[line_key]['y_max'] = max(lines[line_key]['y_max'], y + h)
            lines[line_key]['text'] += ' ' + text_stripped

    if not lines:
        return []

    # Common instruction patterns that appear in PDFs but are not hymn text
    # These are extra_instructions like "Em pé", "sem instrumentos", etc.
    INSTRUCTION_PATTERNS = [
        'sem instrumentos',
        'em pé',
        'sentados',
        'sentado',
        'de pé',
        'em pe',  # without accent
        'instrumental',
    ]

    # Filter out lines that are likely artifacts or instructions
    filtered_lines = []
    for line_data in lines.values():
        text = line_data.get('text', '')
        text_lower = text.lower().strip()

        # Real hymn lines usually have more than 2-3 characters
        if len(text) <= 3:
            continue

        # Skip instruction patterns
        is_instruction = False
        for pattern in INSTRUCTION_PATTERNS:
            if pattern in text_lower:
                is_instruction = True
                break
        if is_instruction:
            continue

        filtered_lines.append((line_data['y_min'], line_data['y_max']))

    # Sort by y_min (top to bottom)
    sorted_lines = sorted(filtered_lines, key=lambda x: x[0])

    return sorted_lines


def map_y_to_line_tesseract(
    y: int,
    line_boundaries: list[tuple[int, int]],
    is_end: bool = False,
) -> int:
    """
    Map a Y coordinate to a line number using actual Tesseract positions.

    This is more accurate than proportional mapping because it uses
    the real Y positions of text lines from OCR.

    Args:
        y: Y coordinate in the body zone.
        line_boundaries: List of (y_min, y_max) tuples from get_line_boundaries_tesseract.
        is_end: If True, this is the end of a bar (adjust mapping accordingly).

    Returns:
        1-indexed line number.
    """
    if not line_boundaries:
        return 1

    num_lines = len(line_boundaries)

    # For each line, find where y falls
    for i, (y_min, y_max) in enumerate(line_boundaries):
        line_num = i + 1  # 1-indexed

        if is_end:
            # For bar end: include the line if bar ends at or after line center
            line_center = (y_min + y_max) / 2
            if y <= line_center:
                # Bar ends before this line's center - doesn't cover this line
                return max(1, line_num - 1) if line_num > 1 else 1
            elif y <= y_max:
                # Bar ends within this line - include it
                return line_num
        else:
            # For bar start: include the line if bar starts before line's center
            line_center = (y_min + y_max) / 2
            if y <= line_center:
                # Bar starts at or before this line's center - include this line
                return line_num
            elif y <= y_max:
                # Bar starts in the second half of this line - still include it
                return line_num

    # If we get here, y is after all lines
    return num_lines


def map_y_to_line_v3(
    y: int,
    first_line_y: int,
    line_height: float,
    num_lines: int,
    is_end: bool = False,
) -> int:
    """
    Map a Y coordinate to a line number using estimated line height.

    This approach estimates the line height from the bar segment patterns
    and uses that to map Y coordinates to line numbers.

    Args:
        y: Y coordinate in the body zone.
        first_line_y: Y coordinate where first line starts.
        line_height: Estimated height per line in pixels.
        num_lines: Total number of text lines.
        is_end: If True, this is the end of a bar (use ceiling logic).

    Returns:
        1-indexed line number.
    """
    if line_height <= 0:
        return 1

    # Calculate relative position from first line
    relative_y = y - first_line_y

    # Calculate line number (0-indexed, floating point)
    line_index = relative_y / line_height

    if is_end:
        # For end of bar: the y coordinate represents where the bar ends
        # If it ends exactly at a line boundary (frac ≈ 0), it covers up to the previous line
        # If it ends in the middle of a line (frac > 0.5), include that line
        frac = line_index - int(line_index)
        if frac < 0.1:  # At or very close to boundary
            line = max(1, int(line_index))  # Previous line (without +1)
        elif frac > 0.5:
            line = int(line_index) + 1  # Include current line
        else:
            line = int(line_index) + 1  # Include current line (in first half)
    else:
        # For start of bar: use floor (which line does the start fall in)
        line = int(line_index) + 1

    # Clamp to valid range
    return max(1, min(line, num_lines))


def map_y_to_line_v2(
    y: int,
    span_start: int,
    span_end: int,
    num_lines: int,
    is_end: bool = False,
) -> int:
    """
    Map a Y coordinate to a line number using the bar span as reference.

    This approach assumes that the span from the first bar to the last bar
    covers all lines that have repetition bars. This is more accurate than
    using the full body height.

    Args:
        y: Y coordinate in the body zone.
        span_start: Y coordinate where first bar starts.
        span_end: Y coordinate where last bar ends.
        num_lines: Number of text lines in the hymn.
        is_end: If True, round up for end of bar (more inclusive).

    Returns:
        1-indexed line number.
    """
    span = span_end - span_start
    if span == 0 or num_lines == 0:
        return 1

    # Calculate relative position within the bar span
    relative_y = y - span_start
    proportion = relative_y / span

    # Map to line number (0-indexed first, then convert to 1-indexed)
    line_float = proportion * num_lines

    if is_end:
        # For end of bar, round up to include the line
        line = int(line_float) + 1
        # If we're very close to the end (>90%), round up to next line
        if line_float - int(line_float) > 0.9:
            line = min(num_lines, line + 1)
    else:
        # For start of bar, use floor and add 1 for 1-indexing
        line = int(line_float) + 1

    # Clamp to valid range
    return max(1, min(line, num_lines))


def map_y_to_line(
    y: int,
    total_height: int,
    num_lines: int,
    text_end_y: int = 0,
    is_end: bool = False,
) -> int:
    """
    Map a Y coordinate to a line number using proportional mapping.
    (Legacy function, kept for compatibility)

    Args:
        y: Y coordinate in the body zone.
        total_height: Total height of the body zone.
        num_lines: Number of text lines in the hymn.
        text_end_y: Y coordinate where text actually ends (if known).
        is_end: If True, use ceiling for end of bar (more inclusive).

    Returns:
        1-indexed line number.
    """
    if total_height == 0 or num_lines == 0:
        return 1

    # Use actual text height if provided, otherwise use full height
    effective_height = text_end_y if text_end_y > 0 else total_height

    # Proportional mapping based on text region
    proportion = y / effective_height
    line_float = proportion * num_lines

    if is_end:
        # For end of bar, round up if we're more than 60% into the next line
        line = int(line_float) + 1
        if line_float - int(line_float) < 0.6:
            line = max(1, line)
        else:
            line = min(num_lines, line + 1)
    else:
        # For start of bar, use floor
        line = int(line_float) + 1

    # Clamp to valid range
    return max(1, min(line, num_lines))


def estimate_text_region_height(profile: np.ndarray, threshold: float = 0.05) -> int:
    """
    Estimate where the text region ends based on the profile.

    Looks for the last significant activity in the profile.

    Args:
        profile: Vertical projection profile.
        threshold: Minimum relative intensity to consider as text.

    Returns:
        Estimated Y coordinate where text ends.
    """
    if profile is None or len(profile) == 0:
        return 0

    max_val = np.max(profile)
    if max_val == 0:
        return len(profile)

    # Find the last row with significant intensity
    is_active = profile > (threshold * max_val)

    # Find the last True value
    active_rows = np.where(is_active)[0]
    if len(active_rows) == 0:
        return len(profile)

    # Add some padding (10% of profile length)
    padding = int(len(profile) * 0.1)
    return min(active_rows[-1] + padding, len(profile))


def visualize_detection(
    image: np.ndarray,
    body_zone: Zone,
    segments: list[BarSegment],
    profile: np.ndarray,
) -> np.ndarray:
    """
    Create a debug visualization of the detection.

    Args:
        image: Original BGR image.
        body_zone: Body zone that was analyzed.
        segments: Detected bar segments.
        profile: Vertical projection profile.

    Returns:
        Debug image with annotations.
    """
    debug_image = image.copy()
    h, w = debug_image.shape[:2]

    # Draw body zone boundary
    cv2.rectangle(
        debug_image,
        (body_zone.x_start, body_zone.y_start),
        (body_zone.x_end or w, body_zone.y_end),
        (0, 255, 0),  # Green
        2,
    )

    # Draw detected segments
    bar_width = int((body_zone.x_end or w) * BAR_REGION_PERCENT)

    for i, segment in enumerate(segments):
        # Adjust Y to full image coordinates
        y_start = body_zone.y_start + segment.y_start
        y_end = body_zone.y_start + segment.y_end

        # Draw segment rectangle
        cv2.rectangle(
            debug_image,
            (body_zone.x_start, y_start),
            (body_zone.x_start + bar_width, y_end),
            (0, 0, 255),  # Red
            2,
        )

        # Add label
        cv2.putText(
            debug_image,
            f"Bar {i+1}",
            (body_zone.x_start + bar_width + 5, (y_start + y_end) // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            1,
        )

    return debug_image
