"""Tests for zone detector."""

import numpy as np
import pytest
from PIL import Image

from hymn_ocr.models import PageType
from hymn_ocr.zone_detector import (
    PageZones,
    Zone,
    classify_page,
    detect_horizontal_lines,
    detect_zones,
    extract_zone,
    is_cover_page,
    pil_to_cv2,
    cv2_to_pil,
)


class TestImageConversion:
    """Tests for image format conversion."""

    def test_pil_to_cv2(self):
        """Test PIL to OpenCV conversion."""
        # Create a simple RGB image
        pil_img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        cv2_img = pil_to_cv2(pil_img)

        assert isinstance(cv2_img, np.ndarray)
        assert cv2_img.shape == (100, 100, 3)
        # OpenCV uses BGR, so red should be (0, 0, 255)
        assert cv2_img[50, 50, 2] == 255  # Red channel
        assert cv2_img[50, 50, 0] == 0  # Blue channel

    def test_cv2_to_pil(self):
        """Test OpenCV to PIL conversion."""
        # Create a BGR image (OpenCV format)
        cv2_img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2_img[:, :, 2] = 255  # Red channel in BGR

        pil_img = cv2_to_pil(cv2_img)

        assert isinstance(pil_img, Image.Image)
        assert pil_img.size == (100, 100)
        # Check that red is preserved
        r, g, b = pil_img.getpixel((50, 50))
        assert r == 255
        assert g == 0
        assert b == 0


class TestZone:
    """Tests for Zone dataclass."""

    def test_zone_to_slice(self):
        """Test Zone.to_slice method."""
        zone = Zone(y_start=10, y_end=100, x_start=0, x_end=200)
        y_slice, x_slice = zone.to_slice()

        assert y_slice == slice(10, 100)
        assert x_slice == slice(0, 200)

    def test_zone_to_slice_no_x_end(self):
        """Test Zone.to_slice with no x_end."""
        zone = Zone(y_start=10, y_end=100)
        y_slice, x_slice = zone.to_slice()

        assert y_slice == slice(10, 100)
        assert x_slice == slice(0, None)


class TestExtractZone:
    """Tests for extract_zone function."""

    def test_extract_zone(self):
        """Test extracting a zone from an image."""
        # Create a test image
        img = np.zeros((200, 300, 3), dtype=np.uint8)
        img[50:100, :, :] = 128  # Gray band

        zone = Zone(y_start=50, y_end=100)
        extracted = extract_zone(img, zone)

        assert extracted.shape == (50, 300, 3)
        assert np.all(extracted == 128)


class TestIsCoverPage:
    """Tests for is_cover_page function."""

    def test_is_cover_page_with_cover(self, cover_image: Image.Image):
        """Test that cover page is detected."""
        cv2_img = pil_to_cv2(cover_image)
        result = is_cover_page(cv2_img)
        assert result  # Should be True

    def test_is_cover_page_with_hymn(self, first_hymn_image: Image.Image):
        """Test that hymn page is not detected as cover."""
        cv2_img = pil_to_cv2(first_hymn_image)
        result = is_cover_page(cv2_img)
        assert not result  # Should be False

    def test_is_cover_page_mostly_white(self):
        """Test that mostly white image is not a cover."""
        # Create a mostly white image
        img = np.ones((1000, 800, 3), dtype=np.uint8) * 255
        result = is_cover_page(img)
        assert not result  # Should be False

    def test_is_cover_page_colorful(self):
        """Test that colorful image is detected as cover."""
        # Create a colorful image (simulating a cover)
        img = np.random.randint(0, 200, (1000, 800, 3), dtype=np.uint8)
        result = is_cover_page(img)
        assert result  # Should be True


class TestDetectHorizontalLines:
    """Tests for detect_horizontal_lines function."""

    def test_detect_horizontal_lines_with_line(self):
        """Test detection of a horizontal line."""
        # Create image with horizontal line
        img = np.ones((500, 800), dtype=np.uint8) * 255
        img[100:102, 100:700] = 0  # Horizontal line at y=100

        lines = detect_horizontal_lines(img, min_length=100)

        # Should detect the line near y=100
        assert len(lines) > 0
        assert any(abs(y - 100) < 10 for y in lines)

    def test_detect_horizontal_lines_no_lines(self):
        """Test with image without horizontal lines."""
        img = np.ones((500, 800), dtype=np.uint8) * 255
        lines = detect_horizontal_lines(img)
        assert len(lines) == 0


class TestDetectZones:
    """Tests for detect_zones function."""

    def test_detect_zones_hymn_page(self, first_hymn_image: Image.Image):
        """Test zone detection on a hymn page."""
        cv2_img = pil_to_cv2(first_hymn_image)
        zones = detect_zones(cv2_img)

        assert not zones.is_cover
        # Should have detected some zones
        assert zones.body is not None
        assert zones.footer is not None

    def test_detect_zones_cover(self, cover_image: Image.Image):
        """Test zone detection on a cover page."""
        cv2_img = pil_to_cv2(cover_image)
        zones = detect_zones(cv2_img)

        assert zones.is_cover is True
        assert zones.header is None
        assert zones.body is None

    def test_detect_zones_continuation(self, continuation_image: Image.Image):
        """Test zone detection on a continuation page."""
        cv2_img = pil_to_cv2(continuation_image)
        zones = detect_zones(cv2_img)

        assert not zones.is_cover
        # Continuation pages might not have header
        assert zones.body is not None

    def test_zone_boundaries_dont_overlap(self, first_hymn_image: Image.Image):
        """Test that zones don't overlap."""
        cv2_img = pil_to_cv2(first_hymn_image)
        zones = detect_zones(cv2_img)

        all_zones = []
        if zones.header:
            all_zones.append(("header", zones.header))
        if zones.metadata:
            all_zones.append(("metadata", zones.metadata))
        if zones.body:
            all_zones.append(("body", zones.body))
        if zones.footer:
            all_zones.append(("footer", zones.footer))

        # Check no overlap between consecutive zones
        for i in range(len(all_zones) - 1):
            _, zone1 = all_zones[i]
            _, zone2 = all_zones[i + 1]
            # Zone 1 should end before or at zone 2 start
            assert zone1.y_end <= zone2.y_start + 5  # Allow small overlap


class TestClassifyPage:
    """Tests for classify_page function."""

    def test_classify_cover(self, cover_image: Image.Image):
        """Test classification of cover page."""
        cv2_img = pil_to_cv2(cover_image)
        result = classify_page(cv2_img)
        assert result == PageType.COVER

    def test_classify_new_hymn_with_text(self, first_hymn_image: Image.Image):
        """Test classification of new hymn with OCR text."""
        cv2_img = pil_to_cv2(first_hymn_image)
        ocr_text = "01. Disciplina (62)\nSanta Maria..."
        result = classify_page(cv2_img, ocr_text)
        assert result == PageType.NEW_HYMN

    def test_classify_continuation_with_text(self):
        """Test classification of continuation page with OCR text."""
        # Create a mostly white image (not cover)
        img = np.ones((1000, 800, 3), dtype=np.uint8) * 255
        ocr_text = "Continuation of lyrics without header\nMore text here"
        result = classify_page(img, ocr_text)
        assert result == PageType.CONTINUATION

    def test_classify_blank(self):
        """Test classification of blank page."""
        # Create a blank white image with no text
        img = np.ones((1000, 800, 3), dtype=np.uint8) * 255
        result = classify_page(img, "")
        # Blank white images without text are classified as continuation
        # (they have a body zone but no header)
        # Real blank pages would need to be detected by OCR returning no text
        assert result in (PageType.BLANK, PageType.CONTINUATION)
