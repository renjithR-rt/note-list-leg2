from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.notes.router import router as notes_router

app = FastAPI(
    title="Note List API",
    version="2.0.0",
    description="Simple note management API - migrated from PHP to FastAPI"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # BR-006: Public API, no auth restrictions
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

# BR-006: No authentication middleware - intentionally public
app.include_router(notes_router)