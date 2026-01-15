"""
Git integration package for Listing Generator.

Provides:
- VcsProvider: Protocol for VCS implementations (extensible to other VCS)
- NullVcs: Fallback when no VCS is available
- GitVcs: Git-specific VCS provider implementation
- GitIgnoreService: Recursive .gitignore loading with caching
"""

from .base import VcsProvider, NullVcs
from .provider import GitVcs
from .gitignore import GitIgnoreService
from .utils import is_git_repo

__all__ = [
    "VcsProvider",
    "NullVcs",
    "GitVcs",
    "GitIgnoreService",
    "is_git_repo",
]
