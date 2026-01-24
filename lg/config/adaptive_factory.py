"""
Lightweight factory for creating adaptive system services for list commands.
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

from ..cache.fs_cache import Cache
from ..version import tool_version
from ..section import SectionService
from ..addressing import AddressingContext
from ..adaptive.context_resolver import ContextResolver


def create_context_resolver(root: Path) -> Tuple[ContextResolver, Path]:
    """
    Create ContextResolver for list commands.

    Creates minimal services needed for adaptive model resolution
    without full Engine overhead.

    Args:
        root: Repository root

    Returns:
        Tuple of (ContextResolver, cfg_root Path)
    """
    root = root.resolve()
    cfg_root_path = root / "lg-cfg"

    # Create cache
    cache = Cache(root, enabled=None, fresh=False, tool_version=tool_version())

    # Create section service
    section_service = SectionService(root, cache)

    # Create addressing context
    addressing = AddressingContext(
        repo_root=root,
        initial_cfg_root=cfg_root_path,
        section_service=section_service
    )

    # Create context resolver
    resolver = ContextResolver(
        section_service=section_service,
        addressing=addressing,
        cfg_root=cfg_root_path,
    )

    return resolver, cfg_root_path


__all__ = ["create_context_resolver"]
