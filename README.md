# Hymn OCR

Convert PDF hymnals to YAML using OCR and computer vision.

## Installation

```bash
# System dependencies (macOS)
brew install poppler tesseract tesseract-lang

# Python package
poetry install
```

## Usage

```bash
# Convert PDF to YAML
hymn-ocr convert input.pdf -o output.yaml

# Preview without saving
hymn-ocr convert input.pdf --preview

# Debug mode
hymn-ocr convert input.pdf --debug
```

## Development

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=hymn_ocr --cov-report=html
```
