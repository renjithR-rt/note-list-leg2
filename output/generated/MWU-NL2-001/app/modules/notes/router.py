from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.notes.schemas import NoteCreate, NoteListResponse, NoteResponse
from app.modules.notes.service import NoteService

# BR-006: No authentication on any endpoint - intentionally public
router = APIRouter(prefix="/api")


@router.get("/notes", response_model=NoteListResponse)
async def list_notes(db: AsyncSession = Depends(get_db_session)) -> NoteListResponse:
    """Get all notes, newest first.
    
    BR-007: newest-first ordering (no user-configurable sort).
    BR-006: no auth - public endpoint.
    """
    notes = await NoteService.list_notes(db)
    return NoteListResponse(notes=notes)


@router.post("/notes", response_model=NoteResponse, status_code=201)
async def create_note(
    data: NoteCreate,
    db: AsyncSession = Depends(get_db_session),
) -> NoteResponse:
    """Create a new note.
    
    BR-001/002/003 enforced by Pydantic validation chain.
    BR-006: no auth - public endpoint.
    """
    note = await NoteService.create_note(db, data)
    return NoteResponse.model_validate(note)


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(
    note_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Delete a note by ID.
    
    BR-004/005 enforced in service layer.
    BR-006: no auth - public endpoint.
    """
    await NoteService.delete_note(db, note_id)
    return Response(status_code=204)