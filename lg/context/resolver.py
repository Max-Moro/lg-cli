from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

from ..types import ContextSpec, SectionUsage
from ..config.load import Config

# --------------------------- Helpers --------------------------- #

_TPL_SUFFIX = ".tpl.md"
_CONTEXTS_DIR = "lg-cfg/contexts"

class _Template:
    """
    Минимальный парсер плейсхолдеров по семантике:
      - разрешаем буквы/цифры/подчёркивание/дефис/слеш и двоеточие в идентификаторах
      - распознаём `${name}` и `$name`
    """
    idpattern = r"[A-Za-z0-9_:/-]+"
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

def _contexts_dir(root: Path) -> Path:
    return (root / _CONTEXTS_DIR).resolve()

def _template_path(root: Path, name: str) -> Path:
    return _contexts_dir(root) / f"{name}.tpl.md"

def list_contexts(root: Path) -> List[str]:
    base = _contexts_dir(root)
    if not base.is_dir():
        return []
    out: List[str] = []
    for p in base.rglob(f"*{_TPL_SUFFIX}"):
        rel = p.relative_to(base).as_posix()
        out.append(rel[: -len(_TPL_SUFFIX)])
    out.sort()
    return out

# --------------------------- Resolver --------------------------- #

def _load_template(root: Path, name: str) -> Tuple[Path, str]:
    p = _template_path(root, name)
    if not p.is_file():
        raise RuntimeError(f"Template not found: {p}")
    return p, p.read_text(encoding="utf-8", errors="ignore")

def _collect_sections_counts_for_context(
    *,
    root: Path,
    context_name: str,
    stack: List[str] | None = None,
) -> Dict[str, int]:
    """
    Рекурсивно обходит шаблон и его вложения `${tpl:...}`, собирает кратности секций.
    """
    stack = stack or []
    if context_name in stack:
        cycle = " → ".join(stack + [context_name])
        raise RuntimeError(f"Template cycle detected: {cycle}")

    _, text = _load_template(root, context_name)
    stack.append(context_name)
    counts: Dict[str, int] = {}
    for ph in _Template.placeholders(text):
        if ph.startswith("tpl:"):
            child = ph[4:]
            child_counts = _collect_sections_counts_for_context(root=root, context_name=child, stack=stack)
            for k, v in child_counts.items():
                counts[k] = counts.get(k, 0) + int(v)
        else:
            counts[ph] = counts.get(ph, 0) + 1
    stack.pop()
    return counts

# --------------------------- Public API --------------------------- #

def resolve_context(name_or_sec: str, run_ctx) -> ContextSpec:
    """
    Унифицированный резолвер:
      - ctx:<name> → ищем шаблон в lg-cfg/contexts/<name>.tpl.md
      - sec:<name> → виртуальный контекст для секции <name>
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
        # сначала пробуем как контекст
        tp = _template_path(root, name)
        if tp.is_file():
            sections = _collect_sections_counts_for_context(root=root, context_name=name)
            return ContextSpec(
                kind="context",
                name=name,
                sections=SectionUsage(by_name=sections or {}),
            )
        if kind == "context":
            raise RuntimeError(f"Context template not found: {tp}")

    # секция (виртуальный контекст) — проверяем, что такая секция объявлена в YAML
    if name not in cfg.sections:
        raise RuntimeError(f"Section '{name}' not found in config")
    return ContextSpec(
        kind="section",
        name=name,
        sections=SectionUsage(by_name={name: 1}),
    )
