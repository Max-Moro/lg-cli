from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from .common import TemplateTokens, parse_tpl_locator, load_template_from, context_path
from ..config import Config
from ..config.paths import cfg_root


# --------------------------- Internal walkers --------------------------- #

def _collect_sections_counts_from_template(
    *,
    repo_root: Path,
    cfg_root_current: Path,
    template_name: str,
    stack: List[Tuple[Path, str]] | None = None,
) -> Dict[str, int]:
    """
    Рекурсивно обходит ШАБЛОН (.tpl.md) и его вложения `${tpl:...}` / `${tpl@...:...}`,
    собирая кратности секций. Стек отслеживает цикл по паре (cfg_root, template_name).
    """
    stack = stack or []
    marker = (cfg_root_current, template_name)
    if marker in stack:
        cycle = " → ".join([f"{p.as_posix()}::{n}" for p, n in stack] + [f"{cfg_root_current.as_posix()}::{template_name}"])
        raise RuntimeError(f"Template cycle detected: {cycle}")

    _, text = load_template_from(cfg_root_current, template_name)
    stack.append(marker)

    counts: Dict[str, int] = {}
    for m in TemplateTokens.iter_matches(text):
        ph = m.group("braced") or m.group("name") or ""
        if not ph:
            continue

        if ph.startswith("tpl:"):
            child = ph[4:]
            child_counts = _collect_sections_counts_from_template(
                repo_root=repo_root,
                cfg_root_current=cfg_root_current,
                template_name=child,
                stack=stack,
            )
            for k, v in child_counts.items():
                counts[k] = counts.get(k, 0) + int(v)
            continue

        if ph.startswith("tpl@"):
            child_cfg_root, child_name = parse_tpl_locator(ph, current_cfg_root=cfg_root_current, repo_root=repo_root)
            child_counts = _collect_sections_counts_from_template(
                repo_root=repo_root,
                cfg_root_current=child_cfg_root,
                template_name=child_name,
                stack=stack,
            )
            for k, v in child_counts.items():
                counts[k] = counts.get(k, 0) + int(v)
            continue

        # Иначе — это секционный плейсхолдер (пока без адресности @child)
        counts[ph] = counts.get(ph, 0) + 1

    stack.pop()
    return counts


def _collect_sections_counts_for_context(
    *,
    root: Path,
    context_name: str,
) -> Dict[str, int]:
    """
    Обходит КОНТЕКСТ (.ctx.md): парсит плейсхолдеры и раскрывает вклад секций,
    делегируя разбор вложенных шаблонов в _collect_sections_counts_from_template(...).
    """
    cp = context_path(root, context_name)
    if not cp.is_file():
        raise RuntimeError(f"Context not found: {cp}")

    text = cp.read_text(encoding="utf-8", errors="ignore")
    base_cfg = cfg_root(root)

    counts: Dict[str, int] = {}
    for m in TemplateTokens.iter_matches(text):
        ph = m.group("braced") or m.group("name") or ""
        if not ph:
            continue

        if ph.startswith("tpl:"):
            child = ph[4:]
            tpl_counts = _collect_sections_counts_from_template(
                repo_root=root,
                cfg_root_current=base_cfg,
                template_name=child,
                stack=[],
            )
            for k, v in tpl_counts.items():
                counts[k] = counts.get(k, 0) + int(v)
            continue

        if ph.startswith("tpl@"):
            child_cfg_root, child_name = parse_tpl_locator(ph, current_cfg_root=base_cfg, repo_root=root)
            tpl_counts = _collect_sections_counts_from_template(
                repo_root=root,
                cfg_root_current=child_cfg_root,
                template_name=child_name,
                stack=[],
            )
            for k, v in tpl_counts.items():
                counts[k] = counts.get(k, 0) + int(v)
            continue

        # Иначе — секция верхнего уровня
        counts[ph] = counts.get(ph, 0) + 1

    return counts


# --------------------------- Public API --------------------------- #

from ..types import ContextSpec, SectionUsage  # placed here to avoid circulars


def resolve_context(name_or_sec: str, run_ctx) -> ContextSpec:
    """
    Унифицированный резолвер:
      • ctx:<name> → ищем контекст в lg-cfg/<name>.ctx.md
      • sec:<id>   → виртуальный контекст для секции <id> (канонический ID текущего lg-cfg)
      • <name>     → сначала ctx:<name>, иначе sec:<name>
    (В этой итерации адресные секции @child пока не поддерживаются,
     адресные tpl уже поддерживаются и учитываются в подсчёте кратностей.)
    """
    root = run_ctx.root
    cfg: Config = run_ctx.config  # noqa: F841  (может использоваться в будущих версиях)
    kind = "auto"
    name = name_or_sec.strip()

    if name.startswith("ctx:"):
        kind, name = "context", name[4:]
    elif name.startswith("sec:"):
        kind, name = "section", name[4:]

    if kind in ("auto", "context"):
        cp = context_path(root, name)
        if cp.is_file():
            sections = _collect_sections_counts_for_context(root=root, context_name=name)
            return ContextSpec(
                kind="context",
                name=name,
                sections=SectionUsage(by_name=sections or {}),
            )
        if kind == "context":
            raise RuntimeError(f"Context not found: {cp}")

    # Секция как виртуальный контекст текущего lg-cfg
    if name not in run_ctx.config.sections:
        raise RuntimeError(f"Section '{name}' not found in config")
    return ContextSpec(
        kind="section",
        name=name,
        sections=SectionUsage(by_name={name: 1}),
    )
