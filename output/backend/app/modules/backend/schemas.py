"""
Pydantic v2 schemas for the notes API.

Validation chain for note creation (BR-003 → BR-001 → BR-002):
  1. BR-003: strip() whitespace
  2. BR-001: reject empty string
  3. BR-002: reject length > 500

The chain order is enforced within a single validator so the sequence
cannot be accidentally reordered by a future developer.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


# ---------------------------------------------------------------------------
# Input schemas (request bodies)
# ---------------------------------------------------------------------------

class NoteCreate(BaseModel):
    """
    Request body for POST /api/notes.

    Implements the BR-003 → BR-001 → BR-002 validation chain in strict order.
    The trimmed value (BR-003) is what gets stored, not the raw input.
    """

    content: str

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v: object) -> str:
        """
        Enforces validation chain in mandatory order:
          BR-003 — trim whitespace first
          BR-001 — reject if empty after trim
          BR-002 — reject if exceeds 500 chars after trim
        """
        if not isinstance(v, str):
            raise ValueError("content must be a string")

        # BR-003: trim whitespace; the trimmed result is stored, not the raw input
        v = v.strip()

        # BR-001: reject empty content (checked AFTER trim so "   " is correctly rejected)
        if not v:
            raise ValueError("Note cannot be empty")

        # BR-002: reject content exceeding 500 characters (checked on trimmed value)
        if len(v) > 500:
            raise ValueError("Note too long (max 500 chars)")

        return v


# ---------------------------------------------------------------------------
# Response schemas (response bodies)
# ---------------------------------------------------------------------------

class NoteResponse(BaseModel):
    """
    Response schema for a single note.

    BR-009: created_at is always present (DB-supplied); never null.
    from_attributes=True: required for SQLAlchemy ORM → Pydantic serialization.
    """

    id: int
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeleteResponse(BaseModel):
    """
    Response body for a successful DELETE /api/notes/{note_id}.

    Returns a minimal acknowledgement. Frontend checks ok=True to confirm deletion.
    Chosen over 204 No Content to maintain parity with legacy ok:true JSON shape,
    easing frontend migration (MWU-NL2-002-FE can detect success without
    inspecting status codes alone).
    """

    ok: bool = True