from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

class NoteCreate(BaseModel):
    """Input schema for POST /notes/.
    
    Implements BR-BACKEND-001, BR-BACKEND-002, BR-BACKEND-006.
    Validation order (Pydantic executes mode='before' first):
      1. strip_whitespace (BR-BACKEND-006) — trim before any check
      2. Field(max_length=500) (BR-BACKEND-002) — length after trim  
      3. content_not_empty (BR-BACKEND-001) — empty after trim
    """
    
    content: str = Field(
        ...,
        max_length=500,
        description="Note text. Whitespace is trimmed. Must not be empty. Max 500 characters.",
        examples=["Buy milk", "Call dentist tomorrow at 9am"],
    )
    
    @field_validator("content", mode="before")
    @classmethod
    def strip_whitespace(cls, v: object) -> str:
        """BR-BACKEND-006: trim() is the first operation in legacy add_note().
        Applied before empty check and max_length check.
        """
        if not isinstance(v, str):
            raise ValueError("content must be a string")
        return v.strip()
    
    @field_validator("content")
    @classmethod 
    def content_not_empty(cls, v: str) -> str:
        """BR-BACKEND-001: reject content that is empty after trim.
        Legacy: if (empty($content)) { $errors[] = 'Note cannot be empty'; }
        """
        if not v:
            raise ValueError("Note cannot be empty")
        return v

class NoteRead(BaseModel):
    """Response schema for a single note.
    
    created_at is returned as a timezone-aware datetime.
    Pydantic serializes datetime to ISO 8601 by default.
    Frontend handles date formatting (not API concern).
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    content: str
    created_at: datetime  # ISO 8601: "2026-05-18T14:30:00+00:00"

class DeleteResult(BaseModel):
    """Response schema for DELETE /notes/{id}.
    
    BR-BACKEND-007 HITL GATE:
      Current implementation: ok=True on success, 404 on missing.
      Legacy behavior: ok=True always, even if 0 rows deleted.
      Schema supports both behaviors via ok: bool, message: str.
    """
    
    ok: bool
    message: str