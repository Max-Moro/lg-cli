
from __future__ import annotations


class MigrationFatalError(RuntimeError):
    """
    Top-level exception for fatal migration failures.
    The message text is intended FOR THE USER (with hints).
    The original cause is available via __cause__.
    """
    pass

class PreflightRequired(RuntimeError):
    """Raised by a migration if Git is required for application."""
    pass

__all__ = ["MigrationFatalError", "PreflightRequired"]
