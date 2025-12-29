"""
Utilities for rendering templates and creating engines in tests.

Unifies all rendering utilities from various conftest.py files.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Set
from typing import Optional

from lg.cache.fs_cache import Cache
from lg.config.adaptive_loader import AdaptiveConfigLoader, process_adaptive_options
from lg.engine import Engine
from lg.run_context import RunContext
from lg.stats.tokenizer import default_tokenizer
from lg.types import RunOptions
from lg.git import NullVcs
from lg.git.gitignore import GitIgnoreService


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


def make_run_context(root: Path, options: Optional[RunOptions] = None) -> RunContext:
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
    adaptive_loader = AdaptiveConfigLoader(root)

    # Use process_adaptive_options for correct active_tags initialization
    active_tags, mode_options, _ = process_adaptive_options(
        root,
        options.modes,
        options.extra_tags
    )

    # Initialize GitIgnoreService (same pattern as Engine._init_services)
    gitignore = GitIgnoreService(root) if (root / ".git").is_dir() else None

    return RunContext(
        root=root,
        options=options,
        cache=cache,
        vcs=NullVcs(),
        gitignore=gitignore,
        tokenizer=default_tokenizer(),
        adaptive_loader=adaptive_loader,
        mode_options=mode_options,
        active_tags=active_tags
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
    "make_run_options", "make_run_context", "make_engine", "render_template"
]
