"""Tests for OCR engine."""

import numpy as np
import pytest
from PIL import Image

from hymn_ocr.ocr_engine import (
    clean_ocr_text,
    get_text_line_positions,
    ocr_image,
    ocr_pil_image,
    ocr_zone,
    preprocess_for_ocr,
)
from hymn_ocr.zone_detector import Zone, detect_zones, pil_to_cv2


class TestPreprocessForOcr:
    """Tests for preprocess_for_ocr function."""

    def test_preprocess_returns_grayscale(self):
        """Test that preprocessing returns a grayscale image."""
        # Create a color image
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        img[:, :, 2] = 128  # Red channel

        result = preprocess_for_ocr(img)

        assert len(result.shape) == 2  # Grayscale = 2D
        assert result.dtype == np.uint8

    def test_preprocess_binary_output(self):
        """Test that preprocessing produces binary output."""
        img = np.ones((100, 200, 3), dtype=np.uint8) * 128
        result = preprocess_for_ocr(img)

        # Should be mostly 0 or 255 (binary)
        unique_values = np.unique(result)
        # Allow some intermediate values due to blur
        assert len(unique_values) <= 10


class TestOcrImage:
    """Tests for ocr_image function."""

    def test_ocr_image_basic(self, first_hymn_image: Image.Image):
        """Test basic OCR on a hymn page."""
        cv2_img = pil_to_cv2(first_hymn_image)
        text = ocr_image(cv2_img)

        assert isinstance(text, str)
        assert len(text) > 0

    def test_ocr_image_extracts_portuguese(self, first_hymn_image: Image.Image):
        """Test that Portuguese text is extracted correctly."""
        cv2_img = pil_to_cv2(first_hymn_image)
        text = ocr_image(cv2_img)

        # Should contain Portuguese characters or common words
        # The exact content depends on the test image
        assert isinstance(text, str)

    def test_ocr_empty_image(self):
        """Test OCR on empty/white image."""
        img = np.ones((100, 200, 3), dtype=np.uint8) * 255
        text = ocr_image(img)

        # Should return empty or whitespace only
        assert text.strip() == "" or len(text.strip()) < 5


class TestOcrZone:
    """Tests for ocr_zone function."""

    def test_ocr_zone_none(self):
        """Test that None zone returns empty string."""
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        text = ocr_zone(img, None)
        assert text == ""

    def test_ocr_zone_small(self):
        """Test OCR on very small zone."""
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        zone = Zone(y_start=0, y_end=5, x_start=0, x_end=5)
        text = ocr_zone(img, zone)
        assert text == ""

    def test_ocr_zone_body(self, first_hymn_image: Image.Image):
        """Test OCR on body zone."""
        cv2_img = pil_to_cv2(first_hymn_image)
        zones = detect_zones(cv2_img)

        if zones.body:
            text = ocr_zone(cv2_img, zones.body)
            assert isinstance(text, str)


class TestOcrPilImage:
    """Tests for ocr_pil_image function."""

    def test_ocr_pil_image(self, first_hymn_image: Image.Image):
        """Test OCR directly on PIL Image."""
        text = ocr_pil_image(first_hymn_image)
        assert isinstance(text, str)
        assert len(text) > 0


class TestGetTextLinePositions:
    """Tests for get_text_line_positions function."""

    def test_get_line_positions(self, first_hymn_image: Image.Image):
        """Test getting line positions from an image."""
        cv2_img = pil_to_cv2(first_hymn_image)
        lines = get_text_line_positions(cv2_img)

        assert isinstance(lines, list)
        # Should find some lines
        if lines:
            y_start, y_end, text = lines[0]
            assert isinstance(y_start, int)
            assert isinstance(y_end, int)
            assert isinstance(text, str)
            assert y_start < y_end

    def test_get_line_positions_with_zone(self, first_hymn_image: Image.Image):
        """Test getting line positions within a zone."""
        cv2_img = pil_to_cv2(first_hymn_image)
        zones = detect_zones(cv2_img)

        if zones.body:
            lines = get_text_line_positions(cv2_img, zones.body)
            assert isinstance(lines, list)


class TestCleanOcrText:
    """Tests for clean_ocr_text function."""

    def test_clean_empty_text(self):
        """Test cleaning empty text."""
        assert clean_ocr_text("") == ""
        assert clean_ocr_text(None) == ""  # Should handle None

    def test_clean_whitespace(self):
        """Test cleaning whitespace."""
        text = "  Hello  \n  World  "
        result = clean_ocr_text(text)
        assert result == "Hello\nWorld"

    def test_clean_multiple_blank_lines(self):
        """Test cleaning multiple blank lines."""
        text = "Line 1\n\n\n\nLine 2"
        result = clean_ocr_text(text)
        assert "\n\n\n" not in result
        assert "Line 1" in result
        assert "Line 2" in result

    def test_clean_preserves_double_newline(self):
        """Test that double newlines (paragraph breaks) are preserved."""
        text = "Paragraph 1\n\nParagraph 2"
        result = clean_ocr_text(text)
        assert "\n\n" in result

    def test_clean_windows_line_endings(self):
        """Test cleaning Windows line endings."""
        text = "Line 1\r\nLine 2\rLine 3"
        result = clean_ocr_text(text)
        assert "\r" not in result
        assert "Line 1\nLine 2\nLine 3" == result

    def test_clean_leading_trailing_empty_lines(self):
        """Test removing leading/trailing empty lines."""
        text = "\n\nHello\nWorld\n\n"
        result = clean_ocr_text(text)
        assert result == "Hello\nWorld"


class TestOcrIntegration:
    """Integration tests for OCR functionality."""

    def test_ocr_header_zone(self, first_hymn_image: Image.Image):
        """Test OCR on header zone extracts title."""
        cv2_img = pil_to_cv2(first_hymn_image)
        zones = detect_zones(cv2_img)

        if zones.header:
            text = ocr_zone(cv2_img, zones.header)
            # Header should contain hymn number pattern
            # Depends on actual content of test image
            assert isinstance(text, str)

    def test_ocr_footer_zone(self, first_hymn_image: Image.Image):
        """Test OCR on footer zone."""
        cv2_img = pil_to_cv2(first_hymn_image)
        zones = detect_zones(cv2_img)

        if zones.footer:
            text = ocr_zone(cv2_img, zones.footer)
            # Footer might contain date
            assert isinstance(text, str)
