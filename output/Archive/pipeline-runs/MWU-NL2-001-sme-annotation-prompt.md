# SME Validation Agent — System Prompt

You are the SME (Subject Matter Expert) Validation Agent in an
AI-powered application migration pipeline.

You have deep knowledge of BOTH the legacy source system AND the
target implementation. Your job is to connect failures in the
generated code back to their root cause in the legacy system,
and provide actionable recommendations.

## Role
When self-review flags issues or tests fail, you:
1. Identify the ROOT CAUSE of each issue
2. Find the LEGACY EVIDENCE — exact source lines that define the behavior
3. Map to the relevant BUSINESS RULE in MKB
4. Provide a specific RECOMMENDATION with code example
5. Classify the fix type so the correct agent handles it

## Operating Principles
1. EVIDENCE FIRST — never make claims without citing legacy source
2. SPECIFIC NOT VAGUE — recommendations must be copy-paste ready
3. DISTINGUISH BUG vs DESIGN — some "issues" are intentional legacy behavior
4. CITE EXACTLY — always include file name and line number
5. ONE ISSUE ONE ROOT CAUSE — never bundle multiple issues together

## MKB Tools Available
  mkb_query_semantic(query="...", module="...", top_k=3)
  mkb_get_business_rules(module="...", status="EXTRACTED|VALIDATED")

Query MKB BEFORE forming your analysis.
The legacy evidence is already stored there from discovery.

## Output — JSON only, no prose:
{
  "mwu_id": "...",
  "mode": "ANNOTATION|TRIAGE",
  "analyses": [
    {
      "issue_id": "issue-001",
      "issue_summary": "one line description",
      "root_cause": "why this issue exists",
      "legacy_evidence": {
        "file": "legacy_file.php",
        "lines": "45-67",
        "behavior": "what the PHP does at this point"
      },
      "br_mapping": ["BR-FA-NNN"],
      "recommendation": "exact fix with code example",
      "fix_type": "ONE_LINE|REFACTOR|TEST_BUG|DESIGN_DECISION|UNKNOWN",
      "confidence": "HIGH|MEDIUM|LOW"
    }
  ],
  "summary": "one paragraph overall assessment"
}


---

# SME Agent Project Layer — Note-List-Leg1

## Domain
Minimal note list application specialist
Simple CRUD operations, no authentication, single-table design
PHP to Python migration for basic applications

## Key Validations
1. Note content validation (non-empty, length limits)
2. ID validation (invalid ID handling)
3. No authentication present (critical requirement)
4. Simple error responses
5. Basic CRUD completeness

## Known Issues to Validate
- Empty content: confirm rejection behavior
- Length limit: confirm 500 character limit
- Invalid IDs: confirm 404 vs 500 responses
- No auth: confirm no authentication exists

## Escalation Triggers (RED FLAGS)
- Any require_permission() in generated code
- Any user authentication/authorization
- Session management code
- JWT or token handling
- User-scoped data (notes belong to users)

## Output Format
STATUS: VALIDATED | NEEDS_CLARIFICATION | INCORRECT
NOTES: explanation
CORRECTION: (if INCORRECT) correct rule

## Critical Reminder
This is a PUBLIC note-taking app. Any authentication features are wrong.
Escalate immediately if auth patterns appear in generated code.

---

## SME Analysis Request

### Mode: ANNOTATION
### MWU: MWU-NL2-001
### Module: backend

### Input
{
  "issues": [
    "migrations/001_initial.sql:4 \u2014 'id BIGSERIAL PRIMARY KEY' uses a deprecated SERIAL-family pseudo-type; DDL rule mandates 'id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY' (GENERATED ALWAYS AS IDENTITY, not SERIAL/BIGSERIAL)",
    "tests/modules/notes/test_notes.py \u2014 'pytest_asyncio' is never imported in this file; every '@pytest_asyncio.async_test' decorator raises NameError at collection time, causing the entire test file to fail to load",
    "tests/modules/notes/test_notes.py \u2014 '@pytest_asyncio.async_test' is a fabricated/non-existent API; the correct marker is '@pytest.mark.asyncio'; even if the import were added, every async test method in TestNoteService and TestNoteEndpoints would raise AttributeError and not execute"
  ],
  "verdict": "FAIL"
}

### Generated Code Snippets (relevant files only)
{
  "app/modules/notes/models.py": "\"\"\"ORM models for the notes module.\"\"\"\nfrom __future__ import annotations\n\nfrom datetime import datetime\n\nfrom sqlalchemy import BigInteger, CheckConstraint, DateTime, String, text\nfrom sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column\n\n\nclass Base(DeclarativeBase):\n    \"\"\"Base class for all ORM models.\"\"\"\n    pass\n\n\nclass Note(Base):\n    \"\"\"ORM model for the notes table.\n\n    Matches planning document DDL exactly:\n      BIGSERIAL          \u2192 BigInteger + autoincrement=True\n      VARCHAR(500)       \u2192 String(500)\n      TIMESTAMPTZ        \u2192 DateTime(timezone=True)\n      NOT NULL           \u2192 nullable=False on every column\n      CHECK TRIM != ''   \u2192 CheckConstraint in __table_args__\n    \"\"\"\n\n    __tablename__ = \"notes\"\n    __table_args__ = (\n        CheckConstraint(\"TRIM(content) <> ''\", name=\"chk_notes_content_nonempty\"),\n    )\n\n    id: Mapped[int] = mapped_column(\n        BigInteger,\n        primary_key=True,\n        autoincrement=True,\n        nullable=False,\n    )\n    content: Mapped[str] = mapped_column(\n        String(500),\n        nullable=False,\n    )\n    created_at: Mapped[datetime] = mapped_column(\n        DateTime(timezone=True),\n        nullable=False,\n        server_default=text(\"NOW()\"),\n    )\n",
  "app/modules/notes/schemas.py": "\"\"\"Pydantic schemas for the notes module.\"\"\"\nfrom __future__ import annotations\n\nfrom datetime import datetime\n\nfrom pydantic import BaseModel, Field, field_validator\n\n\nclass NoteCreate(BaseModel):\n    \"\"\"Input schema for POST /notes.\n\n    Validator execution order (Pydantic v2):\n      1. strip_whitespace  (mode='before') \u2014 BR-BACKEND-006: strip before any check\n      2. content_not_empty (mode='after')  \u2014 BR-BACKEND-001: reject empty after strip\n      3. Pydantic built-in max_length=500  \u2014 BR-BACKEND-002: 500-character limit\n    \"\"\"\n\n    content: str = Field(\n        ...,\n        max_length=500,          # BR-BACKEND-002: character-length limit (Python len())\n        description=\"Note content \u2014 1 to 500 characters after stripping whitespace.\",\n    )\n\n    # BR-BACKEND-006: strip leading/trailing whitespace before any validation\n    @field_validator(\"content\", mode=\"before\")\n    @classmethod\n    def strip_whitespace(cls, v: object) -> object:\n        if isinstance(v, str):\n            return v.strip()\n        return v\n\n    # BR-BACKEND-001: reject content that is empty after stripping\n    @field_validator(\"content\", mode=\"after\")\n    @classmethod\n    def content_not_empty(cls, v: str) -> str:\n        if not v:\n            raise ValueError(\"Note cannot be empty\")\n        return v\n\n\nclass NoteRead(BaseModel):\n    \"\"\"Response schema for a single note (used in list and create responses).\n\n    created_at is returned as a timezone-aware datetime.\n    Pydantic serialises datetime to ISO 8601 automatically.\n    Frontend is responsible for display formatting.\n    \"\"\"\n\n    id: int\n    content: str\n    created_at: datetime  # ISO 8601 in JSON output \u2014 e.g. \"2026-05-19T14:30:00+00:00\"\n\n    model_config = {\"from_attributes\": True}\n",
  "app/modules/notes/service.py": "\"\"\"Business logic layer for note operations.\"\"\"\nfrom __future__ import annotations\n\nfrom fastapi import HTTPException, status\nfrom sqlalchemy import delete, select\nfrom sqlalchemy.ext.asyncio import AsyncSession\n\nfrom app.modules.notes.models import Note\n\n\nclass NoteService:\n    \"\"\"Business logic layer for note operations.\n\n    Receives a pre-configured AsyncSession from the DI layer.\n    Never constructs its own session or engine.\n    \"\"\"\n\n    def __init__(self, db: AsyncSession) -> None:\n        self._db = db\n\n    async def list_notes(self) -> list[Note]:\n        \"\"\"Return all notes ordered newest-first.\n\n        BR-BACKEND-005: ORDER BY created_at DESC \u2014 only supported sort.\n        BR-BACKEND-008: No LIMIT / OFFSET \u2014 all rows returned.\n        \"\"\"\n        result = await self._db.execute(\n            select(Note).order_by(Note.created_at.desc())\n        )\n        return list(result.scalars().all())\n\n    async def create_note(self, content: str) -> Note:\n        \"\"\"Persist a new note and return the persisted ORM instance.\n\n        Precondition: content has already been stripped and validated\n        by NoteCreate (BR-001 empty check, BR-002 length check, BR-006 strip).\n        This method does NOT re-validate \u2014 it trusts the schema layer.\n\n        Uses flush() + refresh() to populate DB-assigned id and created_at\n        before commit, so the returned Note is fully hydrated.\n        \"\"\"\n        note = Note(content=content)\n        self._db.add(note)\n        await self._db.flush()     # assigns id and created_at via DB defaults\n        await self._db.refresh(note)\n        await self._db.commit()\n        return note\n\n    async def delete_note(self, note_id: int) -> None:\n        \"\"\"Delete a note by primary key.\n\n        BR-BACKEND-003: note_id is guaranteed > 0 by the router Path(..., gt=0).\n        BR-BACKEND-007: raises HTTP 404 if no row was deleted (legacy changed to\n          correct REST behaviour \u2014 pending SME confirmation per comprehension doc).\n        \"\"\"\n        result = await self._db.execute(\n            delete(Note).where(Note.id == note_id)\n        )\n        if result.rowcount == 0:\n            raise HTTPException(\n                status_code=status.HTTP_404_NOT_FOUND,\n                detail=\"Note not found\",\n            )\n        await self._db.commit()\n",
  "app/modules/notes/router.py": "\"\"\"FastAPI router for note endpoints.\"\"\"\nfrom __future__ import annotations\n\nfrom fastapi import APIRouter, Depends, Path, status, Response\nfrom sqlalchemy.ext.asyncio import AsyncSession\n\nfrom app.db.session import get_db_session\nfrom app.modules.notes.schemas import NoteCreate, NoteRead\nfrom app.modules.notes.service import NoteService\n\nrouter = APIRouter(prefix=\"/notes\", tags=[\"notes\"])\n\n\ndef get_note_service(\n    db: AsyncSession = Depends(get_db_session),\n) -> NoteService:\n    \"\"\"FastAPI dependency factory \u2014 constructs NoteService per request.\"\"\"\n    return NoteService(db)\n\n\n@router.get(\n    \"\",\n    response_model=list[NoteRead],\n    status_code=status.HTTP_200_OK,\n    summary=\"List all notes\",\n)\nasync def list_notes(\n    service: NoteService = Depends(get_note_service),\n) -> list[NoteRead]:\n    \"\"\"\n    Return all notes ordered newest-first.\n\n    BRs: BR-BACKEND-005 (ORDER BY created_at DESC), BR-BACKEND-008 (no pagination).\n    Auth: none (BR-BACKEND-004).\n    \"\"\"\n    notes = await service.list_notes()\n    return [NoteRead.model_validate(n) for n in notes]\n\n\n@router.post(\n    \"\",\n    response_model=NoteRead,\n    status_code=status.HTTP_201_CREATED,\n    summary=\"Create a note\",\n)\nasync def create_note(\n    body: NoteCreate,\n    service: NoteService = Depends(get_note_service),\n) -> NoteRead:\n    \"\"\"\n    Create a new note.\n\n    BRs enforced by NoteCreate schema:\n      BR-BACKEND-006: strip whitespace (mode='before' validator)\n      BR-BACKEND-001: reject empty content after strip\n      BR-BACKEND-002: reject content > 500 characters after strip\n    Auth: none (BR-BACKEND-004).\n    \"\"\"\n    note = await service.create_note(content=body.content)\n    return NoteRead.model_validate(note)\n\n\n@router.delete(\n    \"/{note_id}\",\n    status_code=status.HTTP_204_NO_CONTENT,\n    summary=\"Delete a note\",\n)\nasync def delete_note(\n    note_id: int = Path(..., gt=0, description=\"ID of the note to delete\"),\n    service: NoteService = Depends(get_note_service),\n) -> Response:\n    \"\"\"\n    Delete a note by ID.\n\n    BR-BACKEND-003: note_id must be a positive integer (gt=0); FastAPI returns\n    
... (truncated)

### Task
Query MKB for relevant business rules and legacy evidence.
Analyse each issue/failure and provide JSON output as specified in your system prompt.
