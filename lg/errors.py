"""
Base exception for user-facing errors.

All expected errors that should be displayed to the user
as clean messages (without stack traces) must inherit from LGUserError.

Programming errors and bugs should NOT inherit from LGUserError —
they will propagate with full tracebacks.
"""

from __future__ import annotations


class LGUserError(Exception):
    """
    Base class for all user-facing errors in Listing Generator.

    These errors indicate problems that the user can fix:
    configuration issues, invalid references, missing files, etc.
    """
    pass


__all__ = ["LGUserError"]
