"""Regex parsing for hymn text extraction."""

import re
from dataclasses import dataclass
from typing import Optional


# Regex patterns
# Header: "NN. Título (original)" or "NN. Título"
HEADER_PATTERN = re.compile(r"^(\d+)\.\s+(.+?)(?:\s*\((\d+)\))?\s*$", re.MULTILINE)

# Date in DD/MM/YYYY format
DATE_PATTERN = re.compile(r"\((\d{2})/(\d{2})/(\d{4})\)")

# Offered to pattern: "Ofertado a/ao/à Nome"
OFFERED_PATTERN = re.compile(
    r"[Oo]fertado\s+(?:a|ao|à)\s+(.+?)(?:\s*[-–—]\s*|\s*$)", re.IGNORECASE
)

# Musical styles
STYLE_KEYWORDS = ["Valsa", "Marcha", "Mazurca", "Bolero"]

# Extra instructions pattern
INSTRUCTION_PATTERN = re.compile(
    r"([Ee]m pé|[Ss]em instrumentos|[Ss]entados?)", re.IGNORECASE
)

# Page number at bottom (standalone number)
PAGE_NUMBER_PATTERN = re.compile(r"^\s*(\d+)\s*$", re.MULTILINE)


@dataclass
class ParsedHeader:
    """Parsed header information."""

    number: int
    title: str
    original_number: Optional[int] = None


@dataclass
class ParsedMetadata:
    """Parsed metadata information."""

    offered_to: Optional[str] = None
    style: Optional[str] = None
    extra_instructions: Optional[str] = None


def parse_header(text: str) -> Optional[ParsedHeader]:
    """
    Parse hymn header to extract number, title, and original number.

    Args:
        text: Header text from OCR.

    Returns:
        ParsedHeader if found, None otherwise.

    Examples:
        "01. Disciplina (62)" -> ParsedHeader(1, "Disciplina", 62)
        "05. Luz Divina" -> ParsedHeader(5, "Luz Divina", None)
        "10. Santa Maria dos Céus (123)" -> ParsedHeader(10, "Santa Maria dos Céus", 123)
    """
    if not text:
        return None

    # Clean the text
    text = text.strip()

    # Try to match the header pattern
    match = HEADER_PATTERN.search(text)
    if match:
        number = int(match.group(1))
        title = match.group(2).strip()
        original_str = match.group(3)
        original_number = int(original_str) if original_str else None

        return ParsedHeader(
            number=number,
            title=title,
            original_number=original_number,
        )

    return None


def parse_date(text: str) -> Optional[str]:
    """
    Parse date from text and return in YYYY-MM-DD format.

    Args:
        text: Text containing a date.

    Returns:
        Date in YYYY-MM-DD format, or None if not found.

    Examples:
        "(18/01/2020)" -> "2020-01-18"
        "Final (25/12/2021) aqui" -> "2021-12-25"
    """
    if not text:
        return None

    match = DATE_PATTERN.search(text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"

    return None


def parse_offered_to(text: str) -> Optional[str]:
    """
    Parse the person the hymn is offered to.

    Args:
        text: Metadata text.

    Returns:
        Name of the person, or None if not found.

    Examples:
        "Ofertado a João" -> "João"
        "Ofertado a Maria - Valsa" -> "Maria"
        "Ofertado ao Pedro" -> "Pedro"
        "Ofertado à Ana" -> "Ana"
    """
    if not text:
        return None

    match = OFFERED_PATTERN.search(text)
    if match:
        name = match.group(1).strip()
        # Remove any trailing style keywords
        for style in STYLE_KEYWORDS:
            if name.lower().endswith(style.lower()):
                name = name[: -len(style)].strip()
                # Remove trailing dash if present
                name = name.rstrip("-–—").strip()
        return name if name else None

    return None


def parse_style(text: str) -> Optional[str]:
    """
    Parse the musical style from text.

    Args:
        text: Text that may contain a style keyword.

    Returns:
        Style name, or None if not found.

    Examples:
        "Texto - Valsa" -> "Valsa"
        "Texto - Marcha" -> "Marcha"
        "Texto sem estilo" -> None
    """
    if not text:
        return None

    text_lower = text.lower()
    for style in STYLE_KEYWORDS:
        if style.lower() in text_lower:
            return style

    return None


def parse_instructions(text: str) -> Optional[str]:
    """
    Parse extra instructions from text.

    Args:
        text: Text that may contain instructions.

    Returns:
        Comma-separated instructions, or None if not found.

    Examples:
        "Em pé, sem instrumentos" -> "Em pé, sem instrumentos"
        "Sentados" -> "Sentados"
    """
    if not text:
        return None

    matches = INSTRUCTION_PATTERN.findall(text)
    if matches:
        # Normalize case
        normalized = []
        for match in matches:
            match_lower = match.lower()
            if "em pé" in match_lower:
                normalized.append("Em pé")
            elif "sem instrumentos" in match_lower:
                normalized.append("sem instrumentos")
            elif "sentado" in match_lower:
                normalized.append("Sentados")
        return ", ".join(normalized) if normalized else None

    return None


def parse_metadata(text: str) -> ParsedMetadata:
    """
    Parse all metadata from text.

    Args:
        text: Metadata text from OCR.

    Returns:
        ParsedMetadata with all extracted fields.

    Examples:
        "Ofertado a Max - Valsa" -> ParsedMetadata(offered_to="Max", style="Valsa")
        "Ofertado a X - Em pé, sem instrumentos" -> ParsedMetadata(offered_to="X", extra_instructions="Em pé, sem instrumentos")
    """
    return ParsedMetadata(
        offered_to=parse_offered_to(text),
        style=parse_style(text),
        extra_instructions=parse_instructions(text),
    )


def extract_page_number(text: str) -> Optional[int]:
    """
    Extract page number from footer text.

    Args:
        text: Footer text from OCR.

    Returns:
        Page number, or None if not found.
    """
    if not text:
        return None

    # Look for standalone number at end of text
    lines = text.strip().split("\n")
    if lines:
        last_line = lines[-1].strip()
        match = PAGE_NUMBER_PATTERN.match(last_line)
        if match:
            return int(match.group(1))

    return None


def clean_body_text(text: str) -> str:
    """
    Clean hymn body text.

    - Remove page numbers
    - Normalize whitespace
    - Preserve stanza breaks (double newlines)

    Args:
        text: Raw body text from OCR.

    Returns:
        Cleaned body text.
    """
    if not text:
        return ""

    # Split into lines
    lines = text.split("\n")

    # Remove lines that are just numbers (page numbers, stanza markers)
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Keep empty lines (stanza breaks) and non-number lines
        if not stripped or not stripped.isdigit():
            cleaned_lines.append(stripped)

    # Join and normalize multiple blank lines
    result = "\n".join(cleaned_lines)

    # Normalize multiple consecutive blank lines to double
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")

    return result.strip()


def has_header_pattern(text: str) -> bool:
    """
    Check if text contains a header pattern.

    Args:
        text: Text to check.

    Returns:
        True if header pattern is found.
    """
    if not text:
        return False
    return bool(HEADER_PATTERN.search(text))


def has_date_pattern(text: str) -> bool:
    """
    Check if text contains a date pattern.

    Args:
        text: Text to check.

    Returns:
        True if date pattern is found.
    """
    if not text:
        return False
    return bool(DATE_PATTERN.search(text))
