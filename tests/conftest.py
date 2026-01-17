"""Shared test fixtures."""

from pathlib import Path

import pytest
from PIL import Image

# Base paths
TESTS_DIR = Path(__file__).parent
FIXTURES_DIR = TESTS_DIR / "fixtures"
IMAGES_DIR = FIXTURES_DIR / "images"

# Sample PDF path (from hymn_pdf_generator)
SAMPLE_PDF_PATH = (
    Path(__file__).parent.parent.parent
    / "hymn_pdf_generator"
    / "example"
    / "selecao_aniversario_ingrid.pdf"
)

SAMPLE_YAML_PATH = (
    Path(__file__).parent.parent.parent
    / "hymn_pdf_generator"
    / "example"
    / "selecao_aniversario_ingrid.yaml"
)


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def images_dir() -> Path:
    """Path to test images directory."""
    return IMAGES_DIR


@pytest.fixture
def sample_pdf_path() -> Path:
    """Path to sample PDF file."""
    if not SAMPLE_PDF_PATH.exists():
        pytest.skip(f"Sample PDF not found: {SAMPLE_PDF_PATH}")
    return SAMPLE_PDF_PATH


@pytest.fixture
def sample_yaml_path() -> Path:
    """Path to sample YAML file."""
    if not SAMPLE_YAML_PATH.exists():
        pytest.skip(f"Sample YAML not found: {SAMPLE_YAML_PATH}")
    return SAMPLE_YAML_PATH


@pytest.fixture
def cover_image(images_dir: Path) -> Image.Image:
    """Load cover page image (page 1)."""
    path = images_dir / "page_01.png"
    if not path.exists():
        pytest.skip(f"Cover image not found: {path}")
    return Image.open(path)


@pytest.fixture
def first_hymn_image(images_dir: Path) -> Image.Image:
    """Load first hymn page image (page 2)."""
    path = images_dir / "page_02.png"
    if not path.exists():
        pytest.skip(f"First hymn image not found: {path}")
    return Image.open(path)


@pytest.fixture
def second_hymn_image(images_dir: Path) -> Image.Image:
    """Load second hymn page image (page 3)."""
    path = images_dir / "page_03.png"
    if not path.exists():
        pytest.skip(f"Second hymn image not found: {path}")
    return Image.open(path)


@pytest.fixture
def multipage_start_image(images_dir: Path) -> Image.Image:
    """Load multi-page hymn start image (page 16)."""
    path = images_dir / "page_16.png"
    if not path.exists():
        pytest.skip(f"Multi-page start image not found: {path}")
    return Image.open(path)


@pytest.fixture
def continuation_image(images_dir: Path) -> Image.Image:
    """Load continuation page image (page 17)."""
    path = images_dir / "page_17.png"
    if not path.exists():
        pytest.skip(f"Continuation image not found: {path}")
    return Image.open(path)


@pytest.fixture
def last_hymn_image(images_dir: Path) -> Image.Image:
    """Load last hymn page image (page 50)."""
    path = images_dir / "page_50.png"
    if not path.exists():
        pytest.skip(f"Last hymn image not found: {path}")
    return Image.open(path)


@pytest.fixture
def valid_hymn_data() -> dict:
    """Valid hymn data for testing."""
    return {
        "number": 1,
        "title": "Disciplina",
        "text": "Santa Maria\nO caminho da disciplina\nVem chegando noite e dia",
        "original_number": 62,
        "style": "Valsa",
        "offered_to": "João",
        "extra_instructions": "Em pé",
        "repetitions": "1-4",
        "received_at": "2020-01-18",
    }


@pytest.fixture
def minimal_hymn_data() -> dict:
    """Minimal valid hymn data (only required fields)."""
    return {
        "number": 1,
        "title": "Test Hymn",
        "text": "Some lyrics here",
    }


@pytest.fixture
def valid_hymnbook_data(valid_hymn_data: dict) -> dict:
    """Valid hymn book data for testing."""
    return {
        "name": "Seleção Aniversário Ingrid",
        "owner_name": "Ingrid",
        "intro_name": "Introdução",
        "hymns": [valid_hymn_data],
    }
