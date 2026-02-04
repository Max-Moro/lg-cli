"""
Utilities for rendering templates and creating engines in tests.

Unifies all rendering utilities from various conftest.py files.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Set
from typing import Optional

from lg.addressing import AddressingContext
from lg.cache.fs_cache import Cache
from lg.engine import Engine
from lg.run_context import RunContext
from lg.section import SectionService
from lg.stats.tokenizer import default_tokenizer
from lg.types import RunOptions
from lg.git import NullVcs
from lg.git.gitignore import GitIgnoreService
from lg.section.model import SectionCfg


def load_sections(root: Path) -> Dict[str, SectionCfg]:
    """
    Load all sections from a scope (for testing).

    Replaces the deprecated load_config() function.
    Internally uses SectionService for lazy-loading.

    Args:
        root: Scope directory (parent of lg-cfg/)

    Returns:
        Dictionary mapping section_name -> SectionCfg

    Example:
        sections = load_sections(tmp_path)
        section_cfg = sections.get("my-section")
    """
    from lg.section import SectionService

    cache = Cache(root, enabled=None, fresh=False, tool_version="test")
    service = SectionService(root, cache)

    sections: Dict[str, SectionCfg] = {}
    for name in service.list_sections(root):
        _, location = service.find_section(name, "", root)
        sections[name] = service.load_section(location)

    return sections


def make_run_options(
    modes: Optional[Dict[str, str]] = None,
    extra_tags: Optional[Set[str]] = None,
    task_text: Optional[str] = None
) -> RunOptions:
    """
    Creates RunOptions with specified parameters.

    Unified function for all tests.

    Args:
        modes: Dictionary of active modes {modeset: mode}
        extra_tags: Additional tags
        task_text: Current task text

    Returns:
        Configured RunOptions
    """
    return RunOptions(
        modes=modes or {},
        extra_tags=extra_tags or set(),
        task_text=task_text
    )


def make_run_context(
    root: Path,
    options: Optional[RunOptions] = None,
) -> RunContext:
    """
    Creates RunContext for testing.

    Args:
        root: Project root
        options: Execution options

    Returns:
        Configured RunContext
    """
    if options is None:
        options = make_run_options()

    cache = Cache(root, enabled=None, fresh=False, tool_version="test")

    # Initialize GitIgnoreService (same pattern as Engine._init_services)
    gitignore = GitIgnoreService(root) if (root / ".git").is_dir() else None

    # Initialize SectionService and AddressingContext
    section_service = SectionService(root, cache)
    addressing = AddressingContext(
        repo_root=root,
        initial_cfg_root=root / "lg-cfg",
        section_service=section_service
    )

    return RunContext(
        root=root,
        options=options,
        cache=cache,
        vcs=NullVcs(),
        gitignore=gitignore,
        tokenizer=default_tokenizer(),
        addressing=addressing,
    )


def make_engine(root: Path, options: Optional[RunOptions] = None) -> Engine:
    """
    Creates Engine for testing.

    Args:
        root: Project root
        options: Execution options

    Returns:
        Configured Engine
    """
    if options is None:
        options = make_run_options()

    # Temporarily change current directory for Engine
    original_cwd = os.getcwd()
    try:
        os.chdir(root)
        return Engine(options)
    finally:
        os.chdir(original_cwd)


def render_template(root: Path, target: str, options: Optional[RunOptions] = None) -> str:
    """
    Renders a template or section in the specified project.

    Args:
        root: Project root
        target: Rendering target (ctx:name, sec:name or name)
        options: Execution options

    Returns:
        Rendered text
    """
    if options is None:
        options = make_run_options()

    from lg.engine import _parse_target

    # Create engine with correct working directory
    original_cwd = os.getcwd()
    try:
        os.chdir(root)
        engine = Engine(options)
        target_spec = _parse_target(target, root)
        return engine.render_text(target_spec)
    finally:
        os.chdir(original_cwd)


__all__ = [
    "load_sections",
    "make_run_options", "make_run_context", "make_engine", "render_template"
]
