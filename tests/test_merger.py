"""Tests for merger module."""

import pytest

from hymn_ocr.merger import (
    count_hymns_by_type,
    create_page_data_from_ocr,
    merge_multipage_hymns,
)
from hymn_ocr.models import Hymn, PageData, PageType


class TestMergeMultipageHymns:
    """Tests for merge_multipage_hymns function."""

    def test_merge_single_page(self):
        """Test merging a single-page hymn."""
        pages = [
            PageData(
                page_number=2,
                page_type=PageType.NEW_HYMN,
                body_text="Lyrics here",
                hymn_number=1,
                hymn_title="Test Hymn",
            )
        ]

        hymns = merge_multipage_hymns(pages)

        assert len(hymns) == 1
        assert hymns[0].number == 1
        assert hymns[0].title == "Test Hymn"
        assert hymns[0].text == "Lyrics here"

    def test_merge_two_pages(self):
        """Test merging a two-page hymn."""
        pages = [
            PageData(
                page_number=2,
                page_type=PageType.NEW_HYMN,
                body_text="First part",
                hymn_number=1,
                hymn_title="Test Hymn",
            ),
            PageData(
                page_number=3,
                page_type=PageType.CONTINUATION,
                body_text="Second part",
            ),
        ]

        hymns = merge_multipage_hymns(pages)

        assert len(hymns) == 1
        assert "First part" in hymns[0].text
        assert "Second part" in hymns[0].text

    def test_merge_multiple_hymns(self):
        """Test merging multiple single-page hymns."""
        pages = [
            PageData(
                page_number=2,
                page_type=PageType.NEW_HYMN,
                body_text="Hymn 1 text",
                hymn_number=1,
                hymn_title="Hymn One",
            ),
            PageData(
                page_number=3,
                page_type=PageType.NEW_HYMN,
                body_text="Hymn 2 text",
                hymn_number=2,
                hymn_title="Hymn Two",
            ),
            PageData(
                page_number=4,
                page_type=PageType.NEW_HYMN,
                body_text="Hymn 3 text",
                hymn_number=3,
                hymn_title="Hymn Three",
            ),
        ]

        hymns = merge_multipage_hymns(pages)

        assert len(hymns) == 3
        assert hymns[0].number == 1
        assert hymns[1].number == 2
        assert hymns[2].number == 3

    def test_merge_mixed(self):
        """Test merging mix of single and multi-page hymns."""
        pages = [
            PageData(
                page_number=2,
                page_type=PageType.NEW_HYMN,
                body_text="Hymn 1 part 1",
                hymn_number=1,
                hymn_title="Long Hymn",
            ),
            PageData(
                page_number=3,
                page_type=PageType.CONTINUATION,
                body_text="Hymn 1 part 2",
            ),
            PageData(
                page_number=4,
                page_type=PageType.NEW_HYMN,
                body_text="Hymn 2 text",
                hymn_number=2,
                hymn_title="Short Hymn",
            ),
        ]

        hymns = merge_multipage_hymns(pages)

        assert len(hymns) == 2
        assert "Hymn 1 part 1" in hymns[0].text
        assert "Hymn 1 part 2" in hymns[0].text
        assert hymns[1].text == "Hymn 2 text"

    def test_merge_preserves_date(self):
        """Test that date from continuation page is preserved."""
        pages = [
            PageData(
                page_number=2,
                page_type=PageType.NEW_HYMN,
                body_text="Part 1",
                hymn_number=1,
                hymn_title="Test",
            ),
            PageData(
                page_number=3,
                page_type=PageType.CONTINUATION,
                body_text="Part 2",
                received_at="2020-01-18",
            ),
        ]

        hymns = merge_multipage_hymns(pages)

        assert len(hymns) == 1
        assert hymns[0].received_at == "2020-01-18"

    def test_merge_empty_input(self):
        """Test merging empty list."""
        hymns = merge_multipage_hymns([])
        assert hymns == []

    def test_merge_skips_cover(self):
        """Test that cover pages are skipped."""
        pages = [
            PageData(page_number=1, page_type=PageType.COVER),
            PageData(
                page_number=2,
                page_type=PageType.NEW_HYMN,
                body_text="Lyrics",
                hymn_number=1,
                hymn_title="Test",
            ),
        ]

        hymns = merge_multipage_hymns(pages)

        assert len(hymns) == 1

    def test_merge_skips_blank(self):
        """Test that blank pages are skipped."""
        pages = [
            PageData(
                page_number=2,
                page_type=PageType.NEW_HYMN,
                body_text="Lyrics",
                hymn_number=1,
                hymn_title="Test",
            ),
            PageData(page_number=3, page_type=PageType.BLANK),
        ]

        hymns = merge_multipage_hymns(pages)

        assert len(hymns) == 1

    def test_merge_preserves_metadata(self):
        """Test that metadata is preserved."""
        pages = [
            PageData(
                page_number=2,
                page_type=PageType.NEW_HYMN,
                body_text="Lyrics",
                hymn_number=1,
                hymn_title="Test",
                original_number=42,
                offered_to="John",
                style="Valsa",
                extra_instructions="Em pé",
                repetitions="1-4",
            )
        ]

        hymns = merge_multipage_hymns(pages)

        assert hymns[0].original_number == 42
        assert hymns[0].offered_to == "John"
        assert hymns[0].style == "Valsa"
        assert hymns[0].extra_instructions == "Em pé"
        assert hymns[0].repetitions == "1-4"


class TestCreatePageDataFromOcr:
    """Tests for create_page_data_from_ocr helper."""

    def test_create_basic(self):
        """Test creating basic page data."""
        page = create_page_data_from_ocr(
            page_number=2,
            page_type=PageType.NEW_HYMN,
            body_text="Some text",
        )

        assert page.page_number == 2
        assert page.page_type == PageType.NEW_HYMN
        assert page.body_text == "Some text"

    def test_create_with_all_fields(self):
        """Test creating page data with all fields."""
        page = create_page_data_from_ocr(
            page_number=2,
            page_type=PageType.NEW_HYMN,
            header_text="01. Title",
            metadata_text="Ofertado a X",
            body_text="Lyrics",
            footer_text="(01/01/2020)",
            hymn_number=1,
            hymn_title="Title",
            original_number=42,
            offered_to="X",
            style="Valsa",
        )

        assert page.header_text == "01. Title"
        assert page.hymn_number == 1
        assert page.offered_to == "X"


class TestCountHymnsByType:
    """Tests for count_hymns_by_type function."""

    def test_count_types(self):
        """Test counting page types."""
        pages = [
            PageData(page_number=1, page_type=PageType.COVER),
            PageData(page_number=2, page_type=PageType.NEW_HYMN),
            PageData(page_number=3, page_type=PageType.CONTINUATION),
            PageData(page_number=4, page_type=PageType.NEW_HYMN),
            PageData(page_number=5, page_type=PageType.BLANK),
        ]

        counts = count_hymns_by_type(pages)

        assert counts["cover"] == 1
        assert counts["new_hymn"] == 2
        assert counts["continuation"] == 1
        assert counts["blank"] == 1

    def test_count_empty(self):
        """Test counting empty list."""
        counts = count_hymns_by_type([])

        assert counts["cover"] == 0
        assert counts["new_hymn"] == 0
