"""Tests for regex parser."""

import pytest

from hymn_ocr.parser import (
    ParsedHeader,
    ParsedMetadata,
    clean_body_text,
    extract_page_number,
    has_date_pattern,
    has_header_pattern,
    parse_date,
    parse_header,
    parse_instructions,
    parse_metadata,
    parse_offered_to,
    parse_style,
)


class TestParseHeader:
    """Tests for parse_header function."""

    def test_parse_header_full(self):
        """Test parsing header with all parts."""
        result = parse_header("01. Disciplina (62)")
        assert result is not None
        assert result.number == 1
        assert result.title == "Disciplina"
        assert result.original_number == 62

    def test_parse_header_no_original(self):
        """Test parsing header without original number."""
        result = parse_header("05. Luz Divina")
        assert result is not None
        assert result.number == 5
        assert result.title == "Luz Divina"
        assert result.original_number is None

    def test_parse_header_multiword(self):
        """Test parsing header with multi-word title."""
        result = parse_header("10. Santa Maria dos Céus (123)")
        assert result is not None
        assert result.number == 10
        assert result.title == "Santa Maria dos Céus"
        assert result.original_number == 123

    def test_parse_header_two_digits(self):
        """Test parsing header with two-digit number."""
        result = parse_header("25. Hino Vinte e Cinco")
        assert result is not None
        assert result.number == 25

    def test_parse_header_invalid(self):
        """Test parsing invalid header."""
        result = parse_header("texto qualquer")
        assert result is None

    def test_parse_header_empty(self):
        """Test parsing empty string."""
        result = parse_header("")
        assert result is None

    def test_parse_header_none(self):
        """Test parsing None."""
        result = parse_header(None)
        assert result is None

    def test_parse_header_with_extra_whitespace(self):
        """Test parsing header with extra whitespace."""
        result = parse_header("  03.   Título Com Espaços   (45)  ")
        assert result is not None
        assert result.number == 3
        assert result.title == "Título Com Espaços"
        assert result.original_number == 45


class TestParseDate:
    """Tests for parse_date function."""

    def test_parse_date_valid(self):
        """Test parsing valid date."""
        result = parse_date("(18/01/2020)")
        assert result == "2020-01-18"

    def test_parse_date_in_text(self):
        """Test parsing date embedded in text."""
        result = parse_date("Final (25/12/2021) aqui")
        assert result == "2021-12-25"

    def test_parse_date_invalid(self):
        """Test parsing text without date."""
        result = parse_date("texto sem data")
        assert result is None

    def test_parse_date_empty(self):
        """Test parsing empty string."""
        result = parse_date("")
        assert result is None

    def test_parse_date_none(self):
        """Test parsing None."""
        result = parse_date(None)
        assert result is None

    def test_parse_date_multiple_dates(self):
        """Test parsing text with multiple dates (returns first)."""
        result = parse_date("(01/01/2020) e (31/12/2020)")
        assert result == "2020-01-01"


class TestParseOfferedTo:
    """Tests for parse_offered_to function."""

    def test_parse_offered_to_simple(self):
        """Test parsing simple offering."""
        result = parse_offered_to("Ofertado a João")
        assert result == "João"

    def test_parse_offered_to_with_style(self):
        """Test parsing offering with style."""
        result = parse_offered_to("Ofertado a Maria - Valsa")
        assert result == "Maria"

    def test_parse_offered_to_ao(self):
        """Test parsing 'Ofertado ao'."""
        result = parse_offered_to("Ofertado ao Pedro")
        assert result == "Pedro"

    def test_parse_offered_to_a_accent(self):
        """Test parsing 'Ofertado à'."""
        result = parse_offered_to("Ofertado à Ana")
        assert result == "Ana"

    def test_parse_offered_to_full_name(self):
        """Test parsing full name."""
        result = parse_offered_to("Ofertado a Maria da Silva")
        assert result == "Maria da Silva"

    def test_parse_offered_to_lowercase(self):
        """Test parsing lowercase 'ofertado'."""
        result = parse_offered_to("ofertado a josé")
        assert result == "josé"

    def test_parse_offered_to_not_found(self):
        """Test parsing text without offering."""
        result = parse_offered_to("Texto sem oferecimento")
        assert result is None

    def test_parse_offered_to_empty(self):
        """Test parsing empty string."""
        result = parse_offered_to("")
        assert result is None


class TestParseStyle:
    """Tests for parse_style function."""

    def test_parse_style_valsa(self):
        """Test detecting Valsa."""
        result = parse_style("Texto - Valsa")
        assert result == "Valsa"

    def test_parse_style_marcha(self):
        """Test detecting Marcha."""
        result = parse_style("Texto - Marcha")
        assert result == "Marcha"

    def test_parse_style_mazurca(self):
        """Test detecting Mazurca."""
        result = parse_style("Texto - Mazurca")
        assert result == "Mazurca"

    def test_parse_style_bolero(self):
        """Test detecting Bolero."""
        result = parse_style("Texto - Bolero")
        assert result == "Bolero"

    def test_parse_style_case_insensitive(self):
        """Test case insensitive detection."""
        result = parse_style("Texto - VALSA")
        assert result == "Valsa"

    def test_parse_style_none(self):
        """Test text without style."""
        result = parse_style("Texto sem estilo")
        assert result is None

    def test_parse_style_empty(self):
        """Test empty string."""
        result = parse_style("")
        assert result is None


class TestParseInstructions:
    """Tests for parse_instructions function."""

    def test_parse_instructions_em_pe(self):
        """Test detecting 'Em pé'."""
        result = parse_instructions("Em pé")
        assert result == "Em pé"

    def test_parse_instructions_sem_instrumentos(self):
        """Test detecting 'sem instrumentos'."""
        result = parse_instructions("Sem instrumentos")
        assert result == "sem instrumentos"

    def test_parse_instructions_sentados(self):
        """Test detecting 'Sentados'."""
        result = parse_instructions("Sentados")
        assert result == "Sentados"

    def test_parse_instructions_multiple(self):
        """Test detecting multiple instructions."""
        result = parse_instructions("Em pé, sem instrumentos")
        assert "Em pé" in result
        assert "sem instrumentos" in result

    def test_parse_instructions_none(self):
        """Test text without instructions."""
        result = parse_instructions("Texto normal")
        assert result is None

    def test_parse_instructions_empty(self):
        """Test empty string."""
        result = parse_instructions("")
        assert result is None


class TestParseMetadata:
    """Tests for parse_metadata function."""

    def test_parse_metadata_complete(self):
        """Test parsing complete metadata."""
        result = parse_metadata("Ofertado a Max - Valsa, Em pé")
        assert result.offered_to == "Max"
        assert result.style == "Valsa"
        assert "Em pé" in result.extra_instructions

    def test_parse_metadata_partial(self):
        """Test parsing partial metadata."""
        result = parse_metadata("Ofertado a João")
        assert result.offered_to == "João"
        assert result.style is None
        assert result.extra_instructions is None

    def test_parse_metadata_empty(self):
        """Test parsing empty string."""
        result = parse_metadata("")
        assert result.offered_to is None
        assert result.style is None
        assert result.extra_instructions is None


class TestExtractPageNumber:
    """Tests for extract_page_number function."""

    def test_extract_page_number(self):
        """Test extracting page number."""
        result = extract_page_number("Some text\n\n42")
        assert result == 42

    def test_extract_page_number_single_digit(self):
        """Test extracting single digit page number."""
        result = extract_page_number("Text\n1")
        assert result == 1

    def test_extract_page_number_not_found(self):
        """Test when no page number present."""
        result = extract_page_number("Just text here")
        assert result is None

    def test_extract_page_number_empty(self):
        """Test empty string."""
        result = extract_page_number("")
        assert result is None


class TestCleanBodyText:
    """Tests for clean_body_text function."""

    def test_clean_body_text_basic(self):
        """Test basic text cleaning."""
        text = "Line 1\nLine 2\nLine 3"
        result = clean_body_text(text)
        assert result == "Line 1\nLine 2\nLine 3"

    def test_clean_body_text_removes_page_numbers(self):
        """Test that standalone numbers are removed."""
        text = "Line 1\nLine 2\n42\nLine 3"
        result = clean_body_text(text)
        assert "42" not in result

    def test_clean_body_text_preserves_stanza_breaks(self):
        """Test that double newlines are preserved."""
        text = "Stanza 1\n\nStanza 2"
        result = clean_body_text(text)
        assert "\n\n" in result

    def test_clean_body_text_normalizes_multiple_blanks(self):
        """Test that triple+ newlines are normalized."""
        text = "Line 1\n\n\n\nLine 2"
        result = clean_body_text(text)
        assert "\n\n\n" not in result
        assert "\n\n" in result

    def test_clean_body_text_empty(self):
        """Test empty string."""
        result = clean_body_text("")
        assert result == ""

    def test_clean_body_text_strips(self):
        """Test that whitespace is stripped."""
        text = "  \n  Text  \n  "
        result = clean_body_text(text)
        assert result == "Text"

    def test_clean_body_text_removes_symbol_xx(self):
        """Test that XX symbol artifacts are removed."""
        text = "Line 1\nLine 2\nXX\nLine 3"
        result = clean_body_text(text)
        assert "XX" not in result
        assert "Line 1" in result
        assert "Line 3" in result

    def test_clean_body_text_removes_symbol_wc(self):
        """Test that WC x symbol artifacts are removed."""
        text = "Line 1\nWC x\nLine 2"
        result = clean_body_text(text)
        assert "WC" not in result

    def test_clean_body_text_removes_symbol_cc(self):
        """Test that CC x symbol artifacts are removed."""
        text = "Line 1\nCC x\nLine 2"
        result = clean_body_text(text)
        assert "CC" not in result

    def test_clean_body_text_removes_dates(self):
        """Test that standalone dates are removed."""
        text = "Line 1\nLine 2\n(18/01/2020)"
        result = clean_body_text(text)
        assert "(18/01/2020)" not in result

    def test_clean_body_text_removes_repetition_markers(self):
        """Test that | markers are removed from line starts."""
        text = "| Line 1\n| Line 2\nLine 3"
        result = clean_body_text(text)
        assert "|" not in result
        assert "Line 1" in result
        assert "Line 2" in result

    def test_clean_body_text_removes_instruction_lines(self):
        """Test that standalone instruction lines are removed."""
        text = "sem instrumentos\nLine 1\nLine 2"
        result = clean_body_text(text)
        assert "sem instrumentos" not in result
        assert "Line 1" in result

    def test_clean_body_text_removes_ocr_noise(self):
        """Test that OCR noise like (NOINAIININN is removed."""
        text = "Line 1\n(NOINAIININN\nLine 2"
        result = clean_body_text(text)
        assert "NOINAIININN" not in result
        assert "Line 1" in result
        assert "Line 2" in result

    def test_clean_body_text_removes_single_char(self):
        """Test that single character lines are removed."""
        text = "Line 1\no\nLine 2"
        result = clean_body_text(text)
        # Check single 'o' is removed but lines are kept
        lines = result.split("\n")
        assert "o" not in lines
        assert "Line 1" in result
        assert "Line 2" in result

    def test_clean_body_text_removes_gibberish(self):
        """Test that gibberish lines are removed."""
        text = "Line 1\nNOIALL\nLine 2"
        result = clean_body_text(text)
        assert "NOIALL" not in result
        assert "Line 1" in result


class TestHasPatterns:
    """Tests for pattern detection functions."""

    def test_has_header_pattern_true(self):
        """Test header pattern detection."""
        assert has_header_pattern("01. Título") is True

    def test_has_header_pattern_false(self):
        """Test header pattern not present."""
        assert has_header_pattern("Just text") is False

    def test_has_date_pattern_true(self):
        """Test date pattern detection."""
        assert has_date_pattern("(01/01/2020)") is True

    def test_has_date_pattern_false(self):
        """Test date pattern not present."""
        assert has_date_pattern("No date here") is False
