#!/usr/bin/env python3
"""Debug script for visualizing repetition bar detection.

This script helps debug the repetition bar detection algorithm by:
1. Loading a PDF and extracting page images
2. Running the detection algorithm
3. Generating visualizations of the detection process
4. Comparing results with expected values

Usage:
    poetry run python scripts/debug_repetition.py <pdf_path> [--page N] [--output DIR]

Examples:
    # Debug all pages
    poetry run python scripts/debug_repetition.py example.pdf

    # Debug specific page
    poetry run python scripts/debug_repetition.py example.pdf --page 5

    # Save output to directory
    poetry run python scripts/debug_repetition.py example.pdf --output /tmp/debug
"""

import argparse
import sys
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hymn_ocr.ocr_engine import ocr_image
from hymn_ocr.pdf_processor import convert_pdf_to_images
from hymn_ocr.repetition_detector_v2 import (
    BAR_REGION_PERCENT,
    compute_vertical_profile,
    detect_repetition_bars_v2,
    find_bar_segments,
)
from hymn_ocr.zone_detector import detect_zones, extract_zone, pil_to_cv2


def debug_page(
    image: np.ndarray,
    page_number: int,
    output_dir: Path | None = None,
) -> dict:
    """
    Debug repetition detection on a single page.

    Args:
        image: BGR image of the page.
        page_number: Page number (for labeling).
        output_dir: Optional directory to save debug images.

    Returns:
        Dictionary with detection results.
    """
    h, w = image.shape[:2]

    # Detect zones
    zones = detect_zones(image)

    if zones.is_cover:
        print(f"  Page {page_number}: COVER PAGE (skipping)")
        return {"page": page_number, "type": "cover", "repetitions": None}

    if zones.body is None:
        print(f"  Page {page_number}: No body zone detected")
        return {"page": page_number, "type": "no_body", "repetitions": None}

    # Extract body zone
    body_image = extract_zone(image, zones.body)
    body_h, body_w = body_image.shape[:2]

    # OCR the body
    body_text = ocr_image(body_image)
    text_lines = [line for line in body_text.split('\n') if line.strip()]
    num_lines = len(text_lines)

    # Show lines for debug
    print(f"  OCR text lines:")
    for i, line in enumerate(text_lines):
        print(f"    [{i+1}] {line[:60]}")

    # Extract bar region from PAGE margin (not body margin)
    page_h, page_w = image.shape[:2]
    bar_width = max(10, int(page_w * BAR_REGION_PERCENT))
    page_left_margin = image[:, :bar_width]
    bar_region = page_left_margin[zones.body.y_start:zones.body.y_end, :]

    # Compute profile
    profile = compute_vertical_profile(bar_region)

    # Find segments
    segments = find_bar_segments(profile, 0.15, body_h) if profile is not None else []

    # Detect repetitions
    repetitions = detect_repetition_bars_v2(image, zones.body, body_text)

    print(f"  Page {page_number}:")
    print(f"    - Body zone: {zones.body.y_start}-{zones.body.y_end} (height={body_h})")
    print(f"    - Text lines: {num_lines}")
    print(f"    - Bar segments found: {len(segments)}")
    for i, seg in enumerate(segments):
        y_start_pct = seg.y_start / body_h * 100
        y_end_pct = seg.y_end / body_h * 100
        print(f"      Segment {i+1}: y={seg.y_start}-{seg.y_end} ({y_start_pct:.1f}%-{y_end_pct:.1f}%)")
    print(f"    - Repetitions: {repetitions}")

    # NEW: Gap detection analysis for debugging
    from hymn_ocr.repetition_detector_v2 import (
        analyze_bar_columns,
        NUM_COLUMNS,
        detect_gaps_in_segment,
        GAP_DETECTION_THRESHOLD,
        MIN_GAP_HEIGHT_PERCENT,
        BarSegment,
    )

    # Analyze the profile within each segment for gaps
    print(f"    - Gap detection analysis:")
    for seg in segments:
        seg_profile = profile[seg.y_start:seg.y_end]
        if len(seg_profile) > 0:
            max_val = np.max(seg_profile)
            if max_val > 0:
                normalized = seg_profile / max_val
                min_val = np.min(normalized)
                mean_val = np.mean(normalized)
                print(f"      Segment y={seg.y_start}-{seg.y_end}: max={max_val:.0f}, min/max={min_val:.2f}, mean/max={mean_val:.2f}")
                print(f"        Gap threshold: {GAP_DETECTION_THRESHOLD}, min_gap_height: {int(body_h * MIN_GAP_HEIGHT_PERCENT)}")

                # Find potential valleys
                is_valley = normalized < GAP_DETECTION_THRESHOLD
                diff = np.diff(is_valley.astype(int), prepend=0, append=0)
                valley_starts = np.where(diff == 1)[0]
                valley_ends = np.where(diff == -1)[0]
                if len(valley_starts) > 0:
                    print(f"        Valleys (below {GAP_DETECTION_THRESHOLD}):")
                    for vs, ve in zip(valley_starts, valley_ends):
                        print(f"          y={seg.y_start + vs}-{seg.y_start + ve} (height={ve-vs})")
                else:
                    print(f"        No valleys found (profile never drops below {GAP_DETECTION_THRESHOLD} of max)")

                # Try with lower threshold
                for thresh in [0.6, 0.7, 0.8]:
                    is_valley_t = normalized < thresh
                    diff_t = np.diff(is_valley_t.astype(int), prepend=0, append=0)
                    vs_t = np.where(diff_t == 1)[0]
                    if len(vs_t) > 0:
                        print(f"        At threshold {thresh}: {len(vs_t)} valleys found")

    column_profiles = analyze_bar_columns(bar_region, NUM_COLUMNS)

    print(f"    - Bar region size: {bar_region.shape[1]}w x {bar_region.shape[0]}h")
    print(f"    - Columns: {len(column_profiles)}")
    for col_idx, (col_profile, col_start, col_end) in enumerate(column_profiles):
        col_segs = find_bar_segments(col_profile, 0.15, body_h) if col_profile is not None else []
        print(f"      Column {col_idx} (x={col_start}-{col_end}): {len(col_segs)} segments")
        for seg in col_segs:
            print(f"        y={seg.y_start}-{seg.y_end}")

    # Generate visualization
    if output_dir:
        # Create figure with more subplots for column analysis
        fig = plt.figure(figsize=(24, 10))

        # Row 1: Original views
        ax1 = fig.add_subplot(2, 4, 1)
        ax1.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        ax1.axhline(y=zones.body.y_start, color='g', linestyle='--', label='Body start')
        ax1.axhline(y=zones.body.y_end, color='r', linestyle='--', label='Body end')
        ax1.set_title(f"Page {page_number} - Zones")
        ax1.legend()

        ax2 = fig.add_subplot(2, 4, 2)
        ax2.imshow(cv2.cvtColor(bar_region, cv2.COLOR_BGR2RGB))
        # Draw column divisions
        col_width = bar_region.shape[1] // NUM_COLUMNS
        for i in range(1, NUM_COLUMNS):
            ax2.axvline(x=i * col_width, color='yellow', linestyle='--', alpha=0.7)
        ax2.set_title(f"Bar Region ({BAR_REGION_PERCENT*100:.0f}% width) - {NUM_COLUMNS} cols")

        ax3 = fig.add_subplot(2, 4, 3)
        if profile is not None:
            ax3.plot(profile, range(len(profile)), label='Full profile')
            ax3.invert_yaxis()
            ax3.set_xlabel("Intensity")
            ax3.set_ylabel("Y coordinate")
            ax3.set_title("Full Vertical Profile")
            for seg in segments:
                ax3.axhspan(seg.y_start, seg.y_end, alpha=0.3, color='red')

        ax4 = fig.add_subplot(2, 4, 4)
        body_annotated = body_image.copy()
        for seg in segments:
            cv2.rectangle(
                body_annotated,
                (0, seg.y_start),
                (bar_width, seg.y_end),
                (0, 0, 255),
                2,
            )
        ax4.imshow(cv2.cvtColor(body_annotated, cv2.COLOR_BGR2RGB))
        ax4.set_title(f"Detected: {repetitions or 'None'}")

        # Row 2: Column-by-column profiles
        colors = ['blue', 'green', 'red', 'purple', 'orange']
        for col_idx, (col_profile, col_start, col_end) in enumerate(column_profiles):
            ax = fig.add_subplot(2, 4, 5 + col_idx)
            if col_profile is not None:
                ax.plot(col_profile, range(len(col_profile)), color=colors[col_idx % len(colors)])
                ax.invert_yaxis()
                ax.set_xlabel("Intensity")
                ax.set_ylabel("Y coordinate")

                # Mark segments for this column
                col_segs = find_bar_segments(col_profile, 0.15, body_h) if col_profile is not None else []
                for seg in col_segs:
                    ax.axhspan(seg.y_start, seg.y_end, alpha=0.3, color=colors[col_idx % len(colors)])

                ax.set_title(f"Column {col_idx} (x={col_start}-{col_end}): {len(col_segs)} segs")
            else:
                ax.set_title(f"Column {col_idx}: No profile")

        plt.tight_layout()
        output_path = output_dir / f"page_{page_number:03d}_debug.png"
        plt.savefig(output_path, dpi=150)
        plt.close()
        print(f"    - Saved: {output_path}")

    return {
        "page": page_number,
        "type": "hymn",
        "num_lines": num_lines,
        "segments": len(segments),
        "repetitions": repetitions,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Debug repetition bar detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--page", type=int, help="Process only this page number")
    parser.add_argument("--output", "-o", help="Output directory for debug images")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for PDF conversion")

    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    output_dir = None
    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing: {pdf_path}")
    print(f"DPI: {args.dpi}")

    # Convert PDF to images
    if args.page:
        images = convert_pdf_to_images(pdf_path, dpi=args.dpi, first_page=args.page, last_page=args.page)
        page_numbers = [args.page]
    else:
        images = convert_pdf_to_images(pdf_path, dpi=args.dpi)
        page_numbers = range(1, len(images) + 1)

    print(f"Pages to process: {len(images)}")
    print()

    results = []
    for pil_image, page_num in zip(images, page_numbers):
        cv2_image = pil_to_cv2(pil_image)
        result = debug_page(cv2_image, page_num, output_dir)
        results.append(result)
        print()

    # Summary
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)

    hymn_pages = [r for r in results if r["type"] == "hymn"]
    with_bars = [r for r in hymn_pages if r["repetitions"]]
    without_bars = [r for r in hymn_pages if not r["repetitions"]]

    print(f"Total pages: {len(results)}")
    print(f"Hymn pages: {len(hymn_pages)}")
    print(f"With repetitions: {len(with_bars)}")
    print(f"Without repetitions: {len(without_bars)}")

    if with_bars:
        print("\nPages with repetitions:")
        for r in with_bars:
            print(f"  Page {r['page']}: {r['repetitions']}")


if __name__ == "__main__":
    main()
