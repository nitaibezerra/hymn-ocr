"""PDF to images conversion using pdf2image."""

from pathlib import Path
from typing import Optional

from pdf2image import convert_from_path
from PIL import Image


def convert_pdf_to_images(
    pdf_path: str | Path,
    dpi: int = 300,
    first_page: Optional[int] = None,
    last_page: Optional[int] = None,
) -> list[Image.Image]:
    """
    Convert a PDF file to a list of PIL Image objects.

    Args:
        pdf_path: Path to the PDF file.
        dpi: Resolution for conversion. Higher = better quality but slower.
        first_page: First page to convert (1-indexed). None = start from beginning.
        last_page: Last page to convert (1-indexed). None = go to end.

    Returns:
        List of PIL Image objects, one per page.

    Raises:
        FileNotFoundError: If the PDF file doesn't exist.
        pdf2image.exceptions.PDFPageCountError: If PDF is invalid.
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    if not pdf_path.suffix.lower() == ".pdf":
        raise ValueError(f"File is not a PDF: {pdf_path}")

    images = convert_from_path(
        pdf_path,
        dpi=dpi,
        first_page=first_page,
        last_page=last_page,
    )

    return images


def get_page_count(pdf_path: str | Path) -> int:
    """
    Get the number of pages in a PDF.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Number of pages.
    """
    from pdf2image.pdf2image import pdfinfo_from_path

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    info = pdfinfo_from_path(str(pdf_path))
    return info["Pages"]


def save_page_as_image(
    pdf_path: str | Path,
    page_number: int,
    output_path: str | Path,
    dpi: int = 300,
) -> Path:
    """
    Extract a single page from PDF and save as image.

    Args:
        pdf_path: Path to the PDF file.
        page_number: Page number to extract (1-indexed).
        output_path: Path to save the image.
        dpi: Resolution for conversion.

    Returns:
        Path to the saved image.
    """
    images = convert_pdf_to_images(
        pdf_path,
        dpi=dpi,
        first_page=page_number,
        last_page=page_number,
    )

    if not images:
        raise ValueError(f"Could not extract page {page_number}")

    output_path = Path(output_path)
    images[0].save(output_path)

    return output_path
