# Note List Migration — Agent Context
project_id: NOTE-LIST-1
Legacy: PHP 5.6 + MySQL (single file — index.php contains both logic and HTML)
Target: FastAPI + React + PostgreSQL

## Source Structure Note
index.php is a mixed-concern file — it contains:
  - DB query functions (get_notes, add_note, delete_note) <- backend scope
  - HTML rendering (<!DOCTYPE html>...) <- frontend scope
  - Form handling (POST/GET) <- maps to both

The pipeline splits this into two MWUs by SCOPE, not by file.

## MWU-NL-001 — BACKEND (FastAPI)
EXTRACT FROM SOURCE: business logic functions + DB layer only
IGNORE: everything inside <?php ... ?> HTML block, all echo/print statements

OUTPUT FILES (Python only):
  output/backend/main.py
  output/backend/database.py
  output/backend/models.py
  output/backend/routers/notes.py     <- GET /notes, POST /notes, DELETE /notes/{id}
  output/backend/schemas.py
  output/backend/requirements.txt

Business rules to preserve:
  BR-NL-001: content cannot be empty (trim then check)
  BR-NL-002: content max 500 characters
  BR-NL-003: delete id must be positive integer

PHP -> Python patterns:
  mysql_query(SELECT)     -> await db.execute(select(Note).order_by(Note.created_at.desc()))
  mysql_insert_id()       -> result.inserted_primary_key[0]
  mysql_real_escape_string -> SQLAlchemy bound parameters (NEVER f-strings for SQL)
  All DB operations: async SQLAlchemy — NEVER sync

## MWU-NL-002-FE — FRONTEND (React + Vite)
WARNING: THIS MWU PRODUCES REACT FILES. ZERO PYTHON FILES. ZERO PHP FILES.

EXTRACT FROM SOURCE: HTML structure, CSS classes, user interactions
  - The <form> -> React AddNote component with useState
  - The <ul class="note-list"> -> React NoteList component
  - The <li class="note-card"> -> React NoteCard component
  - style.css -> src/index.css (direct port, same class names)
  - The ?delete=id link -> fetch DELETE /notes/{id}
  - The POST form -> fetch POST /notes with JSON body

OUTPUT FILES (JSX/JS/CSS only — if you write a .py file you have the wrong MWU):
  output/frontend/package.json          (vite + react + axios)
  output/frontend/vite.config.js        (proxy: /api -> http://localhost:8280)
  output/frontend/index.html
  output/frontend/src/main.jsx
  output/frontend/src/App.jsx
  output/frontend/src/components/
    AddNote.jsx     <- textarea + submit button, calls POST /notes
    NoteList.jsx    <- maps notes array, calls GET /notes on mount
    NoteCard.jsx    <- single note row + delete button, calls DELETE /notes/{id}
  output/frontend/src/index.css         <- ported from style.css

API calls (backend at http://localhost:8280 via Vite proxy):
  GET    /notes       -> load on mount in NoteList
  POST   /notes       -> AddNote submit {content: string}
  DELETE /notes/{id}  -> NoteCard delete button

CODEGEN HARD RULE: If the output file extension is .py, you are writing
backend code for a FRONTEND MWU. Stop. Re-read this context. Output .jsx only.

## CODEGEN REQUIRED FILES — MWU-NL-001 BACKEND
Every backend MWU MUST generate these files or tests will fail at collection:

  app/__init__.py              (empty)
  app/main.py                  (FastAPI app + include_router)
  app/db/__init__.py           (empty)
  app/db/base.py               (get_db_session + engine + AsyncSessionLocal)
  app/modules/__init__.py      (empty)
  app/modules/backend/__init__.py
  app/modules/backend/models.py
  app/modules/backend/router.py
  app/modules/backend/schemas.py
  app/modules/backend/service.py

app/main.py minimum:
  from fastapi import FastAPI; from app.modules.backend.router import router
  app = FastAPI(); app.include_router(router)

app/db/base.py minimum:
  DATABASE_URL from env var; async engine+sessionmaker; get_db_session() async gen

models.py MUST use MappedAsDataclass if any column uses init=False:
  class Base(MappedAsDataclass, DeclarativeBase): pass

tests/conftest.py MUST use NullPool (port 5436, Docker-mapped):
  test_engine = create_async_engine(url, echo=False, poolclass=NullPool)

service.py list_notes ORDER BY needs id.desc() tiebreaker (PostgreSQL NOW() = txn start time):
  select(Note).order_by(Note.created_at.desc(), Note.id.desc())

## CODEGEN REQUIRED — FastAPI CORS
Every generated main.py MUST include CORSMiddleware:
  from fastapi.middleware.cors import CORSMiddleware
  app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"], allow_headers=["*"])
Missing CORS = browser blocks all API calls from React frontend.
