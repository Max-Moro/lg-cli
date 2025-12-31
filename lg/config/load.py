from __future__ import annotations

from pathlib import Path
from typing import Dict

from .model import Config
from .paths import cfg_root
from ..section import list_sections, list_sections_peek
from ..section.model import SectionCfg
from ..cache.fs_cache import Cache
from ..version import tool_version
from ..migrate import ensure_cfg_actual
from ..section.service import SectionService


def load_config(root: Path) -> Config:
    """
    Load configuration with all sections.

    This is a compatibility wrapper. For lazy loading, use SectionService directly.

    Args:
        root: Repository root path

    Returns:
        Config with all sections loaded
    """
    base = cfg_root(root)
    if not base.is_dir():
        raise RuntimeError(f"Config directory not found: {base}")

    # Ensure migrations are up to date
    ensure_cfg_actual(base)

    # Create temporary service for loading
    cache = Cache(root, enabled=None, fresh=False, tool_version=tool_version())
    service = SectionService(root, cache)

    # Get all section names
    section_names = service.list_sections(root)

    # Load all sections (for backward compatibility)
    sections: Dict[str, SectionCfg] = {}
    for name in section_names:
        # Find and load section
        location = service.find_section(name, "", root)
        sections[name] = service.load_section(location)

    return Config(sections=sections)


# Re-export from section module
__all__ = ["load_config", "list_sections", "list_sections_peek"]
