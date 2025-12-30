"""
Path resolver for the addressing system.

Resolves ParsedPath objects into fully resolved ResolvedPath objects
using the AddressingContext for relative path resolution.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Tuple

from .context import AddressingContext
from .errors import PathResolutionError, ScopeNotFoundError
from .types import ParsedPath, ResolvedPath, ResourceKind


class PathResolver:
    """
    Path resolver — transforms ParsedPath into ResolvedPath.

    Uses AddressingContext for resolving relative paths
    and determining current scope.
    """

    # File extensions by resource kind
    _EXTENSIONS = {
        ResourceKind.TEMPLATE: ".tpl.md",
        ResourceKind.CONTEXT: ".ctx.md",
        ResourceKind.MARKDOWN: ".md",
        ResourceKind.MARKDOWN_EXTERNAL: ".md",
    }

    def __init__(self, repo_root: Path):
        """
        Initialize resolver.

        Args:
            repo_root: Repository root (absolute path)
        """
        self.repo_root = repo_root.resolve()

    def resolve(self, parsed: ParsedPath, context: AddressingContext) -> ResolvedPath:
        """
        Resolve path in context.

        Args:
            parsed: Parsed path
            context: Addressing context (directory stack)

        Returns:
            Fully resolved path

        Raises:
            PathResolutionError: If path cannot be resolved
        """
        # External markdown is handled separately
        if parsed.kind == ResourceKind.MARKDOWN_EXTERNAL:
            return self._resolve_external_markdown(parsed, context)

        # Determine scope
        scope_dir, scope_rel, cfg_root = self._resolve_scope(parsed, context)

        # Determine base directory inside lg-cfg
        base_dir = self._resolve_base_directory(parsed, context)

        # Resolve relative path with support for ../
        resource_rel = self._resolve_relative_path(parsed.path, base_dir, parsed.is_absolute)

        # Add extension if needed
        resource_rel = self._add_extension(resource_rel, parsed.kind)

        # Build full path
        resource_path = (cfg_root / resource_rel).resolve()

        # Validate path doesn't escape lg-cfg
        self._validate_path_bounds(resource_path, cfg_root, parsed)

        return ResolvedPath(
            kind=parsed.kind,
            scope_dir=scope_dir,
            scope_rel=scope_rel,
            cfg_root=cfg_root,
            resource_path=resource_path,
            resource_rel=resource_rel,
        )

    def _resolve_scope(
        self,
        parsed: ParsedPath,
        context: AddressingContext
    ) -> Tuple[Path, str, Path]:
        """
        Resolve scope (origin) to absolute paths.

        Returns:
            (scope_dir, scope_rel, cfg_root)
        """
        origin = parsed.origin

        # If no explicit origin OR "self"/"", use current scope directly
        if origin is None or origin == "self" or origin == "":
            cfg_root = context.cfg_root  # Use current scope's cfg_root
            scope_dir = cfg_root.parent
            try:
                scope_rel = scope_dir.relative_to(self.repo_root).as_posix()
                if scope_rel == ".":
                    scope_rel = ""
            except ValueError:
                scope_rel = ""
            return scope_dir, scope_rel, cfg_root

        # "/" prefix means root scope explicitly
        if origin == "/":
            cfg_root = self.repo_root / "lg-cfg"
            if not cfg_root.is_dir():
                raise ScopeNotFoundError(
                    message="Root lg-cfg/ not found",
                    scope_path=""
                )
            return self.repo_root, "", cfg_root

        # Other origin — path relative to current scope
        current_scope_dir = context.cfg_root.parent  # parent of current lg-cfg/
        scope_dir = (current_scope_dir / origin).resolve()
        cfg_root = scope_dir / "lg-cfg"

        if not cfg_root.is_dir():
            raise ScopeNotFoundError(
                message=f"Scope not found: {origin}",
                scope_path=origin
            )

        # Calculate scope_rel as path from repo root
        try:
            scope_rel = scope_dir.relative_to(self.repo_root).as_posix()
        except ValueError:
            scope_rel = origin

        return scope_dir, scope_rel, cfg_root

    def _resolve_base_directory(
        self,
        parsed: ParsedPath,
        context: AddressingContext
    ) -> str:
        """
        Determine base directory for resolving relative path.

        For absolute paths (starting with /) returns "".
        For relative paths — current directory from context.
        """
        if parsed.is_absolute:
            return ""
        return context.current_directory

    def _resolve_relative_path(self, path: str, base_dir: str, is_absolute: bool) -> str:
        """
        Resolve path relative to base directory.

        Handles:
        - Absolute paths (is_absolute=True): ignores base_dir
        - Relative paths: combines with base_dir
        - Components ".." for going up directories

        Returns:
            Normalized path inside lg-cfg (no leading /)
        """
        if is_absolute:
            work_path = path
        else:
            if base_dir:
                work_path = f"{base_dir}/{path}"
            else:
                work_path = path

        # Normalize path using PurePosixPath
        normalized = PurePosixPath(work_path)

        # Track depth to detect boundary escape early
        parts: list[str] = []
        depth = 0

        for part in normalized.parts:
            if part == '.':
                continue
            elif part == '..':
                if depth > 0:
                    parts.pop()
                    depth -= 1
                else:
                    # Attempting to go above lg-cfg/ boundary
                    raise PathResolutionError(
                        message=f"Path escapes lg-cfg/ boundary: {path}",
                        hint="Cannot use '../' to escape lg-cfg/ directory"
                    )
            else:
                parts.append(part)
                depth += 1

        return '/'.join(parts) if parts else ''

    def _add_extension(self, path: str, kind: ResourceKind) -> str:
        """
        Add file extension if not specified.

        - TEMPLATE → .tpl.md
        - CONTEXT → .ctx.md
        - MARKDOWN → .md
        - SECTION → no change
        """
        if kind == ResourceKind.SECTION:
            return path

        ext = self._EXTENSIONS.get(kind)
        if ext is None:
            return path

        # Check if extension already present
        if path.endswith(ext):
            return path

        # For .md, also check .markdown
        if kind in (ResourceKind.MARKDOWN, ResourceKind.MARKDOWN_EXTERNAL):
            if path.endswith('.md') or path.endswith('.markdown'):
                return path

        return path + ext

    def _validate_path_bounds(
        self,
        resolved: Path,
        cfg_root: Path,
        parsed: ParsedPath
    ) -> None:
        """
        Validate that resolved path doesn't escape lg-cfg/.

        Raises:
            PathResolutionError: When attempting to escape
        """
        try:
            resolved.relative_to(cfg_root)
        except ValueError:
            raise PathResolutionError(
                message=f"Path escapes lg-cfg/ boundary: {parsed.path}",
                parsed=parsed,
                hint="Cannot use '../' to escape lg-cfg/ directory"
            )

    def _resolve_external_markdown(self, parsed: ParsedPath, context: AddressingContext) -> ResolvedPath:
        """
        Resolve external markdown (without @) relative to current scope.

        External markdown files are outside lg-cfg/ but within the current scope directory.
        """
        # Add extension if needed
        resource_rel = self._add_extension(parsed.path, parsed.kind)

        # Build full path relative to current scope (parent of lg-cfg/)
        scope_dir = context.cfg_root.parent
        resource_path = (scope_dir / resource_rel).resolve()

        # Validate path doesn't escape scope
        try:
            resource_path.relative_to(scope_dir)
        except ValueError:
            raise PathResolutionError(
                message=f"Path escapes scope boundary: {parsed.path}",
                parsed=parsed,
                hint="External markdown paths must be within current scope"
            )

        # Calculate scope_rel from repo root
        try:
            scope_rel = scope_dir.relative_to(self.repo_root).as_posix()
            if scope_rel == ".":
                scope_rel = ""
        except ValueError:
            scope_rel = ""

        return ResolvedPath(
            kind=parsed.kind,
            scope_dir=scope_dir,
            scope_rel=scope_rel,
            cfg_root=context.cfg_root,
            resource_path=resource_path,
            resource_rel=resource_rel,
        )


__all__ = ["PathResolver"]
