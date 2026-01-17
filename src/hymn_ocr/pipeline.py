"""Complete OCR pipeline for PDF to YAML conversion."""

from pathlib import Path
from typing import Callable, Optional

from PIL import Image

from hymn_ocr.merger import merge_multipage_hymns
from hymn_ocr.models import Hymn, HymnBook, PageData, PageType
from hymn_ocr.ocr_engine import clean_ocr_text, get_text_line_positions, ocr_zone
from hymn_ocr.parser import (
    clean_body_text,
    parse_date,
    parse_header,
    parse_metadata,
)
from hymn_ocr.pdf_processor import convert_pdf_to_images, get_page_count
from hymn_ocr.repetition_detector import detect_repetition_bars
from hymn_ocr.zone_detector import classify_page, detect_zones, pil_to_cv2


def process_page(
    image: Image.Image,
    page_number: int,
) -> PageData:
    """
    Process a single page image through the OCR pipeline.

    Args:
        image: PIL Image of the page.
        page_number: Page number (1-indexed).

    Returns:
        PageData with all extracted information.
    """
    # Convert to OpenCV format
    cv2_image = pil_to_cv2(image)

    # Detect zones
    zones = detect_zones(cv2_image)

    # If it's a cover page, return early
    if zones.is_cover:
        return PageData(
            page_number=page_number,
            page_type=PageType.COVER,
        )

    # OCR each zone
    header_text = clean_ocr_text(ocr_zone(cv2_image, zones.header)) if zones.header else None
    metadata_text = clean_ocr_text(ocr_zone(cv2_image, zones.metadata)) if zones.metadata else None
    body_text = clean_ocr_text(ocr_zone(cv2_image, zones.body)) if zones.body else None
    footer_text = clean_ocr_text(ocr_zone(cv2_image, zones.footer)) if zones.footer else None

    # Combine all text for classification
    full_text = "\n".join(filter(None, [header_text, metadata_text, body_text, footer_text]))

    # Classify page type
    page_type = classify_page(cv2_image, full_text)

    # Create base page data
    page_data = PageData(
        page_number=page_number,
        page_type=page_type,
        header_text=header_text,
        metadata_text=metadata_text,
        body_text=clean_body_text(body_text) if body_text else None,
        footer_text=footer_text,
    )

    # If it's a new hymn, parse header and metadata
    if page_type == PageType.NEW_HYMN and header_text:
        header_info = parse_header(header_text)
        if header_info:
            page_data.hymn_number = header_info.number
            page_data.hymn_title = header_info.title
            page_data.original_number = header_info.original_number

        if metadata_text:
            metadata_info = parse_metadata(metadata_text)
            page_data.offered_to = metadata_info.offered_to
            page_data.style = metadata_info.style
            page_data.extra_instructions = metadata_info.extra_instructions

    # Parse date from footer
    if footer_text:
        page_data.received_at = parse_date(footer_text)

    # Detect repetition bars in body zone
    if zones.body:
        text_lines = get_text_line_positions(cv2_image, zones.body)
        page_data.repetitions = detect_repetition_bars(
            cv2_image, text_lines=text_lines, zone=zones.body
        )

    return page_data


def process_pdf(
    pdf_path: str | Path,
    dpi: int = 300,
    first_page: Optional[int] = None,
    last_page: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> list[PageData]:
    """
    Process a PDF file through the OCR pipeline.

    Args:
        pdf_path: Path to the PDF file.
        dpi: Resolution for PDF conversion.
        first_page: First page to process (1-indexed).
        last_page: Last page to process (1-indexed).
        progress_callback: Optional callback(current, total) for progress.

    Returns:
        List of PageData for each processed page.
    """
    pdf_path = Path(pdf_path)

    # Get total page count
    total_pages = get_page_count(pdf_path)

    # Apply page range
    start = first_page or 1
    end = last_page or total_pages

    # Convert PDF to images
    images = convert_pdf_to_images(pdf_path, dpi=dpi, first_page=start, last_page=end)

    pages_data = []

    for i, image in enumerate(images):
        page_number = start + i

        if progress_callback:
            progress_callback(i + 1, len(images))

        page_data = process_page(image, page_number)
        pages_data.append(page_data)

    return pages_data


def create_hymnbook(
    pages_data: list[PageData],
    name: str = "Hymn Book",
    owner_name: str = "Unknown",
    intro_name: Optional[str] = None,
) -> HymnBook:
    """
    Create a HymnBook from processed page data.

    Args:
        pages_data: List of PageData from process_pdf.
        name: Name of the hymn book.
        owner_name: Owner's name.
        intro_name: Optional introduction name.

    Returns:
        HymnBook object.
    """
    hymns = merge_multipage_hymns(pages_data)

    return HymnBook(
        name=name,
        owner_name=owner_name,
        intro_name=intro_name,
        hymns=hymns,
    )


def pdf_to_hymnbook(
    pdf_path: str | Path,
    name: str = "Hymn Book",
    owner_name: str = "Unknown",
    intro_name: Optional[str] = None,
    dpi: int = 300,
    first_page: Optional[int] = None,
    last_page: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> HymnBook:
    """
    Complete pipeline: PDF -> HymnBook.

    This is the main entry point for converting a PDF to a HymnBook.

    Args:
        pdf_path: Path to the PDF file.
        name: Name of the hymn book.
        owner_name: Owner's name.
        intro_name: Optional introduction name.
        dpi: Resolution for PDF conversion.
        first_page: First page to process (1-indexed).
        last_page: Last page to process (1-indexed).
        progress_callback: Optional callback(current, total) for progress.

    Returns:
        HymnBook object with all extracted hymns.
    """
    pages_data = process_pdf(
        pdf_path,
        dpi=dpi,
        first_page=first_page,
        last_page=last_page,
        progress_callback=progress_callback,
    )

    return create_hymnbook(
        pages_data,
        name=name,
        owner_name=owner_name,
        intro_name=intro_name,
    )


def extract_cover_info(image: Image.Image) -> dict:
    """
    Extract information from a cover page.

    This is a placeholder - actual implementation would use OCR
    on the cover to extract book name and owner name.

    Args:
        image: PIL Image of the cover page.

    Returns:
        Dictionary with name and owner_name.
    """
    # TODO: Implement cover OCR
    # For now, return placeholders
    return {
        "name": "Hymn Book",
        "owner_name": "Unknown",
    }
