from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from .common import (
    TemplateTokens,
    parse_locator,
    load_from_cfg,
    context_path,
    resolve_cfg_root,
    CTX_SUFFIX,
    TPL_SUFFIX,
)
from ..config.paths import cfg_root
from ..types import ContextSpec, SectionRef, CanonSectionId
from ..run_context import RunContext


# --------------------------- Internal helpers --------------------------- #

def _parse_section_placeholder(ph: str, *, current_cfg_root: Path, repo_root: Path) -> Tuple[Path, str]:
    """
    Разбор секционного плейсхолдера:
      - "name"                  -> (@self, "name")
      - "@origin:name"          -> (@origin, "name")
      - "@[origin/with:colon]:n"-> (@origin/with:colon, "n")
    Возвращает (cfg_root, section_name).
    """
    if ph.startswith("@["):
        # @[origin]:name
        close = ph.find("]:")
        if close < 0:
            raise RuntimeError(f"Invalid section locator (missing ']:' ): {ph}")
        origin = ph[2:close]
        name = ph[close + 2 :]
        cfg = resolve_cfg_root(origin, current_cfg_root=current_cfg_root, repo_root=repo_root)
        return cfg, name
    if ph.startswith("@"):
        # @origin:name
        colon = ph.find(":")
        if colon < 0:
            raise RuntimeError(f"Invalid section locator (missing ':'): {ph}")
        origin = ph[1:colon]
        name = ph[colon + 1 :]
        cfg = resolve_cfg_root(origin, current_cfg_root=current_cfg_root, repo_root=repo_root)
        return cfg, name
    # без адресности → self
    return current_cfg_root, ph


def _load_doc(kind: str, cfg_root_current: Path, name: str) -> str:
    """Загрузка документа 'tpl' или 'ctx' по suffix."""
    suffix = TPL_SUFFIX if kind == "tpl" else CTX_SUFFIX
    _p, text = load_from_cfg(cfg_root_current, name, suffix=suffix)
    return text


def _collect_section_refs_from_doc(
    *,
    repo_root: Path,
    cfg_root_current: Path,
    kind: str,               # "tpl" | "ctx"
    name: str,
    stack: List[Tuple[Path, str]] | None = None,
) -> List[SectionRef]:
    """
    Рекурсивно собирает адресные секции из ДОКУМЕНТА (tpl/ctx), поддерживая вложенные tpl/ctx.
    """
    stack = stack or []
    marker = (cfg_root_current, f"{kind}:{name}")
    if marker in stack:
        cycle = " → ".join([f"{p.as_posix()}::{n}" for p, n in stack] + [f"{cfg_root_current.as_posix()}::{kind}:{name}"])
        raise RuntimeError(f"{kind.upper()} cycle detected: {cycle}")

    text = _load_doc(kind, cfg_root_current, name)
    stack.append(marker)
    out: List[SectionRef] = []

    for m in TemplateTokens.iter_matches(text):
        ph = m.group("braced") or m.group("name") or ""
        if not ph:
            continue

        if ph.startswith("tpl:"):
            child = ph[4:]
            out.extend(_collect_section_refs_from_doc(
                repo_root=repo_root, cfg_root_current=cfg_root_current, kind="tpl", name=child, stack=stack
            ))
        elif ph.startswith("tpl@"):
            loc = parse_locator(ph, expected_kind="tpl")
            child_cfg = resolve_cfg_root(loc.origin, current_cfg_root=cfg_root_current, repo_root=repo_root)
            out.extend(_collect_section_refs_from_doc(
                repo_root=repo_root, cfg_root_current=child_cfg, kind="tpl", name=loc.resource, stack=stack
            ))
        elif ph.startswith("ctx:"):
            child = ph[4:]
            out.extend(_collect_section_refs_from_doc(
                repo_root=repo_root, cfg_root_current=cfg_root_current, kind="ctx", name=child, stack=stack
            ))
        elif ph.startswith("ctx@"):
            loc = parse_locator(ph, expected_kind="ctx")
            child_cfg = resolve_cfg_root(loc.origin, current_cfg_root=cfg_root_current, repo_root=repo_root)
            out.extend(_collect_section_refs_from_doc(
                repo_root=repo_root, cfg_root_current=child_cfg, kind="ctx", name=loc.resource, stack=stack
            ))
        else:
            # Секционный плейсхолдер
            cfg, sec_name = _parse_section_placeholder(ph, current_cfg_root=cfg_root_current, repo_root=repo_root)
            scope_dir = cfg.parent.resolve()
            scope_rel = scope_dir.relative_to(repo_root.resolve()).as_posix()
            canon = CanonSectionId(scope_rel=scope_rel if scope_rel != "." else "", name=sec_name)
            out.append(SectionRef(canon=canon, cfg_root=cfg, ph=ph, multiplicity=1))

    stack.pop()
    return out


def _collect_section_refs_for_context(*, root: Path, context_name: str) -> List[SectionRef]:
    """Собирает адресные секции из .ctx (включая вложенные tpl и ctx)."""
    cp = context_path(root, context_name)
    if not cp.is_file():
        raise RuntimeError(f"Context not found: {cp}")
    base_cfg = cfg_root(root)
    out = _collect_section_refs_from_doc(
        repo_root=root, cfg_root_current=base_cfg, kind="ctx", name=context_name, stack=[]
    )
    # агрегация кратностей
    by_canon: Dict[str, SectionRef] = {}
    for r in out:
        key = r.canon.as_key()
        if key in by_canon:
            prev = by_canon[key]
            by_canon[key] = SectionRef(
                cfg_root=prev.cfg_root,
                ph=prev.ph,
                multiplicity=prev.multiplicity + r.multiplicity,
                canon=prev.canon,
            )
        else:
            by_canon[key] = r
    return list(by_canon.values())


# --------------------------- Public API --------------------------- #

def resolve_context(name_or_sec: str, run_ctx: RunContext) -> ContextSpec:
    """
    Унифицированный резолвер:
      • ctx:<name> → ищем контекст в lg-cfg/<name>.ctx.md
      • sec:<id>   → виртуальный контекст для секции <id> (канонический ID текущего lg-cfg)
      • <name>     → сначала ctx:<name>, иначе sec:<name>
    Адресные шаблоны (${tpl@child:...}) и адресные контексты (${ctx@child:...})
    поддерживаются и корректно учитываются в подсчёте кратностей.
    """
    root = run_ctx.root
    kind = "auto"
    name = name_or_sec.strip()

    if name.startswith("ctx:"):
        kind, name = "context", name[4:]
    elif name.startswith("sec:"):
        kind, name = "section", name[4:]

    if kind in ("auto", "context"):
        cp = context_path(root, name)
        if cp.is_file():
            refs = _collect_section_refs_for_context(root=root, context_name=name)
            # Построим карту плейсхолдер → канон (не важно, какой placeholder встретился первым)
            ph2canon: Dict[str, CanonSectionId] = {}
            for r in refs:
                if r.canon:
                    ph2canon[r.ph] = r.canon
            return ContextSpec(
                kind="context",
                name=name,
                section_refs=refs,
                ph2canon=ph2canon,
            )
        if kind == "context":
            raise RuntimeError(f"Context not found: {cp}")

    # секция текущего lg-cfg: канон строим относительно корня репо
    base_cfg = cfg_root(root)
    scope_dir = base_cfg.parent.resolve()
    scope_rel = scope_dir.relative_to(root.resolve()).as_posix()
    canon = CanonSectionId(scope_rel=scope_rel if scope_rel != "." else "", name=name)
    return ContextSpec(
        kind="section",
        name=name,
        section_refs=[SectionRef(canon=canon, cfg_root=cfg_root(root), ph=name, multiplicity=1)],
        ph2canon={name: canon},
    )
