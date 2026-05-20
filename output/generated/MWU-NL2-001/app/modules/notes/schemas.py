from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NoteCreate(BaseModel):
    """Input schema for POST /api/notes.

    Enforces BR-003 → BR-001 → BR-002 validation chain in strict order.
    """

    content: str = Field(
        ...,
        description="Note text - trimmed before validation, max 500 characters",
    )

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v: object) -> str:
        if not isinstance(v, str):
            raise ValueError("content must be a string")

        # BR-003: strip leading/trailing whitespace FIRST; stripped value is stored
        v = v.strip()

        # BR-001: after strip, value must not be empty
        if not v:
            raise ValueError("Note cannot be empty")

        # BR-002: character-count (not byte-count) must not exceed 500
        if len(v) > 500:
            raise ValueError("Note too long (max 500 chars)")

        # Return trimmed value - this is what gets persisted (BR-003 confirmed)
        return v


class NoteResponse(BaseModel):
    """Output schema for all note endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    created_at: datetime


class NoteListResponse(BaseModel):
    """Envelope for GET /api/notes."""

    notes: list[NoteResponse]