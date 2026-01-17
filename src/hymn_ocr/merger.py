"""Merge multi-page hymns into complete hymn objects."""

from typing import Optional

from hymn_ocr.models import Hymn, PageData, PageType
from hymn_ocr.repetition_detector import adjust_repetition_numbers


def merge_multipage_hymns(pages_data: list[PageData]) -> list[Hymn]:
    """
    Combine pages of continuation with the preceding hymn.

    Detects continuation by:
    - Page type is CONTINUATION
    - No header on the page

    Args:
        pages_data: List of PageData from processed pages.

    Returns:
        List of merged Hymn objects.
    """
    if not pages_data:
        return []

    merged_hymns = []
    current_hymn_data: Optional[dict] = None

    for page in pages_data:
        if page.page_type == PageType.COVER:
            # Skip cover pages
            continue

        if page.page_type == PageType.BLANK:
            # Skip blank pages
            continue

        if page.page_type == PageType.NEW_HYMN:
            # Save previous hymn if exists
            if current_hymn_data:
                try:
                    hymn = Hymn(**current_hymn_data)
                    merged_hymns.append(hymn)
                except Exception:
                    # Skip invalid hymns
                    pass

            # Start new hymn
            current_hymn_data = {
                "number": page.hymn_number or 0,
                "title": page.hymn_title or "Untitled",
                "text": page.body_text or "",
                "original_number": page.original_number,
                "style": page.style,
                "offered_to": page.offered_to,
                "extra_instructions": page.extra_instructions,
                "repetitions": page.repetitions,
                "received_at": page.received_at,
            }

        elif page.page_type == PageType.CONTINUATION and current_hymn_data:
            # Append text to current hymn
            if page.body_text:
                prev_text = current_hymn_data.get("text", "")
                if prev_text:
                    current_hymn_data["text"] = prev_text + "\n\n" + page.body_text
                else:
                    current_hymn_data["text"] = page.body_text

            # Take date/repetitions from continuation if available
            if page.received_at:
                current_hymn_data["received_at"] = page.received_at

            if page.repetitions:
                # Adjust repetition line numbers
                current_hymn_data["repetitions"] = adjust_repetition_numbers(
                    current_hymn_data.get("repetitions"),
                    page.repetitions,
                    current_hymn_data.get("text", ""),
                )

    # Don't forget the last hymn
    if current_hymn_data:
        try:
            hymn = Hymn(**current_hymn_data)
            merged_hymns.append(hymn)
        except Exception:
            pass

    return merged_hymns


def create_page_data_from_ocr(
    page_number: int,
    page_type: PageType,
    header_text: Optional[str] = None,
    metadata_text: Optional[str] = None,
    body_text: Optional[str] = None,
    footer_text: Optional[str] = None,
    repetitions: Optional[str] = None,
    hymn_number: Optional[int] = None,
    hymn_title: Optional[str] = None,
    original_number: Optional[int] = None,
    offered_to: Optional[str] = None,
    style: Optional[str] = None,
    extra_instructions: Optional[str] = None,
    received_at: Optional[str] = None,
) -> PageData:
    """
    Create a PageData object with OCR results and parsed data.

    This is a helper function to construct PageData objects.
    """
    return PageData(
        page_number=page_number,
        page_type=page_type,
        header_text=header_text,
        metadata_text=metadata_text,
        body_text=body_text,
        footer_text=footer_text,
        repetitions=repetitions,
        hymn_number=hymn_number,
        hymn_title=hymn_title,
        original_number=original_number,
        offered_to=offered_to,
        style=style,
        extra_instructions=extra_instructions,
        received_at=received_at,
    )


def count_hymns_by_type(pages_data: list[PageData]) -> dict[str, int]:
    """
    Count pages by type for diagnostics.

    Args:
        pages_data: List of PageData objects.

    Returns:
        Dictionary with counts by page type.
    """
    counts = {
        "cover": 0,
        "new_hymn": 0,
        "continuation": 0,
        "blank": 0,
    }

    for page in pages_data:
        counts[page.page_type.value] += 1

    return counts
