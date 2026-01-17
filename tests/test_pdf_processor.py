"""Tests for PDF processor."""

from pathlib import Path
import tempfile

import pytest
from PIL import Image

from hymn_ocr.pdf_processor import (
    convert_pdf_to_images,
    get_page_count,
    save_page_as_image,
)


class TestConvertPdfToImages:
    """Tests for convert_pdf_to_images function."""

    def test_convert_pdf_returns_images(self, sample_pdf_path: Path):
        """Test that PDF conversion returns list of PIL Images."""
        images = convert_pdf_to_images(sample_pdf_path, dpi=72)
        assert isinstance(images, list)
        assert len(images) > 0
        assert all(isinstance(img, Image.Image) for img in images)

    def test_convert_specific_pages(self, sample_pdf_path: Path):
        """Test converting specific page range."""
        images = convert_pdf_to_images(
            sample_pdf_path, dpi=72, first_page=2, last_page=4
        )
        assert len(images) == 3

    def test_convert_single_page(self, sample_pdf_path: Path):
        """Test converting a single page."""
        images = convert_pdf_to_images(
            sample_pdf_path, dpi=72, first_page=1, last_page=1
        )
        assert len(images) == 1

    def test_convert_dpi_affects_size(self, sample_pdf_path: Path):
        """Test that higher DPI produces larger images."""
        images_72 = convert_pdf_to_images(
            sample_pdf_path, dpi=72, first_page=1, last_page=1
        )
        images_150 = convert_pdf_to_images(
            sample_pdf_path, dpi=150, first_page=1, last_page=1
        )

        # Higher DPI should result in larger image
        size_72 = images_72[0].width * images_72[0].height
        size_150 = images_150[0].width * images_150[0].height
        assert size_150 > size_72

    def test_convert_nonexistent_file(self):
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError):
            convert_pdf_to_images("/nonexistent/path/file.pdf")

    def test_convert_non_pdf_file(self, images_dir: Path):
        """Test that ValueError is raised for non-PDF file."""
        # Use an existing image file as non-PDF
        image_file = images_dir / "page_01.png"
        if image_file.exists():
            with pytest.raises(ValueError) as exc_info:
                convert_pdf_to_images(image_file)
            assert "not a PDF" in str(exc_info.value)

    def test_convert_accepts_string_path(self, sample_pdf_path: Path):
        """Test that string paths are accepted."""
        images = convert_pdf_to_images(str(sample_pdf_path), dpi=72, first_page=1, last_page=1)
        assert len(images) == 1


class TestGetPageCount:
    """Tests for get_page_count function."""

    def test_get_page_count(self, sample_pdf_path: Path):
        """Test getting page count from PDF."""
        count = get_page_count(sample_pdf_path)
        assert count == 50  # Known page count of sample PDF

    def test_get_page_count_nonexistent(self):
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError):
            get_page_count("/nonexistent/file.pdf")


class TestSavePageAsImage:
    """Tests for save_page_as_image function."""

    def test_save_page_creates_file(self, sample_pdf_path: Path):
        """Test that save_page_as_image creates an image file."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            output_path = Path(f.name)

        try:
            result = save_page_as_image(sample_pdf_path, 1, output_path, dpi=72)
            assert result == output_path
            assert output_path.exists()

            # Verify it's a valid image
            img = Image.open(output_path)
            assert img.width > 0
            assert img.height > 0
        finally:
            output_path.unlink(missing_ok=True)

    def test_save_page_returns_path(self, sample_pdf_path: Path):
        """Test that save_page_as_image returns the output path."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            output_path = Path(f.name)

        try:
            result = save_page_as_image(sample_pdf_path, 2, output_path, dpi=72)
            assert isinstance(result, Path)
            assert result.exists()
        finally:
            output_path.unlink(missing_ok=True)
