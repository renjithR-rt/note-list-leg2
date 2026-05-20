"""
FastAPI router for the notes API.

BR-006: No authentication, authorization, sessions, or API keys anywhere
        in this module. This is a CRITICAL hard constraint from the source design.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.backend.schemas import DeleteResponse, NoteCreate, NoteResponse
from app.modules.backend.service import NoteService

router = APIRouter(prefix="/api", tags=["notes"])


@router.get(
    "/notes",
    response_model=list[NoteResponse],
    summary="List all notes",
    description="Returns all notes ordered by creation date descending (newest first). BR-007.",
)
async def get_notes(
    db: AsyncSession = Depends(get_db_session),
) -> list[NoteResponse]:
    """
    BR-007: notes always returned newest-first; no client-configurable sort.
    BR-006: no auth.
    """
    service = NoteService(db)
    notes = await service.get_notes()
    return [NoteResponse.model_validate(note) for note in notes]


@router.post(
    "/notes",
    response_model=NoteResponse,
    status_code=201,
    summary="Create a note",
    description=(
        "Creates a new note. "
        "Content is whitespace-trimmed (BR-003), must not be empty (BR-001), "
        "and must not exceed 500 characters (BR-002)."
    ),
)
async def create_note(
    payload: NoteCreate,
    db: AsyncSession = Depends(get_db_session),
) -> NoteResponse:
    """
    BR-001, BR-002, BR-003: enforced by NoteCreate Pydantic schema.
    BR-009: created_at is set by DB server_default; app never supplies it.
    BR-006: no auth.
    RISK-005: REST + SPA eliminates PRG; POST returns 201 JSON, no redirect.
    """
    service = NoteService(db)
    note = await service.create_note(payload.content)
    return NoteResponse.model_validate(note)


@router.delete(
    "/notes/{note_id}",
    response_model=DeleteResponse,
    status_code=200,
    summary="Delete a note",
    description=(
        "Deletes a note by ID. "
        "ID must be a positive integer (BR-004). "
        "Returns 404 if the note does not exist (BR-005)."
    ),
)
async def delete_note(
    note_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> DeleteResponse:
    """
    BR-004: reject note_id <= 0 with "Invalid note ID".
    BR-005: 404 if note_id valid but note not found.
    RISK-004: DELETE HTTP method; no GET-based deletion accepted.
    BR-006: no auth.
    """
    # BR-004: cast to int happens via FastAPI path type annotation.
    # Manual > 0 check produces the exact error message specified in BR-004.
    if note_id <= 0:
        raise HTTPException(status_code=422, detail="Invalid note ID")

    service = NoteService(db)
    await service.delete_note(note_id)
    return DeleteResponse(ok=True)