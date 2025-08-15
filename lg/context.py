from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path
from string import Template as _BaseTemplate
from typing import Dict, List, Set

from lg.config import DEFAULT_CONFIG_DIR
from lg.core.cache import Cache
from lg.core.generator import generate_listing


class ContextTemplate(_BaseTemplate):
    """
    Расширяем стандартный Template, чтобы в именах плейсхолдеров
    разрешались буквы, цифры, подчёркивания и дефисы (например: core-model-src).
    Разрешаем в идентификаторах двоеточие и слеш, чтобы поддержать `${tpl:docs/arch}`.
    """
    idpattern = r'[A-Za-z0-9_:/-]+'

def _load_template(root: Path, name: str) -> tuple[Path, ContextTemplate]:
    """
    Общая загрузка шаблона: проверка существования файла и парсинг в ContextTemplate.
    """
    tpl_path = _template_path(root, name)
    if not tpl_path.is_file():
        raise RuntimeError(f"Template not found: {tpl_path}")
    text = tpl_path.read_text(encoding="utf-8")
    return tpl_path, ContextTemplate(text)

def _ensure_section_exists(section: str, configs: Dict[str, object]) -> None:
    """Raise a RuntimeError if section is not present in configs mapping."""
    if section not in configs:
        available = ", ".join(sorted(configs.keys()))
        raise RuntimeError(
            f"Section '{section}' not in configs mapping "
            f"(available: {available})"
        )

def collect_sections_for_context(
    context_name: str,
    *,
    root: Path,
    configs: Dict[str, object],
    stack: List[str] | None = None,
) -> Set[str]:
    """Собрать имена секций, используемых в шаблоне и его вложениях (${tpl:...})."""
    stack = stack or []
    if context_name in stack:
        cycle = " → ".join(stack + [context_name])
        raise RuntimeError(f"Template cycle detected: {cycle}")

    tpl_path, tpl = _load_template(root, context_name)
    stack.append(context_name)

    used: Set[str] = set()
    for placeholder in _collect_placeholders(tpl):
        if placeholder.startswith("tpl:"):
            child = placeholder[4:]
            used |= collect_sections_for_context(child, root=root, configs=configs, stack=stack)
        else:
            _ensure_section_exists(placeholder, configs)
            used.add(placeholder)
    stack.pop()
    return used

def collect_sections_with_counts(
    context_name: str,
    *,
    root: Path,
    configs: Dict[str, object],
    stack: List[str] | None = None,
) -> Dict[str, int]:
    """Вернуть кратности использования секций в шаблоне (учитывает `${tpl:...}`)."""
    stack = stack or []
    if context_name in stack:
        cycle = " → ".join(stack + [context_name])
        raise RuntimeError(f"Template cycle detected: {cycle}")

    tpl_path, tpl = _load_template(root, context_name)
    stack.append(context_name)

    counts: Dict[str, int] = {}
    for placeholder in _collect_placeholders(tpl):
        if placeholder.startswith("tpl:"):
            child = placeholder[4:]
            child_counts = collect_sections_with_counts(child, root=root, configs=configs, stack=stack)
            for k, v in child_counts.items():
                counts[k] = counts.get(k, 0) + int(v)
        else:
            _ensure_section_exists(placeholder, configs)
            counts[placeholder] = counts.get(placeholder, 0) + 1
    stack.pop()
    return counts

def generate_context(
    context_name: str,
    configs: Dict[str, object],
    list_only: bool = False,
    cache: Cache | None = None,
) -> None:
    """Публичная точка входа – печатает результат в stdout."""
    root = Path.cwd()
    rendered = _render_template(
        context_name,
        root=root,
        configs=configs,
        list_only=list_only,
        stack=[],
        cache=cache,
    )
    sys.stdout.write(rendered)


# --------------------------------------------------------------------------- #
# ↓↓↓  внутренности: рекурсивный рендер с защитой от циклов  ↓↓↓
# --------------------------------------------------------------------------- #

def _template_path(root: Path, name: str) -> Path:
    """`docs/arch` → <root>/lg-cfg/contexts/docs/arch.tpl.md"""
    return root / DEFAULT_CONFIG_DIR / "contexts" / f"{name}.tpl.md"

def list_context_names(root: Path) -> List[str]:
    """
    Рекурсивно найти все шаблоны *.tpl.md внутри lg-cfg/contexts/
    и вернуть их имена в виде относительных путей без суффикса (e.g. 'docs/arch').
    """
    base = root / DEFAULT_CONFIG_DIR / "contexts"
    if not base.is_dir():
        return []
    names: List[str] = []
    for p in base.rglob("*.tpl.md"):
        rel = p.relative_to(base).as_posix()
        if rel.endswith(".tpl.md"):
            names.append(rel[:-7])  # срезаем '.tpl.md'
    names.sort()
    return names

def _collect_placeholders(template: ContextTemplate) -> Set[str]:
    """Возвращает идентификаторы из шаблона (named + braced)."""
    ph: Set[str] = set()
    for esc, name, braced, invalid in template.pattern.findall(template.template):
        if name:
            ph.add(name)
        elif braced:
            ph.add(braced)
    return ph


def _render_template(
    context_name: str,
    *,
    root: Path,
    configs: Dict[str, object],
    list_only: bool,
    stack: List[str],
    cache: Cache | None = None,
) -> str:
    # 1. цикл?
    if context_name in stack:
        cycle = " → ".join(stack + [context_name])
        raise RuntimeError(f"Template cycle detected: {cycle}")

    tpl_path, tpl = _load_template(root, context_name)
    stack.append(context_name)

    mapping: Dict[str, str] = {}
    for placeholder in _collect_placeholders(tpl):
        # 2. вложенный шаблон `${tpl:...}`
        if placeholder.startswith("tpl:"):
            child_name = placeholder[4:]
            mapping[placeholder] = _render_template(
                child_name,
                root=root,
                configs=configs,
                list_only=list_only,
                stack=stack,
                cache=cache,
            )
            continue

        # 3. секция из config.yaml
        _ensure_section_exists(placeholder, configs)

        cfg = configs[placeholder]
        buf = StringIO()
        stdout_orig = sys.stdout
        sys.stdout = buf
        try:
            # для list_only кэш не влияет; для реального рендера — ускоряет
            generate_listing(root=root, cfg=cfg, mode="all", list_only=list_only, cache=cache)
        finally:
            sys.stdout = stdout_orig

        content = buf.getvalue().strip()
        if not content:
            content = "*(файлы отсутствуют)*"
        mapping[placeholder] = content

    stack.pop()
    return tpl.substitute(mapping)
