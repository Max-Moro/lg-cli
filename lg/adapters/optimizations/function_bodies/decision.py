"""
Decision model for function body optimization.
Provides normalized representation of function body processing decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class FunctionBodyDecision:
    """Decision about function body processing."""
    action: Literal["keep", "strip", "trim"]
    max_tokens: Optional[int] = None  # For "trim" action


__all__ = ["FunctionBodyDecision"]
