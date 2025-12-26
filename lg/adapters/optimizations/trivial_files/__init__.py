"""
Trivial File Detection.

This package provides infrastructure for detecting and skipping
trivial files that add no value to AI context (re-export only files,
barrel files, package-info files, etc.)
"""

from .analyzer import TrivialFileAnalyzer

__all__ = ["TrivialFileAnalyzer"]
