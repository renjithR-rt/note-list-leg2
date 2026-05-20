"""Stubs for the backend module.

This simple note-taking application has no external dependencies
that require stubs. All functionality is self-contained.

If future sprints add authentication (after BR-BACKEND-005 is updated),
an AuthServiceStub would be added here.
"""

from typing import Optional

class AuthServiceStub:
    """Placeholder for future authentication service.
    
    DO NOT IMPLEMENT — BR-BACKEND-005 forbids authentication.
    This stub documents that auth absence is intentional, not an oversight.
    """
    
    @classmethod
    def get_current_user(cls, token: Optional[str] = None) -> None:
        raise NotImplementedError(
            "Authentication not implemented — BR-BACKEND-005: "
            "this app is intentionally public with no auth"
        )

# Export empty for now - no stubs needed
__all__: list[str] = []