from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

from ..types import ContextSpec, SectionUsage
from ..config.load import Config

# --------------------------- Helpers --------------------------- #

_CFG_DIR = "lg-cfg"
_TPL_SUFFIX = ".tpl.md"
_CTX_SUFFIX = ".ctx.md"


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


def _cfg_root(root: Path) -> Path:
    return (root / _CFG_DIR).resolve()


def _template_path(root: Path, name: str) -> Path:
    # Шаблоны живут прямо под lg-cfg/: <name>.tpl.md (с поддиректориями)
    return _cfg_root(root) / f"{name}{_TPL_SUFFIX}"


def _ctx_path(root: Path, name: str) -> Path:
    # Контексты: <name>.ctx.md под lg-cfg/
    return _cfg_root(root) / f"{name}{_CTX_SUFFIX}"


def list_contexts(root: Path) -> List[str]:
    base = _cfg_root(root)
    if not base.is_dir():
        return []
    out: List[str] = []
    for p in base.rglob(f"*{_CTX_SUFFIX}"):
        rel = p.relative_to(base).as_posix()
        out.append(rel[: -len(_CTX_SUFFIX)])
    out.sort()
    return out

# --------------------------- Resolver --------------------------- #

def _load_template(root: Path, name: str) -> Tuple[Path, str]:
    p = _template_path(root, name)
    if not p.is_file():
        raise RuntimeError(f"Template not found: {p}")
    return p, p.read_text(encoding="utf-8", errors="ignore")

def _collect_sections_counts_from_template(
    *,
    root: Path,
    template_name: str,
    stack: List[str] | None = None,
) -> Dict[str, int]:
    """
    Рекурсивно обходит ШАБЛОН (.tpl.md) и его вложения `${tpl:...}`, собирая кратности секций.
    Стек отслеживает цикл именно по именам шаблонов.
    """
    stack = stack or []
    if template_name in stack:
        cycle = " → ".join(stack + [template_name])
        raise RuntimeError(f"Template cycle detected: {cycle}")

    _, text = _load_template(root, template_name)
    stack.append(template_name)
    counts: Dict[str, int] = {}
    for ph in _Template.placeholders(text):
        if ph.startswith("tpl:"):
            child = ph[4:]
            child_counts = _collect_sections_counts_from_template(root=root, template_name=child, stack=stack)
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
    cp = _ctx_path(root, context_name)
    if not cp.is_file():
        raise RuntimeError(f"Context not found: {cp}")
    text = cp.read_text(encoding="utf-8", errors="ignore")
    counts: Dict[str, int] = {}
    for ph in _Template.placeholders(text):
        if ph.startswith("tpl:"):
            child = ph[4:]
            tpl_counts = _collect_sections_counts_from_template(root=root, template_name=child, stack=[])
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
        cp = _ctx_path(root, name)
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
