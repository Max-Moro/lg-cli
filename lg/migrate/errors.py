
from __future__ import annotations

from ..errors import LGUserError


class MigrationFatalError(LGUserError):
    """
    Top-level exception for fatal migration failures.
    The message text is intended FOR THE USER (with hints).
    The original cause is available via __cause__.
    """
    pass

class PreflightRequired(LGUserError):
    """Raised by a migration if Git is required for application."""
    pass

__all__ = ["MigrationFatalError", "PreflightRequired"]
