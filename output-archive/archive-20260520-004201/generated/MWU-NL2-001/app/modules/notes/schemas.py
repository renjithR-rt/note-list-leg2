from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, ConfigDict


class NoteCreate(BaseModel):
    """Input schema for POST /notes.

    Validator execution order (Pydantic v2):
      1. strip_whitespace  (mode='before') — BR-BACKEND-006: strip before any check
      2. content_not_empty (mode='after')  — BR-BACKEND-001: reject empty after strip
      3. Pydantic built-in max_length=500  — BR-BACKEND-002: 500-character limit
    """

    content: str = Field(
        ...,
        max_length=500,          # BR-BACKEND-002: character-length limit (Python len())
        description="Note content — 1 to 500 characters after stripping whitespace.",
    )

    # BR-BACKEND-006: strip leading/trailing whitespace before any validation
    @field_validator("content", mode="before")
    @classmethod
    def strip_whitespace(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v

    # BR-BACKEND-001: reject content that is empty after stripping
    @field_validator("content", mode="after")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Note cannot be empty")
        return v

    model_config = ConfigDict(populate_by_name=True)


class NoteRead(BaseModel):
    """Response schema for a single note (used in list and create responses).

    created_at is returned as a timezone-aware datetime.
    Pydantic serialises datetime to ISO 8601 automatically.
    Frontend is responsible for display formatting — BR-RISK-004.
    """

    id: int
    content: str
    created_at: datetime  # ISO 8601 in JSON output — e.g. "2026-05-19T14:30:00+00:00"

    model_config = ConfigDict(from_attributes=True)