from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.modules.backend.models import Note
from app.modules.backend.schemas import DeleteResult, NoteCreate

class NoteService:
    """Business logic for the notes resource.
    
    All methods are async and use SQLAlchemy 2.x async patterns.
    The db session is injected via FastAPI Depends(get_db) — no globals.
    Commit/rollback is handled by get_db(), not here.
    """
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
    
    # ------------------------------------------------------------------ 
    # BR-BACKEND-004: list always ordered by created_at DESC
    # ------------------------------------------------------------------
    async def list_notes(self) -> list[Note]:
        """Return all notes, newest first.
        
        Implements BR-BACKEND-004: ORDER BY created_at DESC is an invariant.
        No pagination, no filtering — matches legacy behavior exactly.
        Uses idx_notes_created_at_desc index for efficient sort.
        """
        result = await self.db.execute(
            select(Note).order_by(Note.created_at.desc(), Note.id.desc())
        )
        return list(result.scalars().all())
    
    # ------------------------------------------------------------------
    # BR-BACKEND-001: empty content rejected after trim
    # BR-BACKEND-002: content max 500 characters  
    # BR-BACKEND-006: content trimmed before validation and storage
    # ------------------------------------------------------------------
    async def create_note(self, data: NoteCreate) -> Note:
        """Create and persist a new note.
        
        BR-BACKEND-001, BR-BACKEND-002, BR-BACKEND-006:
        All three are enforced by NoteCreate Pydantic validators BEFORE this
        method is called. By the time data reaches here, content is already:
          - stripped of leading/trailing whitespace (BR-006)
          - confirmed non-empty (BR-001)
          - confirmed <= 500 chars (BR-002)
          
        Uses ORM (parameterized) — never string concatenation.
        Session is injected, never a global.
        """
        note = Note(content=data.content)
        self.db.add(note)
        await self.db.flush()  # assigns id and created_at from DB without committing
        await self.db.refresh(note)  # populate all DB-defaulted fields  
        return note
    
    # ------------------------------------------------------------------
    # BR-BACKEND-003: note_id must be positive integer (enforced in router)
    # BR-BACKEND-007: HITL GATE — 404 on missing (recommended, not yet signed off)
    # ------------------------------------------------------------------
    async def delete_note(self, note_id: int) -> DeleteResult:
        """Delete a note by primary key.
        
        BR-BACKEND-003: note_id > 0 is already validated by Path(gt=0) in the
        router before this method is called.
        
        BR-BACKEND-007 HITL GATE:
          CURRENT IMPLEMENTATION: Returns HTTP 404 if note does not exist.
          LEGACY BEHAVIOR: Silent success — DELETE runs, ok=True always.
          
          To revert to legacy silent-success behavior, replace the rowcount
          check below with:
              return DeleteResult(ok=True, message="Deleted")
              
          Do NOT change this until stakeholder resolves the HITL gate.
        """
        result = await self.db.execute(
            delete(Note).where(Note.id == note_id)
        )
        # BR-BACKEND-007 recommended path: 404 if not found
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Note {note_id} not found",
            )
        return DeleteResult(ok=True, message="Deleted")