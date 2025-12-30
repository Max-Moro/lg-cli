"""
Addressing context for the template engine.

Manages the directory context stack for resolving relative paths
during template processing.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .types import DirectoryContext


class AddressingContext:
    """
    Addressing context — manages the directory stack.

    Tracks the current scope (origin) and current directory inside lg-cfg
    when processing nested template inclusions.
    """

    def __init__(self, repo_root: Path, initial_cfg_root: Path):
        """
        Initialize addressing context.

        Args:
            repo_root: Repository root
            initial_cfg_root: Initial lg-cfg/ directory
        """
        self.repo_root = repo_root.resolve()
        self._stack: List[DirectoryContext] = []

        # Initialize root context
        self._stack.append(DirectoryContext(
            origin="self",
            current_dir="",
            cfg_root=initial_cfg_root.resolve()
        ))

    @property
    def current(self) -> DirectoryContext:
        """Current context (top of stack)."""
        return self._stack[-1]

    @property
    def origin(self) -> str:
        """Current scope."""
        return self.current.origin

    @property
    def current_directory(self) -> str:
        """Current directory inside lg-cfg (POSIX, no leading /)."""
        return self.current.current_dir

    @property
    def cfg_root(self) -> Path:
        """Current lg-cfg/ directory."""
        return self.current.cfg_root

    @property
    def root_context(self) -> DirectoryContext:
        """Root context (bottom of stack)."""
        return self._stack[0]

    def push(self, origin: str, current_dir: str, cfg_root: Optional[Path] = None) -> None:
        """
        Push new context onto stack.

        Called when entering ${tpl:...} or ${ctx:...}.

        Args:
            origin: New scope
            current_dir: Directory of loaded file inside lg-cfg
            cfg_root: lg-cfg/ directory (if different from current)
        """
        if cfg_root is None:
            cfg_root = self.current.cfg_root

        self._stack.append(DirectoryContext(
            origin=origin,
            current_dir=current_dir,
            cfg_root=cfg_root.resolve()
        ))

    def pop(self) -> DirectoryContext:
        """
        Pop current context from stack.

        Called when exiting a processed inclusion.

        Returns:
            Removed context

        Raises:
            RuntimeError: When attempting to pop root context
        """
        if len(self._stack) <= 1:
            raise RuntimeError("Cannot pop root addressing context")
        return self._stack.pop()

    def push_for_file(self, file_path: Path, new_origin: Optional[str] = None) -> None:
        """
        Convenience method: push context for a file.

        Automatically computes current_dir from file path.

        Args:
            file_path: Path to loaded file
            new_origin: New scope (if None, keeps current)
        """
        origin = new_origin if new_origin is not None else self.origin

        # Determine cfg_root for the new origin
        if new_origin is not None and new_origin != self.origin and new_origin != "self":
            cfg_root = self._resolve_cfg_root_for_origin(new_origin)
        else:
            cfg_root = self.cfg_root

        # Compute directory of file relative to cfg_root
        try:
            rel_path = file_path.resolve().relative_to(cfg_root)
            current_dir = rel_path.parent.as_posix()
            if current_dir == ".":
                current_dir = ""
        except ValueError:
            # File in different scope — need new cfg_root
            current_dir = ""

        self.push(origin, current_dir, cfg_root)

    def _resolve_cfg_root_for_origin(self, origin: str) -> Path:
        """Compute lg-cfg/ path for specified origin."""
        if origin == "self" or origin == "":
            return self._stack[0].cfg_root  # Root cfg_root

        return (self.repo_root / origin / "lg-cfg").resolve()

    def get_effective_origin(self) -> str:
        """
        Get effective origin for the current context.

        Returns "self" for root scope, or relative path for nested scopes.
        """
        if self.origin == "self":
            # Check if we're at root scope
            try:
                rel = self.cfg_root.parent.relative_to(self.repo_root)
                if rel == Path("."):
                    return "self"
                return rel.as_posix()
            except ValueError:
                return "self"
        return self.origin

    def __len__(self) -> int:
        """Stack depth."""
        return len(self._stack)

    def __repr__(self) -> str:
        return f"AddressingContext(depth={len(self)}, current={self.current})"


__all__ = ["AddressingContext"]
