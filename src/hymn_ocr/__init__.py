"""Hymn OCR - Convert PDF hymnals to YAML using OCR and computer vision."""

from hymn_ocr.models import Hymn, HymnBook, PageType
from hymn_ocr.pipeline import pdf_to_hymnbook
from hymn_ocr.yaml_generator import generate_yaml, save_yaml

__version__ = "0.1.0"
__all__ = [
    "Hymn",
    "HymnBook",
    "PageType",
    "pdf_to_hymnbook",
    "generate_yaml",
    "save_yaml",
]
