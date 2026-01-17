"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from hymn_ocr.models import Hymn, HymnBook, PageData, PageType


class TestPageType:
    """Tests for PageType enum."""

    def test_page_type_values(self):
        """Test all PageType enum values."""
        assert PageType.COVER.value == "cover"
        assert PageType.NEW_HYMN.value == "new_hymn"
        assert PageType.CONTINUATION.value == "continuation"
        assert PageType.BLANK.value == "blank"

    def test_page_type_from_string(self):
        """Test creating PageType from string."""
        assert PageType("cover") == PageType.COVER
        assert PageType("new_hymn") == PageType.NEW_HYMN


class TestHymn:
    """Tests for Hymn model."""

    def test_hymn_valid(self, valid_hymn_data: dict):
        """Test creating a valid hymn with all fields."""
        hymn = Hymn(**valid_hymn_data)
        assert hymn.number == 1
        assert hymn.title == "Disciplina"
        assert hymn.original_number == 62
        assert hymn.style == "Valsa"
        assert hymn.offered_to == "João"
        assert hymn.extra_instructions == "Em pé"
        assert hymn.repetitions == "1-4"
        assert hymn.received_at == "2020-01-18"

    def test_hymn_minimal(self, minimal_hymn_data: dict):
        """Test creating a hymn with only required fields."""
        hymn = Hymn(**minimal_hymn_data)
        assert hymn.number == 1
        assert hymn.title == "Test Hymn"
        assert hymn.text == "Some lyrics here"
        assert hymn.original_number is None
        assert hymn.style is None
        assert hymn.offered_to is None
        assert hymn.extra_instructions is None
        assert hymn.repetitions is None
        assert hymn.received_at is None

    def test_hymn_invalid_number_zero(self):
        """Test that number must be > 0."""
        with pytest.raises(ValidationError) as exc_info:
            Hymn(number=0, title="Test", text="Text")
        assert "greater than 0" in str(exc_info.value).lower()

    def test_hymn_invalid_number_negative(self):
        """Test that negative numbers are rejected."""
        with pytest.raises(ValidationError):
            Hymn(number=-1, title="Test", text="Text")

    def test_hymn_empty_title(self):
        """Test that empty title is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Hymn(number=1, title="", text="Text")
        assert "min_length" in str(exc_info.value).lower() or "string" in str(
            exc_info.value
        ).lower()

    def test_hymn_empty_text(self):
        """Test that empty text is rejected."""
        with pytest.raises(ValidationError):
            Hymn(number=1, title="Test", text="")

    def test_hymn_whitespace_title_stripped(self):
        """Test that whitespace is stripped from title."""
        hymn = Hymn(number=1, title="  Test Title  ", text="Text")
        assert hymn.title == "Test Title"

    def test_hymn_whitespace_text_stripped(self):
        """Test that whitespace is stripped from text."""
        hymn = Hymn(number=1, title="Test", text="  Some text  ")
        assert hymn.text == "Some text"

    def test_hymn_invalid_date_format(self):
        """Test that invalid date format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Hymn(number=1, title="Test", text="Text", received_at="18/01/2020")
        assert "date" in str(exc_info.value).lower()

    def test_hymn_valid_date_format(self):
        """Test that YYYY-MM-DD format is accepted."""
        hymn = Hymn(number=1, title="Test", text="Text", received_at="2020-01-18")
        assert hymn.received_at == "2020-01-18"

    def test_hymn_invalid_original_number_zero(self):
        """Test that original_number must be > 0 if provided."""
        with pytest.raises(ValidationError):
            Hymn(number=1, title="Test", text="Text", original_number=0)

    def test_hymn_multiline_text(self):
        """Test hymn with multiline text."""
        text = "Line 1\nLine 2\nLine 3"
        hymn = Hymn(number=1, title="Test", text=text)
        assert "\n" in hymn.text
        assert hymn.text == text


class TestHymnBook:
    """Tests for HymnBook model."""

    def test_hymnbook_valid(self, valid_hymnbook_data: dict):
        """Test creating a valid hymn book."""
        book = HymnBook(**valid_hymnbook_data)
        assert book.name == "Seleção Aniversário Ingrid"
        assert book.owner_name == "Ingrid"
        assert book.intro_name == "Introdução"
        assert len(book.hymns) == 1

    def test_hymnbook_minimal(self, minimal_hymn_data: dict):
        """Test hymn book without intro_name."""
        book = HymnBook(
            name="Test Book",
            owner_name="Test Owner",
            hymns=[Hymn(**minimal_hymn_data)],
        )
        assert book.name == "Test Book"
        assert book.intro_name is None

    def test_hymnbook_empty_hymns(self):
        """Test that empty hymns list is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            HymnBook(name="Test", owner_name="Owner", hymns=[])
        assert "min_length" in str(exc_info.value).lower() or "list" in str(
            exc_info.value
        ).lower()

    def test_hymnbook_empty_name(self, minimal_hymn_data: dict):
        """Test that empty name is rejected."""
        with pytest.raises(ValidationError):
            HymnBook(name="", owner_name="Owner", hymns=[Hymn(**minimal_hymn_data)])

    def test_hymnbook_empty_owner(self, minimal_hymn_data: dict):
        """Test that empty owner_name is rejected."""
        with pytest.raises(ValidationError):
            HymnBook(name="Test", owner_name="", hymns=[Hymn(**minimal_hymn_data)])

    def test_hymnbook_whitespace_stripped(self, minimal_hymn_data: dict):
        """Test that whitespace is stripped from name and owner."""
        book = HymnBook(
            name="  Test Book  ",
            owner_name="  Test Owner  ",
            hymns=[Hymn(**minimal_hymn_data)],
        )
        assert book.name == "Test Book"
        assert book.owner_name == "Test Owner"

    def test_hymnbook_multiple_hymns(self, minimal_hymn_data: dict):
        """Test hymn book with multiple hymns."""
        hymns = [
            Hymn(**{**minimal_hymn_data, "number": i, "title": f"Hymn {i}"})
            for i in range(1, 6)
        ]
        book = HymnBook(name="Test", owner_name="Owner", hymns=hymns)
        assert len(book.hymns) == 5


class TestPageData:
    """Tests for PageData model."""

    def test_page_data_valid(self):
        """Test creating valid page data."""
        data = PageData(
            page_number=2,
            page_type=PageType.NEW_HYMN,
            header_text="01. Disciplina (62)",
            body_text="Santa Maria\nO caminho da disciplina",
        )
        assert data.page_number == 2
        assert data.page_type == PageType.NEW_HYMN

    def test_page_data_continuation(self):
        """Test page data for continuation page."""
        data = PageData(
            page_number=17,
            page_type=PageType.CONTINUATION,
            body_text="Continuation text",
        )
        assert data.page_type == PageType.CONTINUATION
        assert data.header_text is None

    def test_page_data_invalid_page_number(self):
        """Test that page_number must be >= 1."""
        with pytest.raises(ValidationError):
            PageData(page_number=0, page_type=PageType.BLANK)
