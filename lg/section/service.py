from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

from ruamel.yaml import YAML

from .index import SectionLocation, ScopeIndex, build_index, iter_all_config_files
from .model import SectionCfg
from .sections_list_schema import (
    SectionsList,
    SectionInfo,
    ModeSet as ModeSetSchema,
    Mode as ModeSchema,
    TagSet as TagSetSchema,
    Tag as TagSchema,
)
from ..cache.fs_cache import Cache
from ..migrate import ensure_cfg_actual
from ..errors import LGUserError
from ..version import tool_version

_yaml = YAML(typ="safe")

CACHE_VERSION = "1.0"


class SectionNotFoundError(LGUserError):
    """Raised when a section cannot be found."""
    def __init__(self, name: str, searched: List[str]):
        self.name = name
        self.searched = searched
        super().__init__(
            f"Section '{name}' not found. Searched: {', '.join(searched)}"
        )


class SectionService:
    """
    Service for finding and loading sections.

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
    ) -> tuple[str, SectionLocation]:
        """
        Find section by name considering context.

        Args:
            name: Section reference from template (e.g., "src", "/src", "adapters/src")
            current_dir: Current directory context (e.g., "adapters" when processing
                         template in lg-cfg/adapters/)
            scope_dir: Scope directory

        Returns:
            Tuple of (canonical_name, SectionLocation).
            The canonical_name is the index key used to find the section.

        Raises:
            SectionNotFoundError: If section not found
        """
        index = self.get_index(scope_dir)

        # Absolute path: skip prefix, search directly
        if name.startswith('/'):
            key = name.lstrip('/')
            if key in index.sections:
                return key, index.sections[key]
            raise SectionNotFoundError(name, searched=[key])

        # Relative path: try with current_dir prefix first
        searched = []

        if current_dir:
            prefixed = f"{current_dir}/{name}"
            searched.append(prefixed)
            if prefixed in index.sections:
                return prefixed, index.sections[prefixed]

        # Then try without prefix (global search)
        searched.append(name)
        if name in index.sections:
            return name, index.sections[name]

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

        if cache_key not in self._loaded:
            node = self._load_raw_section(location)
            self._loaded[cache_key] = SectionCfg.from_dict(location.local_name, node)

        return self._loaded[cache_key]

    def list_sections(self, scope_dir: Path) -> List[str]:
        """
        List renderable sections in a scope.

        Excludes meta-sections (those without explicit filters)
        since they cannot be rendered directly and are used
        only for inheritance via extends.

        Args:
            scope_dir: Scope directory

        Returns:
            Sorted list of renderable section names
        """
        return self._collect_renderable(self.get_index(scope_dir))

    def list_sections_peek(self, scope_dir: Path) -> List[str]:
        """
        List renderable sections without running migrations.

        Safe for diagnostics. Reads directly without ensure_cfg_actual.
        Excludes meta-sections (those without explicit filters).

        Args:
            scope_dir: Scope directory

        Returns:
            Sorted list of renderable section names
        """
        cfg_root_path = scope_dir / "lg-cfg"
        if not cfg_root_path.is_dir():
            return []

        return self._collect_renderable(build_index(cfg_root_path))

    def _collect_renderable(self, index: ScopeIndex) -> List[str]:
        """
        Collect names of renderable (non-meta) sections from index.

        Args:
            index: Section index to filter

        Returns:
            Sorted list of renderable section names
        """
        return [
            name for name in sorted(index.sections.keys())
            if not self.load_section(index.sections[name]).is_meta_section()
        ]

    def _load_raw_section(self, location: SectionLocation) -> dict:
        """
        Load raw section dict from YAML without caching.

        Args:
            location: Section location from index

        Returns:
            Raw section dictionary from YAML
        """
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

        return node

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


# ---- Public API functions ----

def list_sections(
    root: Path,
    *,
    context: Optional[str] = None,
    peek: bool = False,
) -> SectionsList:
    """
    List sections with their adaptive configuration.

    Args:
        root: Repository root
        context: If specified, only return sections used in this context
        peek: If True, skip migrations (safe for diagnostics)

    Returns:
        SectionsList with sections and their mode-sets/tag-sets
    """
    cache = Cache(root, enabled=None, fresh=False, tool_version=tool_version())
    service = SectionService(root, cache)

    sections_info = []

    if context is not None:
        # Use resolved sections to preserve directory context
        resolved_sections = _get_resolved_sections_for_context(root, context, cache)
        for resolved in resolved_sections:
            adaptive_model = _resolve_adaptive_from_resolved(resolved, root, cache)
            # Use canonical_name for display
            section_info = _build_section_info(resolved.canonical_name, adaptive_model)
            sections_info.append(section_info)
    else:
        # Get section names from index
        if peek:
            section_names = service.list_sections_peek(root)
        else:
            section_names = service.list_sections(root)

        for name in section_names:
            adaptive_model = _resolve_section_adaptive(name, root, cache)
            section_info = _build_section_info(name, adaptive_model)
            sections_info.append(section_info)

    return SectionsList(sections=sections_info)


def _get_resolved_sections_for_context(root: Path, context: str, cache: Cache) -> List:
    """
    Get resolved sections used in a context.

    Returns only template sections (renderable), not frontmatter includes (meta).
    ResolvedSection objects preserve directory context for proper extends resolution.
    """
    # Lazy import to avoid circular dependencies
    from ..adaptive.context_resolver import create_context_resolver
    from ..template.analysis import SectionCollector

    _, section_service, addressing = create_context_resolver(root, cache)
    cfg_root = root / "lg-cfg"

    collector = SectionCollector(section_service, addressing, cfg_root)
    collected = collector.collect(context)

    # template_sections are already deduplicated and exclude frontmatter
    result = list(collected.template_sections)

    # Sort by canonical name for stable output
    result.sort(key=lambda r: r.canonical_name)
    return result


def _resolve_adaptive_from_resolved(resolved, root: Path, cache: Cache):
    """
    Resolve adaptive model from already resolved section.

    Uses ExtendsResolver.resolve_from_cfg with proper current_dir
    to correctly resolve relative extends references.
    """
    from ..adaptive.extends_resolver import ExtendsResolver

    service = SectionService(root, cache)
    extends_resolver = ExtendsResolver(service)

    return extends_resolver.resolve_from_resolved(resolved).adaptive_model


def _resolve_section_adaptive(name: str, root: Path, cache: Cache):
    """
    Resolve adaptive model (mode-sets, tag-sets) for a section by name.

    Used when listing all sections (no context filtering).

    Returns:
        AdaptiveModel for the section
    """
    # Lazy import to avoid circular dependencies
    from ..adaptive.context_resolver import create_context_resolver

    resolver, section_service, addressing = create_context_resolver(root, cache)

    # Use resolve_for_section which handles extends chain
    return resolver.resolve_for_section(name, scope_dir=root)


def _build_section_info(name: str, adaptive_model) -> SectionInfo:
    """
    Build SectionInfo schema object from section name and adaptive model.
    """
    # Convert mode-sets
    mode_sets_list = []
    for set_id, mode_set in adaptive_model.mode_sets.items():
        modes_list = []
        for mode_id, mode in mode_set.modes.items():
            mode_schema = ModeSchema(
                id=mode_id,
                title=mode.title,
                description=mode.description if mode.description else None,
                tags=list(mode.tags) if mode.tags else None,
                runs=dict(mode.runs) if mode.runs else None,
            )
            modes_list.append(mode_schema)

        mode_set_schema = ModeSetSchema(
            id=set_id,
            title=mode_set.title,
            modes=modes_list,
            integration=mode_set.is_integration if mode_set.is_integration else None,
        )
        mode_sets_list.append(mode_set_schema)

    # Sort mode-sets by id for stable output
    mode_sets_list.sort(key=lambda x: x.id)

    # Convert tag-sets
    tag_sets_list = []
    for set_id, tag_set in adaptive_model.tag_sets.items():
        tags_list = []
        for tag_id, tag in tag_set.tags.items():
            tag_schema = TagSchema(
                id=tag_id,
                title=tag.title,
                description=tag.description if tag.description else None,
            )
            tags_list.append(tag_schema)

        tag_set_schema = TagSetSchema(
            id=set_id,
            title=tag_set.title,
            tags=tags_list,
        )
        tag_sets_list.append(tag_set_schema)

    # Sort tag-sets by id for stable output
    tag_sets_list.sort(key=lambda x: x.id)

    return SectionInfo(
        name=name,
        **{"mode-sets": mode_sets_list, "tag-sets": tag_sets_list}
    )


__all__ = [
    "SectionService",
    "SectionLocation",
    "ScopeIndex",
    "SectionNotFoundError",
    "list_sections",
    "SectionsList",
    "SectionInfo",
]
