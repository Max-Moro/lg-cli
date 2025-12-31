from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

from ruamel.yaml import YAML

from .index import SectionLocation, ScopeIndex, build_index, iter_all_config_files
from .model import SectionCfg
from ..cache.fs_cache import Cache
from ..migrate import ensure_cfg_actual

_yaml = YAML(typ="safe")

CACHE_VERSION = "1.0"


class SectionNotFoundError(RuntimeError):
    """Raised when a section cannot be found."""
    def __init__(self, name: str, searched: List[str]):
        self.name = name
        self.searched = searched
        super().__init__(
            f"Section '{name}' not found. Searched: {', '.join(searched)}"
        )


class SectionService:
    """
    Unified service for finding and loading sections.

    Provides single point of access to sections with:
    - Lazy loading of section configs
    - Index-based lookup
    - Memory and disk caching
    """

    def __init__(self, root: Path, cache: Cache):
        """
        Initialize section service.

        Args:
            root: Repository root path
            cache: LG cache instance
        """
        self._root = root.resolve()
        self._cache = cache
        # Index cache by scope
        self._indexes: Dict[Path, ScopeIndex] = {}
        # Loaded sections cache: (file_path, local_name) → SectionCfg
        self._loaded: Dict[tuple[Path, str], SectionCfg] = {}

    def get_index(self, scope_dir: Path) -> ScopeIndex:
        """
        Get or build index for a scope.

        Args:
            scope_dir: Scope directory (parent of lg-cfg/)

        Returns:
            ScopeIndex for the scope
        """
        scope_dir = scope_dir.resolve()

        # Check memory cache
        if scope_dir in self._indexes:
            return self._indexes[scope_dir]

        cfg_root_path = scope_dir / "lg-cfg"
        if not cfg_root_path.is_dir():
            raise RuntimeError(f"No lg-cfg/ directory found in {scope_dir}")

        # Ensure migrations are up to date
        ensure_cfg_actual(cfg_root_path)

        # Try to load from disk cache
        cached = self._load_index_from_cache(scope_dir)
        if cached and self._is_index_valid(cached, cfg_root_path):
            self._indexes[scope_dir] = cached
            return cached

        # Build new index
        index = build_index(cfg_root_path)
        self._save_index_to_cache(scope_dir, index)
        self._indexes[scope_dir] = index
        return index

    def find_section(
        self,
        name: str,
        current_dir: str,
        scope_dir: Path
    ) -> SectionLocation:
        """
        Find section by name considering context.

        Args:
            name: Section reference from template (e.g., "src", "/src", "adapters/src")
            current_dir: Current directory context (e.g., "adapters" when processing
                         template in lg-cfg/adapters/)
            scope_dir: Scope directory

        Returns:
            SectionLocation for found section

        Raises:
            SectionNotFoundError: If section not found
        """
        index = self.get_index(scope_dir)

        # Absolute path: skip prefix, search directly
        if name.startswith('/'):
            key = name.lstrip('/')
            if key in index.sections:
                return index.sections[key]
            raise SectionNotFoundError(name, searched=[key])

        # Relative path: try with current_dir prefix first
        searched = []

        if current_dir:
            prefixed = f"{current_dir}/{name}"
            searched.append(prefixed)
            if prefixed in index.sections:
                return index.sections[prefixed]

        # Then try without prefix (global search)
        searched.append(name)
        if name in index.sections:
            return index.sections[name]

        raise SectionNotFoundError(name, searched=searched)

    def load_section(self, location: SectionLocation) -> SectionCfg:
        """
        Lazily load a single section by its location.

        Args:
            location: Section location from index

        Returns:
            Parsed SectionCfg
        """
        cache_key = (location.file_path, location.local_name)

        # Check memory cache
        if cache_key in self._loaded:
            return self._loaded[cache_key]

        # Load from YAML
        try:
            raw = _yaml.load(location.file_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            raise RuntimeError(f"Failed to read {location.file_path}: {e}")

        if not isinstance(raw, dict):
            raise RuntimeError(f"YAML must be a mapping: {location.file_path}")

        node = raw.get(location.local_name)
        if node is None:
            raise RuntimeError(
                f"Section '{location.local_name}' not found in {location.file_path}"
            )

        if not isinstance(node, dict):
            raise RuntimeError(
                f"Section '{location.local_name}' in {location.file_path} must be a mapping"
            )

        # Parse section
        section_cfg = SectionCfg.from_dict(location.local_name, node)

        # Cache
        self._loaded[cache_key] = section_cfg
        return section_cfg

    def list_sections(self, scope_dir: Path) -> List[str]:
        """
        List all sections in a scope.

        Args:
            scope_dir: Scope directory

        Returns:
            Sorted list of section names
        """
        index = self.get_index(scope_dir)
        return sorted(index.sections.keys())

    def list_sections_peek(self, scope_dir: Path) -> List[str]:
        """
        List sections without running migrations.

        Safe for diagnostics. Reads directly without ensure_cfg_actual.

        Args:
            scope_dir: Scope directory

        Returns:
            Sorted list of section names
        """
        cfg_root_path = scope_dir / "lg-cfg"
        if not cfg_root_path.is_dir():
            return []

        # Build index directly without migrations
        index = build_index(cfg_root_path)
        return sorted(index.sections.keys())

    # ---- Cache helpers ----

    def _is_index_valid(self, cached_index: ScopeIndex, cfg_root_path: Path) -> bool:
        """Check if cached index is still valid by comparing file mtimes."""
        # Check if any known file was modified
        for file_path, cached_mtime in cached_index.file_mtimes.items():
            if not file_path.exists():
                return False  # File deleted
            try:
                current_mtime = file_path.stat().st_mtime
                if abs(current_mtime - cached_mtime) > 0.001:  # Float precision
                    return False  # File modified
            except Exception:
                return False

        # Check if new files appeared
        current_files = set(iter_all_config_files(cfg_root_path))
        cached_files = set(cached_index.file_mtimes.keys())
        if current_files != cached_files:
            return False  # Files added or removed

        return True

    def _get_cache_key(self, scope_dir: Path) -> str:
        """Generate cache key for scope."""
        try:
            rel = scope_dir.relative_to(self._root)
            if rel == Path("."):
                return "root"
            return str(rel).replace("/", "_").replace("\\", "_")
        except ValueError:
            # Scope outside repository - hash absolute path
            import hashlib
            return hashlib.sha256(str(scope_dir).encode()).hexdigest()[:16]

    def _get_cache_path(self, scope_dir: Path) -> Path:
        """Get path to cached index file."""
        cache_key = self._get_cache_key(scope_dir)
        return self._cache.dir / "sections" / f"{cache_key}.index"

    def _load_index_from_cache(self, scope_dir: Path) -> Optional[ScopeIndex]:
        """Load index from disk cache."""
        if not self._cache.enabled:
            return None

        cache_file = self._get_cache_path(scope_dir)
        if not cache_file.exists():
            return None

        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))

            # Check format version
            if data.get("version") != CACHE_VERSION:
                return None

            # Deserialize
            sections = {
                name: SectionLocation(
                    file_path=Path(loc["file_path"]),
                    local_name=loc["local_name"]
                )
                for name, loc in data["sections"].items()
            }

            file_mtimes = {
                Path(fp): mtime
                for fp, mtime in data["file_mtimes"].items()
            }

            return ScopeIndex(sections=sections, file_mtimes=file_mtimes)
        except Exception:
            # Invalid cache - ignore
            return None

    def _save_index_to_cache(self, scope_dir: Path, index: ScopeIndex) -> None:
        """Save index to disk cache."""
        if not self._cache.enabled:
            return

        cache_file = self._get_cache_path(scope_dir)
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "version": CACHE_VERSION,
                "scope_dir": str(scope_dir),
                "built_at": time.time(),
                "sections": {
                    name: {
                        "file_path": str(loc.file_path),
                        "local_name": loc.local_name
                    }
                    for name, loc in index.sections.items()
                },
                "file_mtimes": {
                    str(fp): mtime
                    for fp, mtime in index.file_mtimes.items()
                }
            }

            cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            # Best effort - ignore cache write errors
            pass


# ---- Convenience functions for backward compatibility ----

def list_sections(root: Path) -> List[str]:
    """
    List all sections (with migrations).

    Args:
        root: Repository root

    Returns:
        Sorted list of section names
    """
    from ..cache.fs_cache import Cache
    from ..version import tool_version

    cache = Cache(root, enabled=None, fresh=False, tool_version=tool_version())
    service = SectionService(root, cache)
    return service.list_sections(root)


def list_sections_peek(root: Path) -> List[str]:
    """
    List sections without running migrations.

    Args:
        root: Repository root

    Returns:
        Sorted list of section names
    """
    from ..cache.fs_cache import Cache
    from ..version import tool_version

    cache = Cache(root, enabled=None, fresh=False, tool_version=tool_version())
    service = SectionService(root, cache)
    return service.list_sections_peek(root)


__all__ = [
    "SectionService",
    "SectionLocation",
    "ScopeIndex",
    "SectionNotFoundError",
    "list_sections",
    "list_sections_peek",
]
