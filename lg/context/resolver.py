from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from .common import TemplateTokens, parse_tpl_locator, load_template_from, context_path, resolve_cfg_root
from ..config.paths import cfg_root
from ..run_context import RunContext
from ..types import ContextSpec, SectionRef, CanonSectionId


# --------------------------- Internal walkers --------------------------- #

def _parse_section_placeholder(ph: str, *, current_cfg_root: Path, repo_root: Path) -> Tuple[Path, str]:
    """
    Разбор секционного плейсхолдера:
      - "name"                  -> (@self, "name")
      - "@child:name"           -> (@child, "name")
      - "@[child/with:colon]:n" -> (@child/with:colon, "n")
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

def _collect_section_refs_from_template(
    *,
    repo_root: Path,
    cfg_root_current: Path,
    template_name: str,
    stack: List[Tuple[Path, str]] | None = None,
) -> List[SectionRef]:
    """Собирает список адресных секций из шаблона (учитывает вложенные tpl и tpl@)."""
    stack = stack or []
    marker = (cfg_root_current, template_name)
    if marker in stack:
        cycle = " → ".join([f"{p.as_posix()}::{n}" for p, n in stack] + [f"{cfg_root_current.as_posix()}::{template_name}"])
        raise RuntimeError(f"Template cycle detected: {cycle}")
    _, text = load_template_from(cfg_root_current, template_name)
    stack.append(marker)
    out: List[SectionRef] = []
    for m in TemplateTokens.iter_matches(text):
        ph = m.group("braced") or m.group("name") or ""
        if not ph:
            continue
        if ph.startswith("tpl:"):
            child = ph[4:]
            out.extend(_collect_section_refs_from_template(
                repo_root=repo_root, cfg_root_current=cfg_root_current, template_name=child, stack=stack
            ))
        elif ph.startswith("tpl@"):
            child_cfg_root, child_name = parse_tpl_locator(ph, current_cfg_root=cfg_root_current, repo_root=repo_root)
            out.extend(_collect_section_refs_from_template(
                repo_root=repo_root, cfg_root_current=child_cfg_root, template_name=child_name, stack=stack
            ))
        else:
            cfg, name = _parse_section_placeholder(ph, current_cfg_root=cfg_root_current, repo_root=repo_root)
            # канон
            scope_dir = cfg.parent.resolve()
            try:
                scope_rel = scope_dir.relative_to(repo_root.resolve()).as_posix()
            except Exception:
                scope_rel = ""
            canon = CanonSectionId(scope_rel=scope_rel if scope_rel != "." else "", name=name)
            out.append(SectionRef(cfg_root=cfg, name=name, ph=ph, multiplicity=1, canon=canon))
    stack.pop()
    return out

def _collect_section_refs_for_context(*, root: Path, context_name: str) -> List[SectionRef]:
    """Собирает адресные секции из самого .ctx и его вложенных шаблонов."""
    cp = context_path(root, context_name)
    if not cp.is_file():
        raise RuntimeError(f"Context not found: {cp}")
    text = cp.read_text(encoding="utf-8", errors="ignore")
    base_cfg = cfg_root(root)
    out: List[SectionRef] = []
    for m in TemplateTokens.iter_matches(text):
        ph = m.group("braced") or m.group("name") or ""
        if not ph:
            continue
        if ph.startswith("tpl:"):
            child = ph[4:]
            out.extend(_collect_section_refs_from_template(
                repo_root=root, cfg_root_current=base_cfg, template_name=child, stack=[]
            ))
        elif ph.startswith("tpl@"):
            child_cfg_root, child_name = parse_tpl_locator(ph, current_cfg_root=base_cfg, repo_root=root)
            out.extend(_collect_section_refs_from_template(
                repo_root=root, cfg_root_current=child_cfg_root, template_name=child_name, stack=[]
            ))
        else:
            cfg, name = _parse_section_placeholder(ph, current_cfg_root=base_cfg, repo_root=root)
            # канон
            scope_dir = cfg.parent.resolve()
            try:
                scope_rel = scope_dir.relative_to(root.resolve()).as_posix()
            except Exception:
                scope_rel = ""
            canon = CanonSectionId(scope_rel=scope_rel if scope_rel != "." else "", name=name)
            out.append(SectionRef(cfg_root=cfg, name=name, ph=ph, multiplicity=1, canon=canon))
    # агрегация кратностей
    by_canon: Dict[str, SectionRef] = {}
    for r in out:
        # гарантируем наличие канона (на всякий случай)
        if r.canon is None:
            scope_dir = r.cfg_root.parent.resolve()
            try:
                scope_rel = scope_dir.relative_to(root.resolve()).as_posix()
            except Exception:
                scope_rel = ""
            canon = CanonSectionId(scope_rel=scope_rel if scope_rel != "." else "", name=r.name)
            r = SectionRef(cfg_root=r.cfg_root, name=r.name, ph=r.ph, multiplicity=r.multiplicity, canon=canon)
        key = r.canon.as_key()
        if key in by_canon:
            prev = by_canon[key]
            by_canon[key] = SectionRef(
                cfg_root=prev.cfg_root,
                name=prev.name,
                ph=prev.ph,  # первый встретившийся плейсхолдер оставим для удобной диагностики
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
    (В этой итерации адресные секции @child пока не поддерживаются,
     адресные tpl уже поддерживаются и учитываются в подсчёте кратностей.)
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
            refs = _collect_section_refs_for_context(root=root, context_name=name)
            # Построим карту плейсхолдер → канон (последний wins — не важно, канон один и тот же)
            ph2canon: Dict[str, str] = {}
            for r in refs:
                if r.canon:
                    ph2canon[r.ph] = r.canon.as_key()
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
    try:
        scope_rel = scope_dir.relative_to(root.resolve()).as_posix()
    except Exception:
        scope_rel = ""
    canon = CanonSectionId(scope_rel=scope_rel if scope_rel != "." else "", name=name)
    return ContextSpec(
        kind="section",
        name=name,
        section_refs=[SectionRef(cfg_root=cfg_root(root), name=name, ph=name, multiplicity=1, canon=canon)],
        ph2canon={name: canon.as_key()},
    )
