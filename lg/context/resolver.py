from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

from ..config import Config
from ..config.paths import (
    cfg_root,
    context_path,
    CTX_SUFFIX
)
from ..types import ContextSpec, SectionUsage


class _Template:
    """
    Минимальный парсер плейсхолдеров по семантике:
      - разрешаем буквы/цифры/подчёркивание/дефис/слеш и двоеточие в идентификаторах
      - добавляем `@`, `[` и `]` для локаторов вида `tpl@child:res` и `tpl@[child]:res`
      - распознаём `${name}` и `$name`
    """
    idpattern = r"[A-Za-z0-9_@:/\-\[\]\.]+"
    pattern = re.compile(
        r"""
        \$\{
            (?P<braced>""" + idpattern + r""")
        \}
        |
        \$
            (?P<name>""" + idpattern + r""")
        """,
        re.VERBOSE,
    )

    @classmethod
    def placeholders(cls, text: str) -> Set[str]:
        out: Set[str] = set()
        for m in cls.pattern.finditer(text):
            name = m.group("braced") or m.group("name")
            if name:
                out.add(name)
        return out

def list_contexts(root: Path) -> List[str]:
    base = cfg_root(root)
    if not base.is_dir():
        return []
    out: List[str] = []
    for p in base.rglob(f"*{CTX_SUFFIX}"):
        rel = p.relative_to(base).as_posix()
        out.append(rel[: -len(CTX_SUFFIX)])
    out.sort()
    return out

# --------------------------- Resolver --------------------------- #

def _load_template_from(cfg_root: Path, name: str) -> Tuple[Path, str]:
    """
    Локальная загрузка шаблона из указанного cfg_root: <cfg_root>/<name>.tpl.md
    """
    p = (cfg_root / f"{name}.tpl.md").resolve()
    if not p.is_file():
        raise RuntimeError(f"Template not found: {p}")
    return p, p.read_text(encoding="utf-8", errors="ignore")

def _parse_tpl_locator(ph: str, current_cfg_root: Path, repo_root: Path) -> Tuple[Path, str]:
    """
    Разбор локатора шаблона:
      - 'tpl:foo/bar'              -> (current_cfg_root, 'foo/bar')
      - 'tpl@apps/web:docs/guide'  -> (repo_root/apps/web/lg-cfg, 'docs/guide')
      - 'tpl@[apps/web]:foo'       -> (repo_root/apps/web/lg-cfg, 'foo')
    """
    assert ph.startswith("tpl")
    if ph.startswith("tpl:"):
        return current_cfg_root, ph[4:]
    if ph.startswith("tpl@["):
        close = ph.find("]:")
        if close < 0:
            raise RuntimeError(f"Invalid tpl locator (missing ']:' ): {ph}")
        origin = ph[5:close]
        name = ph[close + 2 :]
        if not origin:
            raise RuntimeError(f"Empty origin in tpl locator: {ph}")
        cfg = (repo_root / origin / "lg-cfg").resolve()
        if not cfg.is_dir():
            raise RuntimeError(f"Child lg-cfg not found: {cfg}")
        return cfg, name
    if ph.startswith("tpl@"):
        colon = ph.find(":")
        if colon < 0:
            raise RuntimeError(f"Invalid tpl locator (missing ':'): {ph}")
        origin = ph[4:colon]
        name = ph[colon + 1 :]
        if not origin:
            raise RuntimeError(f"Empty origin in tpl locator: {ph}")
        cfg = (repo_root / origin / "lg-cfg").resolve()
        if not cfg.is_dir():
            raise RuntimeError(f"Child lg-cfg not found: {cfg}")
        return cfg, name
    raise RuntimeError(f"Unsupported tpl locator: {ph}")

def _collect_sections_counts_from_template(
    *,
    repo_root: Path,
    cfg_root_current: Path,
    template_name: str,
    stack: List[Tuple[Path, str]] | None = None,
) -> Dict[str, int]:
    """
    Рекурсивно обходит ШАБЛОН (.tpl.md) и его вложения `${tpl:...}`, собирая кратности секций.
    Стек отслеживает цикл по паре (cfg_root, template_name).
    """
    stack = stack or []
    if (cfg_root_current, template_name) in stack:
        cycle = " → ".join([f"{p.as_posix()}::{n}" for p, n in stack] + [f"{cfg_root_current.as_posix()}::{template_name}"])
        raise RuntimeError(f"Template cycle detected: {cycle}")

    _, text = _load_template_from(cfg_root_current, template_name)
    stack.append((cfg_root_current, template_name))
    counts: Dict[str, int] = {}
    for ph in _Template.placeholders(text):
        if ph.startswith("tpl:"):
            child = ph[4:]
            child_counts = _collect_sections_counts_from_template(
                repo_root=repo_root, cfg_root_current=cfg_root_current, template_name=child, stack=stack
            )
            for k, v in child_counts.items():
                counts[k] = counts.get(k, 0) + int(v)
        elif ph.startswith("tpl@"):
            child_cfg_root, child_name = _parse_tpl_locator(ph, cfg_root_current, repo_root)
            child_counts = _collect_sections_counts_from_template(
                repo_root=repo_root, cfg_root_current=child_cfg_root, template_name=child_name, stack=stack
            )
            for k, v in child_counts.items():
                counts[k] = counts.get(k, 0) + int(v)
        else:
            counts[ph] = counts.get(ph, 0) + 1
    stack.pop()
    return counts

def _collect_sections_counts_for_context(
    *,
    root: Path,
    context_name: str
) -> Dict[str, int]:
    """
    Обходит КОНТЕКСТ (.ctx.md): парсит плейсхолдеры, для `${tpl:...}`
    делегирует разбор в `_collect_sections_counts_from_template(...)`.
    """
    cp = context_path(root, context_name)
    if not cp.is_file():
        raise RuntimeError(f"Context not found: {cp}")
    text = cp.read_text(encoding="utf-8", errors="ignore")
    base_cfg = cfg_root(root)
    counts: Dict[str, int] = {}
    for ph in _Template.placeholders(text):
        if ph.startswith("tpl:"):
            child = ph[4:]
            tpl_counts = _collect_sections_counts_from_template(
                repo_root=root, cfg_root_current=base_cfg, template_name=child, stack=[]
            )
            for k, v in tpl_counts.items():
                counts[k] = counts.get(k, 0) + int(v)
        elif ph.startswith("tpl@"):
            child_cfg_root, child_name = _parse_tpl_locator(ph, base_cfg, root)
            tpl_counts = _collect_sections_counts_from_template(
                repo_root=root, cfg_root_current=child_cfg_root, template_name=child_name, stack=[]
            )
            for k, v in tpl_counts.items():
                counts[k] = counts.get(k, 0) + int(v)
        else:
            counts[ph] = counts.get(ph, 0) + 1
    return counts

# --------------------------- Public API --------------------------- #

def resolve_context(name_or_sec: str, run_ctx) -> ContextSpec:
    """
    Унифицированный резолвер:
      - ctx:<name> → ищем контекст в lg-cfg/<name>.ctx.md
      - sec:<id>   → виртуальный контекст для секции <id> (канонический ID)
      - <name>     → сначала ctx:<name>, иначе sec:<name>
    """
    root = run_ctx.root
    cfg: Config = run_ctx.config
    # нормализуем префиксы
    kind = "auto"
    name = name_or_sec.strip()
    if name.startswith("ctx:"):
        kind, name = "context", name[4:]
    elif name.startswith("sec:"):
        kind, name = "section", name[4:]

    if kind in ("auto", "context"):
        # сначала пробуем как контекст (.ctx.md)
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

    # секция (виртуальный контекст) — проверяем, что такой канонический ID объявлен
    if name not in cfg.sections:
        raise RuntimeError(f"Section '{name}' not found in config")
    return ContextSpec(
        kind="section",
        name=name,
        sections=SectionUsage(by_name={name: 1}),
    )
