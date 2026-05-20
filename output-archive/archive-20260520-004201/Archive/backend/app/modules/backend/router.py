from __future__ import annotations

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db_session
from app.modules.backend.schemas import DeleteResult, NoteCreate, NoteRead
from app.modules.backend.service import NoteService

# BR-BACKEND-005: prefix="/notes", NO auth dependency at router level
router = APIRouter(prefix="/notes", tags=["notes"])

@router.get(
    "/",
    response_model=list[NoteRead],
    status_code=status.HTTP_200_OK,
    summary="List all notes, newest first",
    description=(
        "Returns all notes ordered by created_at DESC. "
        "BR-BACKEND-004: sort order is an invariant — no sort parameter is accepted."
    ),
)
async def list_notes(
    db: AsyncSession = Depends(get_db_session),
    # BR-BACKEND-005: NO current_user parameter. NO auth dependency.
) -> list[NoteRead]:
    service = NoteService(db)
    notes = await service.list_notes()
    return [NoteRead.model_validate(note) for note in notes]

@router.post(
    "/",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new note",
    description=(
        "Creates a note. Content is trimmed (BR-BACKEND-006), "
        "validated non-empty (BR-BACKEND-001), and max 500 chars (BR-BACKEND-002)."
    ),
    responses={
        422: {"description": "Validation error — content empty or too long"},
    },
)
async def create_note(
    data: NoteCreate,
    db: AsyncSession = Depends(get_db_session),
    # BR-BACKEND-005: NO current_user parameter. NO auth dependency.
) -> NoteRead:
    service = NoteService(db)
    note = await service.create_note(data)
    return NoteRead.model_validate(note)

@router.delete(
    "/{note_id}",
    response_model=DeleteResult,
    status_code=status.HTTP_200_OK,
    summary="Delete a note by ID",
    description=(
        "Deletes a note. ID must be a positive integer (BR-BACKEND-003). "
        "HITL GATE (BR-BACKEND-007): returns 404 if note not found "
        "(recommended behavior — pending stakeholder sign-off)."
    ),
    responses={
        400: {"description": "note_id is not a positive integer (handled by 422 from Path)"},
        404: {"description": "Note not found — BR-BACKEND-007 pending validation"},
        422: {"description": "note_id is not an integer or is <= 0"},
    },
)
async def delete_note(
    # BR-BACKEND-003: gt=0 enforces positive integer; FastAPI returns 422 automatically
    # for non-integer or for note_id <= 0.
    note_id: int = Path(..., gt=0, description="Note ID — must be a positive integer"),
    db: AsyncSession = Depends(get_db_session),
    # BR-BACKEND-005: NO current_user parameter. NO auth dependency.
) -> DeleteResult:
    service = NoteService(db)
    return await service.delete_note(note_id)