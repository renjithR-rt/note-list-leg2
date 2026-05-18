from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.notes.schemas import NoteCreate, NoteRead
from app.modules.notes.service import NoteService

router = APIRouter(prefix="/notes", tags=["notes"])


async def get_note_service(
    db: AsyncSession = Depends(get_db_session),
) -> NoteService:
    """FastAPI dependency factory — constructs NoteService per request."""
    return NoteService(db)


@router.get(
    "",
    response_model=list[NoteRead],
    status_code=status.HTTP_200_OK,
    summary="List all notes",
)
async def list_notes(
    service: NoteService = Depends(get_note_service),
) -> list[NoteRead]:
    """
    Return all notes ordered newest-first.

    BRs: BR-BACKEND-005 (ORDER BY created_at DESC), BR-BACKEND-008 (no pagination).
    Auth: none (BR-BACKEND-004).
    """
    notes = await service.list_notes()
    return [NoteRead.model_validate(n) for n in notes]


@router.post(
    "",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a note",
)
async def create_note(
    body: NoteCreate,
    service: NoteService = Depends(get_note_service),
) -> NoteRead:
    """
    Create a new note.

    BRs enforced by NoteCreate schema:
      BR-BACKEND-006: strip whitespace (mode='before' validator)
      BR-BACKEND-001: reject empty content after strip
      BR-BACKEND-002: reject content > 500 characters after strip
    Auth: none (BR-BACKEND-004).
    """
    note = await service.create_note(content=body.content)
    return NoteRead.model_validate(note)


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a note",
)
async def delete_note(
    note_id: int = Path(..., gt=0, description="ID of the note to delete"),
    service: NoteService = Depends(get_note_service),
) -> Response:
    """
    Delete a note by ID.

    BR-BACKEND-003: note_id must be a positive integer (gt=0); FastAPI returns
      422 automatically for non-integer or <= 0 values.
    BR-BACKEND-007: returns 404 if no note with that ID exists.
    Auth: none (BR-BACKEND-004).
    """
    await service.delete_note(note_id=note_id)
    return Response(status_code=204)