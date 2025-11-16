from __future__ import annotations

# Single "current" version of lg-cfg/ format that the tool brings config to.
# Actual migrations can jump directly to CURRENT (mega-migrations).
CFG_CURRENT: int = 4

__all__ = ["CFG_CURRENT"]
