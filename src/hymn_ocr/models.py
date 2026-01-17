"""Pydantic models for hymn data structures."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PageType(str, Enum):
    """Type of page in the PDF."""

    COVER = "cover"
    NEW_HYMN = "new_hymn"
    CONTINUATION = "continuation"
    BLANK = "blank"


class Hymn(BaseModel):
    """A single hymn with all its metadata."""

    number: int = Field(..., gt=0, description="Hymn number in the collection")
    title: str = Field(..., min_length=1, description="Hymn title")
    text: str = Field(..., min_length=1, description="Hymn lyrics")
    original_number: Optional[int] = Field(
        None, gt=0, description="Original hymn number reference"
    )
    style: Optional[str] = Field(None, description="Musical style (Valsa, Marcha, etc.)")
    offered_to: Optional[str] = Field(None, description="Person the hymn is offered to")
    extra_instructions: Optional[str] = Field(
        None, description="Extra instructions (Em pé, Sem instrumentos, etc.)"
    )
    repetitions: Optional[str] = Field(
        None, description="Repetition markers (e.g., '1-4, 5-8')"
    )
    received_at: Optional[str] = Field(
        None, description="Date received in YYYY-MM-DD format"
    )

    @field_validator("title", "text")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace."""
        return v.strip()

    @field_validator("received_at")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate date is in YYYY-MM-DD format."""
        if v is None:
            return None
        import re

        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v


class HymnBook(BaseModel):
    """A collection of hymns."""

    name: str = Field(..., min_length=1, description="Name of the hymn book")
    owner_name: str = Field(..., min_length=1, description="Owner's name")
    intro_name: Optional[str] = Field(None, description="Introduction name")
    hymns: list[Hymn] = Field(..., min_length=1, description="List of hymns")

    @field_validator("name", "owner_name")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace."""
        return v.strip()


class PageData(BaseModel):
    """Processed data from a single page."""

    page_number: int = Field(..., ge=1, description="Page number in PDF")
    page_type: PageType = Field(..., description="Type of page")
    header_text: Optional[str] = Field(None, description="Header zone text")
    metadata_text: Optional[str] = Field(None, description="Metadata zone text")
    body_text: Optional[str] = Field(None, description="Body zone text")
    footer_text: Optional[str] = Field(None, description="Footer zone text")
    repetitions: Optional[str] = Field(None, description="Detected repetition bars")

    # Parsed fields (filled after parsing)
    hymn_number: Optional[int] = Field(None, description="Parsed hymn number")
    hymn_title: Optional[str] = Field(None, description="Parsed hymn title")
    original_number: Optional[int] = Field(None, description="Parsed original number")
    offered_to: Optional[str] = Field(None, description="Parsed offered_to")
    style: Optional[str] = Field(None, description="Parsed style")
    extra_instructions: Optional[str] = Field(None, description="Parsed instructions")
    received_at: Optional[str] = Field(None, description="Parsed date")
