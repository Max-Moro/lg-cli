"""
Function Body Optimization.

This package provides function/method body processing
capabilities for reducing code verbosity in listings.
"""

from .optimizer import FunctionBodyOptimizer
from .decision import FunctionBodyDecision
from .evaluators import (
    ExceptPatternEvaluator,
    KeepAnnotatedEvaluator,
    BasePolicyEvaluator,
)

__all__ = [
    "FunctionBodyOptimizer",
    "FunctionBodyDecision",
    "ExceptPatternEvaluator",
    "KeepAnnotatedEvaluator",
    "BasePolicyEvaluator",
]
