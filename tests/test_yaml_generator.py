"""Tests for YAML generator."""

import tempfile
from pathlib import Path

import pytest
import yaml

from hymn_ocr.models import Hymn, HymnBook
from hymn_ocr.yaml_generator import (
    generate_yaml,
    hymn_to_dict,
    hymnbook_to_dict,
    load_yaml,
    preview_yaml,
    save_yaml,
)


class TestHymnToDict:
    """Tests for hymn_to_dict function."""

    def test_hymn_to_dict_basic(self, minimal_hymn_data: dict):
        """Test converting minimal hymn to dict."""
        hymn = Hymn(**minimal_hymn_data)
        result = hymn_to_dict(hymn)

        assert result["number"] == 1
        assert result["title"] == "Test Hymn"
        assert result["text"] == "Some lyrics here"

    def test_hymn_to_dict_full(self, valid_hymn_data: dict):
        """Test converting full hymn to dict."""
        hymn = Hymn(**valid_hymn_data)
        result = hymn_to_dict(hymn)

        assert result["number"] == 1
        assert result["title"] == "Disciplina"
        assert result["original_number"] == 62
        assert result["style"] == "Valsa"
        assert result["offered_to"] == "João"
        assert result["repetitions"] == "1-4"
        assert result["received_at"] == "2020-01-18"

    def test_hymn_to_dict_omits_none(self, minimal_hymn_data: dict):
        """Test that None values are omitted."""
        hymn = Hymn(**minimal_hymn_data)
        result = hymn_to_dict(hymn)

        assert "original_number" not in result
        assert "style" not in result
        assert "offered_to" not in result


class TestHymnbookToDict:
    """Tests for hymnbook_to_dict function."""

    def test_hymnbook_to_dict(self, valid_hymnbook_data: dict):
        """Test converting hymnbook to dict."""
        hymnbook = HymnBook(**valid_hymnbook_data)
        result = hymnbook_to_dict(hymnbook)

        assert result["name"] == "Seleção Aniversário Ingrid"
        assert result["owner_name"] == "Ingrid"
        assert result["intro_name"] == "Introdução"
        assert "hymns" in result
        assert len(result["hymns"]) == 1

    def test_hymnbook_to_dict_no_intro(self, minimal_hymn_data: dict):
        """Test hymnbook without intro_name."""
        hymnbook = HymnBook(
            name="Test Book",
            owner_name="Owner",
            hymns=[Hymn(**minimal_hymn_data)],
        )
        result = hymnbook_to_dict(hymnbook)

        assert "intro_name" not in result


class TestGenerateYaml:
    """Tests for generate_yaml function."""

    def test_generate_yaml_valid(self, valid_hymnbook_data: dict):
        """Test generating valid YAML."""
        hymnbook = HymnBook(**valid_hymnbook_data)
        yaml_str = generate_yaml(hymnbook)

        assert isinstance(yaml_str, str)
        assert len(yaml_str) > 0

        # Verify it's valid YAML
        data = yaml.safe_load(yaml_str)
        assert data["name"] == "Seleção Aniversário Ingrid"

    def test_generate_yaml_structure(self, valid_hymnbook_data: dict):
        """Test YAML structure."""
        hymnbook = HymnBook(**valid_hymnbook_data)
        yaml_str = generate_yaml(hymnbook)

        data = yaml.safe_load(yaml_str)
        assert "name" in data
        assert "owner_name" in data
        assert "hymns" in data

    def test_generate_yaml_unicode(self):
        """Test that unicode is preserved."""
        hymn = Hymn(
            number=1,
            title="Canção com Acentos",
            text="Coração, Irmão, Mãe",
        )
        hymnbook = HymnBook(
            name="Hinário Português",
            owner_name="João",
            hymns=[hymn],
        )

        yaml_str = generate_yaml(hymnbook)

        assert "Coração" in yaml_str
        assert "Acentos" in yaml_str

    def test_generate_yaml_multiline(self):
        """Test multiline text handling."""
        hymn = Hymn(
            number=1,
            title="Test",
            text="Line 1\nLine 2\nLine 3",
        )
        hymnbook = HymnBook(name="Test", owner_name="Owner", hymns=[hymn])

        yaml_str = generate_yaml(hymnbook)

        # Multiline should use block scalar style
        assert "Line 1" in yaml_str
        assert "Line 2" in yaml_str


class TestSaveYaml:
    """Tests for save_yaml function."""

    def test_save_yaml_creates_file(self, valid_hymnbook_data: dict):
        """Test that save_yaml creates a file."""
        hymnbook = HymnBook(**valid_hymnbook_data)

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            output_path = Path(f.name)

        try:
            result = save_yaml(hymnbook, output_path)

            assert result == output_path
            assert output_path.exists()
            assert output_path.stat().st_size > 0
        finally:
            output_path.unlink(missing_ok=True)

    def test_save_yaml_content(self, valid_hymnbook_data: dict):
        """Test saved YAML content."""
        hymnbook = HymnBook(**valid_hymnbook_data)

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            output_path = Path(f.name)

        try:
            save_yaml(hymnbook, output_path)

            content = output_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)

            assert data["name"] == "Seleção Aniversário Ingrid"
        finally:
            output_path.unlink(missing_ok=True)


class TestLoadYaml:
    """Tests for load_yaml function."""

    def test_load_yaml(self, valid_hymnbook_data: dict):
        """Test loading YAML file."""
        hymnbook = HymnBook(**valid_hymnbook_data)

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            output_path = Path(f.name)

        try:
            save_yaml(hymnbook, output_path)
            loaded = load_yaml(output_path)

            assert loaded.name == hymnbook.name
            assert loaded.owner_name == hymnbook.owner_name
            assert len(loaded.hymns) == len(hymnbook.hymns)
        finally:
            output_path.unlink(missing_ok=True)

    def test_load_yaml_hymns(self, valid_hymnbook_data: dict):
        """Test that loaded hymns are correct."""
        hymnbook = HymnBook(**valid_hymnbook_data)

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            output_path = Path(f.name)

        try:
            save_yaml(hymnbook, output_path)
            loaded = load_yaml(output_path)

            assert loaded.hymns[0].number == hymnbook.hymns[0].number
            assert loaded.hymns[0].title == hymnbook.hymns[0].title
        finally:
            output_path.unlink(missing_ok=True)


class TestPreviewYaml:
    """Tests for preview_yaml function."""

    def test_preview_yaml(self, minimal_hymn_data: dict):
        """Test preview generation."""
        hymns = [
            Hymn(**{**minimal_hymn_data, "number": i, "title": f"Hymn {i}"})
            for i in range(1, 11)
        ]
        hymnbook = HymnBook(name="Test", owner_name="Owner", hymns=hymns)

        preview = preview_yaml(hymnbook, max_hymns=3)

        # Should contain first 3 hymns
        assert "Hymn 1" in preview
        assert "Hymn 2" in preview
        assert "Hymn 3" in preview

        # Should indicate more hymns
        assert "more hymns" in preview

    def test_preview_yaml_all_hymns(self, minimal_hymn_data: dict):
        """Test preview with fewer hymns than max."""
        hymns = [Hymn(**minimal_hymn_data)]
        hymnbook = HymnBook(name="Test", owner_name="Owner", hymns=hymns)

        preview = preview_yaml(hymnbook, max_hymns=5)

        # Should not mention "more hymns"
        assert "more hymns" not in preview
