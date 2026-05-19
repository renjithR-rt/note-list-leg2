"""Note List Backend Module.

Implements a simple note CRUD API migrated from PHP.
No authentication required (BR-BACKEND-005).
"""

from app.modules.backend.models import Note
from app.modules.backend.router import router
from app.modules.backend.service import NoteService

__all__ = ["Note", "router", "NoteService"]