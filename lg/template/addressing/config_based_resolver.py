"""
Config-based resolver for addressing system.

Provides context-dependent resolution using configuration lookup.
Used by plugins that need to resolve references based on configuration
(e.g., sections in common_placeholders plugin).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict

from .context import AddressingContext

# Type alias for config provider
# Returns dict of available items by name (e.g., sections dict)
ConfigProvider = Callable[[Path], Dict[str, object]]


class ConfigBasedResolver:
    """
    Resolver for references that are defined in configuration.

    Provides context-dependent resolution with prefix fallback:
    - For addressed refs (@origin:name): resolves to target scope
    - For simple refs (name): tries current_dir prefix first, then global
    - For absolute refs (/name): skips prefix, searches globally

    Generic implementation - doesn't know about sections or any specific config structure.
    Uses callback to get available items from config.
    """

    def __init__(
        self,
        repo_root: Path,
        config_provider: ConfigProvider,
        item_name: str = "Item"
    ):
        """
        Initialize resolver.

        Args:
            repo_root: Repository root path
            config_provider: Function to get config items dict for scope
            item_name: Name for items in error messages (e.g., "Section", "Item")
        """
        self.repo_root = repo_root.resolve()
        self.config_provider = config_provider
        self.item_name = item_name

    def resolve(
        self,
        name: str,
        context: AddressingContext
    ) -> tuple[str, Path, str]:
        """
        Resolve reference to (canonical_id, scope_dir, scope_rel).

        Args:
            name: Reference name (may be @origin:name or simple name)
            context: Addressing context with current scope and directory

        Returns:
            Tuple of (canonical_id, scope_dir, scope_rel)

        Raises:
            ValueError: If reference syntax is invalid
            RuntimeError: If reference cannot be resolved
        """
        # Check for addressed reference
        if name.startswith('@'):
            return self._resolve_addressed(name, context)

        # Simple reference - context-dependent search
        return self._resolve_simple(name, context)

    def _resolve_addressed(
        self,
        name: str,
        context: AddressingContext
    ) -> tuple[str, Path, str]:
        """
        Resolve addressed reference (@origin:name or @[origin]:name).

        Parses origin, loads config for target scope, searches there.
        """
        # Parse addressed reference
        origin, local_name = self._parse_addressed_ref(name)

        # Determine scope directory
        scope_dir, scope_rel = self._resolve_origin(origin, context)

        # Load config for target scope
        try:
            config_items = self.config_provider(scope_dir)
        except RuntimeError as e:
            raise RuntimeError(f"Scope not found: {origin}") from e

        # Search in target scope
        # Try with origin prefix first (e.g., "apps/web/web-src")
        if scope_rel:
            prefixed_name = f"{scope_rel}/{local_name}"
            if prefixed_name in config_items:
                return prefixed_name, scope_dir, scope_rel

        # Try without prefix
        if local_name in config_items:
            return local_name, scope_dir, scope_rel

        # Not found
        available = list(config_items.keys())
        raise RuntimeError(
            f"{self.item_name} '{local_name}' not found in scope '{origin}' ({scope_dir}). "
            f"Available: {', '.join(available) if available else '(none)'}"
        )

    def _resolve_simple(
        self,
        name: str,
        context: AddressingContext
    ) -> tuple[str, Path, str]:
        """
        Resolve simple reference with context-dependent search.

        Search order:
        1. If absolute path (/name) - skip prefix, search globally
        2. With current_dir prefix (e.g., 'adapters/src')
        3. Without prefix (global search, e.g., 'src')
        """
        # Get current scope
        scope_dir = context.cfg_root.parent

        # Compute scope_rel
        try:
            scope_rel = scope_dir.relative_to(self.repo_root).as_posix()
            if scope_rel == ".":
                scope_rel = ""
        except ValueError:
            scope_rel = ""

        # Load config for current scope
        config_items = self.config_provider(scope_dir)

        # Get current directory
        current_dir = context.current_directory

        # Handle absolute paths (starting with /)
        is_absolute = name.startswith('/')
        if is_absolute:
            name = name.lstrip('/')
            current_dir = ""  # Skip prefix search

        # Try with current directory prefix first
        if current_dir:
            prefixed_name = f"{current_dir}/{name}"
            if prefixed_name in config_items:
                return prefixed_name, scope_dir, scope_rel

        # Try without prefix (global search)
        if name in config_items:
            return name, scope_dir, scope_rel

        # Not found
        available = list(config_items.keys())
        prefix_hint = f" (tried with prefix '{current_dir}/')" if current_dir else ""
        raise RuntimeError(
            f"{self.item_name} '{name}' not found{prefix_hint}. "
            f"Available: {', '.join(available) if available else '(none)'}"
        )

    def _parse_addressed_ref(self, name: str) -> tuple[str, str]:
        """
        Parse addressed reference into (origin, local_name).

        Formats:
        - @origin:name -> ("origin", "name")
        - @[origin]:name -> ("origin", "name")
        """
        if name.startswith('@['):
            # Bracket form: @[origin]:name
            close = name.find(']:')
            if close < 0:
                raise ValueError(f"Invalid bracketed addressed reference: {name}")
            origin = name[2:close]
            local_name = name[close + 2:]
        else:
            # Simple form: @origin:name
            if ':' not in name[1:]:
                raise ValueError(f"Invalid addressed reference (missing ':'): {name}")
            parts = name[1:].split(':', 1)
            origin = parts[0]
            local_name = parts[1]

        return origin, local_name

    def _resolve_origin(
        self,
        origin: str,
        context: AddressingContext
    ) -> tuple[Path, str]:
        """
        Resolve origin to (scope_dir, scope_rel).

        Args:
            origin: Origin string from addressed reference
            context: Addressing context

        Returns:
            Tuple of (scope_dir, scope_rel)
        """
        if origin == '/' or origin == '':
            # Root scope
            return self.repo_root, ""

        # Relative to current scope
        current_scope = context.cfg_root.parent
        scope_dir = (current_scope / origin).resolve()
        return scope_dir, origin


__all__ = ["ConfigBasedResolver", "ConfigProvider"]
