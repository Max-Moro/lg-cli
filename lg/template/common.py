"""
Helper functions for loading templates and contexts.

Supports addressing and cascading includes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

# Unified document suffixes
TPL_SUFFIX = ".tpl.md"
CTX_SUFFIX = ".ctx.md"


def merge_origins(base_origin: str | None, node_origin: str | None) -> str:
    """
    Merges base origin from stack with origin from node.

    Logic:
    - Ignores None, empty strings, and "self"
    - If both are ignored → "self"
    - If one is ignored → returns the other
    - If both are valid → merges with "/" (base_origin/node_origin)

    Args:
        base_origin: Base origin from context stack
        node_origin: Origin from AST node

    Returns:
        Resulting effective origin
    """
    def _is_empty(origin: str | None) -> bool:
        """Checks if origin is empty or 'self'."""
        return not origin or origin == "self"

    # Normalize input values
    base = (base_origin or "").strip()
    node = (node_origin or "").strip()

    # Both empty → self
    if _is_empty(base) and _is_empty(node):
        return "self"

    # Only base is valid
    if _is_empty(node):
        return base if not _is_empty(base) else "self"

    # Only node is valid
    if _is_empty(base):
        return node if not _is_empty(node) else "self"

    # Both are valid → merge them
    return f"{base}/{node}"


@dataclass(frozen=True)
class Locator:
    """Unified locator: kind + (origin, resource)."""
    kind: str         # "tpl" | "ctx"
    origin: str       # "self" or repo-relative path (POSIX, no "lg-cfg" at end)
    resource: str     # name inside lg-cfg (e.g., "docs/guide" or "core-src")


def parse_locator(ph: str, expected_kind: str) -> Locator:
    """
    Universal locator parser for kind == expected_kind.
    Supports three forms:
      • '{kind}:name'                 → origin=self
      • '{kind}@origin:name'          → explicit origin
      • '{kind}@[origin]:name'        → bracketed origin with ':' inside
    """
    if not ph.startswith(expected_kind):
        raise RuntimeError(f"Not a {expected_kind} locator: {ph}")

    # Local form: '{kind}:name'
    if ph.startswith(f"{expected_kind}:"):
        resource = ph[len(expected_kind) + 1 :].strip()
        if not resource:
            raise RuntimeError(f"Invalid locator (empty resource): {ph}")
        return Locator(kind=expected_kind, origin="self", resource=resource)

    # Bracketed form: '{kind}@[origin]:name'
    if ph.startswith(f"{expected_kind}@["):
        close_bracket = ph.find("]:")
        if close_bracket < 0:
            raise RuntimeError(f"Invalid locator (missing ']:' ): {ph}")
        origin = ph[len(expected_kind) + 2:close_bracket]
        resource = ph[close_bracket + 2:].strip()
        if not origin:
            raise RuntimeError(f"Empty origin in {expected_kind} locator: {ph}")
        if not resource:
            raise RuntimeError(f"Invalid locator (empty resource): {ph}")
        return Locator(kind=expected_kind, origin=origin, resource=resource)

    # Classic addressing form: '{kind}@origin:name'
    if ph.startswith(f"{expected_kind}@"):
        colon_pos = ph.find(":", len(expected_kind) + 1)
        if colon_pos < 0:
            raise RuntimeError(f"Invalid locator (missing ':'): {ph}")
        origin = ph[len(expected_kind) + 1:colon_pos]
        resource = ph[colon_pos + 1:].strip()
        if not origin:
            raise RuntimeError(f"Empty origin in {expected_kind} locator: {ph}")
        if not resource:
            raise RuntimeError(f"Invalid locator (empty resource): {ph}")
        return Locator(kind=expected_kind, origin=origin, resource=resource)

    raise RuntimeError(f"Unsupported {expected_kind} locator: {ph}")


def resolve_cfg_root(origin: str, *, current_cfg_root: Path, repo_root: Path) -> Path:
    """
    Transforms origin → absolute path to lg-cfg/ directory.
    origin == 'self' → current cfg_root, otherwise '<repo_root>/<origin>/lg-cfg'.
    """
    if origin == "self":
        cfg = current_cfg_root
    else:
        cfg = (repo_root / origin / "lg-cfg").resolve()
        _ensure_inside_repo(cfg, repo_root)
    if not cfg.is_dir():
        raise RuntimeError(f"Child lg-cfg not found: {cfg}")
    return cfg


def _ensure_inside_repo(path: Path, repo_root: Path) -> None:
    """Security: path must be inside the repository."""
    try:
        path.resolve().relative_to(repo_root.resolve())
    except Exception:
        raise RuntimeError(f"Resolved path escapes repository: {path} not under {repo_root}")


def load_from_cfg(cfg_root: Path, resource: str, *, suffix: str) -> Tuple[Path, str]:
    """
    Unified loading of file from lg-cfg/: <cfg_root>/<resource><suffix>.
    """
    from ..migrate import ensure_cfg_actual
    ensure_cfg_actual(cfg_root)
    p = (cfg_root / f"{resource}{suffix}").resolve()
    if not p.is_file():
        raise RuntimeError(f"Resource not found: {p}")
    return p, p.read_text(encoding="utf-8", errors="ignore")


def load_context_from(cfg_root: Path, name: str) -> Tuple[Path, str]:
    """Context: <cfg_root>/<name>.ctx.md"""
    return load_from_cfg(cfg_root, name, suffix=CTX_SUFFIX)


def load_template_from(cfg_root: Path, name: str) -> Tuple[Path, str]:
    """Template: <cfg_root>/<name>.tpl.md"""
    return load_from_cfg(cfg_root, name, suffix=TPL_SUFFIX)


def list_contexts(root: Path) -> List[str]:
    """
    List available contexts (ONLY *.ctx.md) relative to lg-cfg/.
    """
    from ..config.paths import cfg_root
    base = cfg_root(root)
    if not base.is_dir():
        return []
    out: List[str] = []
    for p in base.rglob(f"*{CTX_SUFFIX}"):
        rel = p.relative_to(base).as_posix()
        out.append(rel[: -len(CTX_SUFFIX)])
    out.sort()
    return out


__all__ = [
    "Locator",
    "parse_locator", 
    "resolve_cfg_root",
    "load_context_from",
    "load_template_from",
    "list_contexts",
    "merge_origins",
    "TPL_SUFFIX",
    "CTX_SUFFIX"
]