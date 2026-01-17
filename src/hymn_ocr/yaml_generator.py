"""YAML generation for hymn book output."""

from pathlib import Path
from typing import Optional, Union

import yaml

from hymn_ocr.models import Hymn, HymnBook


class LiteralStr(str):
    """String that should be rendered as a literal block in YAML."""

    pass


def literal_str_representer(dumper: yaml.Dumper, data: LiteralStr) -> yaml.Node:
    """Custom representer for literal block strings."""
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


# Register the custom representer
yaml.add_representer(LiteralStr, literal_str_representer)


def hymn_to_dict(hymn: Hymn) -> dict:
    """
    Convert a Hymn to a dictionary for YAML serialization.

    Args:
        hymn: Hymn object.

    Returns:
        Dictionary representation.
    """
    result = {
        "number": hymn.number,
        "title": hymn.title,
        "text": LiteralStr(hymn.text) if "\n" in hymn.text else hymn.text,
    }

    # Add optional fields only if they have values
    if hymn.original_number is not None:
        result["original_number"] = hymn.original_number
    if hymn.style:
        result["style"] = hymn.style
    if hymn.offered_to:
        result["offered_to"] = hymn.offered_to
    if hymn.extra_instructions:
        result["extra_instructions"] = hymn.extra_instructions
    if hymn.repetitions:
        result["repetitions"] = hymn.repetitions
    if hymn.received_at:
        result["received_at"] = hymn.received_at

    return result


def hymnbook_to_dict(hymnbook: HymnBook) -> dict:
    """
    Convert a HymnBook to a dictionary for YAML serialization.

    Args:
        hymnbook: HymnBook object.

    Returns:
        Dictionary representation.
    """
    result = {
        "name": hymnbook.name,
        "owner_name": hymnbook.owner_name,
    }

    if hymnbook.intro_name:
        result["intro_name"] = hymnbook.intro_name

    result["hymns"] = [hymn_to_dict(h) for h in hymnbook.hymns]

    return result


def generate_yaml(hymnbook: HymnBook) -> str:
    """
    Generate YAML string from a HymnBook.

    Args:
        hymnbook: HymnBook object to serialize.

    Returns:
        YAML string.
    """
    data = hymnbook_to_dict(hymnbook)

    return yaml.dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=1000,  # Prevent line wrapping
    )


def save_yaml(hymnbook: HymnBook, output_path: Union[str, Path]) -> Path:
    """
    Save a HymnBook to a YAML file.

    Args:
        hymnbook: HymnBook to save.
        output_path: Path to save the YAML file.

    Returns:
        Path to the saved file.
    """
    output_path = Path(output_path)

    yaml_content = generate_yaml(hymnbook)

    output_path.write_text(yaml_content, encoding="utf-8")

    return output_path


def load_yaml(input_path: Union[str, Path]) -> HymnBook:
    """
    Load a HymnBook from a YAML file.

    Args:
        input_path: Path to the YAML file.

    Returns:
        HymnBook object.
    """
    input_path = Path(input_path)

    content = input_path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    hymns = [Hymn(**h) for h in data.get("hymns", [])]

    return HymnBook(
        name=data["name"],
        owner_name=data["owner_name"],
        intro_name=data.get("intro_name"),
        hymns=hymns,
    )


def preview_yaml(hymnbook: HymnBook, max_hymns: int = 3) -> str:
    """
    Generate a preview of the YAML output.

    Args:
        hymnbook: HymnBook to preview.
        max_hymns: Maximum number of hymns to include.

    Returns:
        Preview YAML string.
    """
    # Create a copy with limited hymns
    preview_hymns = hymnbook.hymns[:max_hymns]
    preview_book = HymnBook(
        name=hymnbook.name,
        owner_name=hymnbook.owner_name,
        intro_name=hymnbook.intro_name,
        hymns=preview_hymns,
    )

    yaml_str = generate_yaml(preview_book)

    if len(hymnbook.hymns) > max_hymns:
        yaml_str += f"\n# ... and {len(hymnbook.hymns) - max_hymns} more hymns\n"

    return yaml_str
