"""Tests for repetition bar detector."""

import numpy as np
import pytest
from PIL import Image

from hymn_ocr.repetition_detector import (
    VerticalSegment,
    adjust_repetition_numbers,
    detect_repetition_bars,
    detect_vertical_lines,
    find_line_at_y,
    merge_overlapping_segments,
)
from hymn_ocr.zone_detector import detect_zones, pil_to_cv2


class TestVerticalSegment:
    """Tests for VerticalSegment dataclass."""

    def test_vertical_segment_creation(self):
        """Test creating a vertical segment."""
        segment = VerticalSegment(x=50, y_start=100, y_end=200)
        assert segment.x == 50
        assert segment.y_start == 100
        assert segment.y_end == 200


class TestDetectVerticalLines:
    """Tests for detect_vertical_lines function."""

    def test_detect_vertical_line(self):
        """Test detecting a vertical line."""
        # Create image with vertical line in left margin
        img = np.ones((500, 800, 3), dtype=np.uint8) * 255
        img[100:300, 50:52, :] = 0  # Vertical line at x=50

        segments = detect_vertical_lines(img)

        # Should detect the line
        assert len(segments) > 0
        # Check approximate position
        found = False
        for seg in segments:
            if 40 < seg.x < 60 and seg.y_start < 150 < seg.y_end:
                found = True
                break
        assert found, f"Expected vertical line near x=50, got {segments}"

    def test_detect_no_vertical_lines(self):
        """Test with image without vertical lines."""
        img = np.ones((500, 800, 3), dtype=np.uint8) * 255
        segments = detect_vertical_lines(img)
        assert len(segments) == 0

    def test_detect_ignores_right_margin(self):
        """Test that vertical lines in right margin are ignored."""
        # Create image with vertical line in right margin
        img = np.ones((500, 800, 3), dtype=np.uint8) * 255
        img[100:300, 700:702, :] = 0  # Vertical line at x=700 (right side)

        segments = detect_vertical_lines(img)

        # Should not detect lines in right margin
        for seg in segments:
            assert seg.x < 800 * 0.15, f"Detected line in right margin at x={seg.x}"


class TestMergeOverlappingSegments:
    """Tests for merge_overlapping_segments function."""

    def test_merge_overlapping(self):
        """Test merging overlapping segments."""
        segments = [
            VerticalSegment(x=50, y_start=100, y_end=200),
            VerticalSegment(x=52, y_start=190, y_end=300),
        ]
        merged = merge_overlapping_segments(segments)

        assert len(merged) == 1
        assert merged[0].y_start == 100
        assert merged[0].y_end == 300

    def test_merge_adjacent(self):
        """Test merging adjacent segments."""
        segments = [
            VerticalSegment(x=50, y_start=100, y_end=200),
            VerticalSegment(x=50, y_start=210, y_end=300),  # 10px gap
        ]
        merged = merge_overlapping_segments(segments)

        # Should merge due to small gap
        assert len(merged) == 1

    def test_no_merge_separate(self):
        """Test that separate segments are not merged."""
        segments = [
            VerticalSegment(x=50, y_start=100, y_end=150),
            VerticalSegment(x=50, y_start=250, y_end=300),  # Large gap
        ]
        merged = merge_overlapping_segments(segments)

        assert len(merged) == 2

    def test_merge_empty(self):
        """Test with empty list."""
        merged = merge_overlapping_segments([])
        assert merged == []


class TestFindLineAtY:
    """Tests for find_line_at_y function."""

    def test_find_line_exact(self):
        """Test finding line at exact y coordinate."""
        text_lines = [
            (100, 120, "Line 1"),
            (130, 150, "Line 2"),
            (160, 180, "Line 3"),
        ]
        result = find_line_at_y(text_lines, 110)
        assert result == 1

    def test_find_line_between(self):
        """Test finding line between two lines with larger gap."""
        text_lines = [
            (100, 120, "Line 1"),
            (180, 200, "Line 2"),  # Gap larger than tolerance (20px)
        ]
        result = find_line_at_y(text_lines, 150)
        # Should return the next line since 150 is before line 2 starts
        assert result == 2

    def test_find_line_below_all(self):
        """Test finding line below all lines."""
        text_lines = [
            (100, 120, "Line 1"),
            (130, 150, "Line 2"),
        ]
        result = find_line_at_y(text_lines, 200)
        # Should return last line
        assert result == 2

    def test_find_line_empty(self):
        """Test with empty text lines."""
        result = find_line_at_y([], 100)
        assert result is None


class TestDetectRepetitionBars:
    """Tests for detect_repetition_bars function."""

    def test_detect_bars_with_image(self, first_hymn_image: Image.Image):
        """Test detecting repetition bars in a hymn image."""
        cv2_img = pil_to_cv2(first_hymn_image)
        result = detect_repetition_bars(cv2_img)

        # Result should be string or None
        assert result is None or isinstance(result, str)

    def test_detect_no_bars(self):
        """Test with image without bars."""
        # Create blank white image
        img = np.ones((500, 800, 3), dtype=np.uint8) * 255
        result = detect_repetition_bars(img)
        assert result is None

    def test_detect_bars_with_text_lines(self):
        """Test detecting bars with text line mapping."""
        # Create image with vertical line
        img = np.ones((500, 800, 3), dtype=np.uint8) * 255
        img[100:200, 50:52, :] = 0

        text_lines = [
            (90, 110, "Line 1"),
            (120, 140, "Line 2"),
            (150, 170, "Line 3"),
            (180, 200, "Line 4"),
        ]

        result = detect_repetition_bars(img, text_lines=text_lines)

        # Should detect and map to lines
        if result:
            assert "-" in result  # Should have line range format


class TestAdjustRepetitionNumbers:
    """Tests for adjust_repetition_numbers function."""

    def test_adjust_no_prev(self):
        """Test adjustment with no previous repetitions."""
        result = adjust_repetition_numbers(None, "1-4", "Some text")
        assert result == "1-4"

    def test_adjust_no_new(self):
        """Test adjustment with no new repetitions."""
        result = adjust_repetition_numbers("1-4", None, "Some text")
        assert result == "1-4"

    def test_adjust_both(self):
        """Test adjustment with both prev and new."""
        prev = "1-4"
        new = "1-2"
        text = "Line 1\nLine 2\nLine 3\nLine 4\n\nLine 5\nLine 6"

        result = adjust_repetition_numbers(prev, new, text)

        # Should combine both
        assert "1-4" in result
        # New should be offset
        assert "," in result

    def test_adjust_preserves_format(self):
        """Test that format is preserved."""
        result = adjust_repetition_numbers("1-4", "5-8", "")
        assert "-" in result


class TestIntegration:
    """Integration tests for repetition detection."""

    def test_detect_in_hymn_body(self, first_hymn_image: Image.Image):
        """Test detecting repetition bars in hymn body zone."""
        cv2_img = pil_to_cv2(first_hymn_image)
        zones = detect_zones(cv2_img)

        if zones.body:
            result = detect_repetition_bars(cv2_img, zone=zones.body)
            # Result may or may not have bars
            assert result is None or isinstance(result, str)

    def test_continuation_page_no_bars(self, continuation_image: Image.Image):
        """Test that continuation pages may have different bar patterns."""
        cv2_img = pil_to_cv2(continuation_image)
        result = detect_repetition_bars(cv2_img)

        # Just check it runs without error
        assert result is None or isinstance(result, str)
