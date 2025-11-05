"""
Вспомогательные функции для загрузки шаблонов и контекстов.

Поддержка адресности и каскадных включений.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

# Унифицированные суффиксы документов  
TPL_SUFFIX = ".tpl.md"
CTX_SUFFIX = ".ctx.md"


def merge_origins(base_origin: str | None, node_origin: str | None) -> str:
    """
    Склеивает базовый origin из стека с origin из узла.

    Логика:
    - Игнорирует None, пустые строки и "self"
    - Если оба игнорируются → "self"
    - Если один игнорируется → возвращает другой
    - Если оба валидны → склеивает через "/" (base_origin/node_origin)

    Args:
        base_origin: Базовый origin из стека контекста
        node_origin: Origin из узла AST

    Returns:
        Результирующий эффективный origin
    """
    def _is_empty(origin: str | None) -> bool:
        """Проверяет, является ли origin пустым или "self"."""
        return not origin or origin == "self"

    # Нормализуем входные значения
    base = (base_origin or "").strip()
    node = (node_origin or "").strip()

    # Оба пусты → self
    if _is_empty(base) and _is_empty(node):
        return "self"

    # Только base валиден
    if _is_empty(node):
        return base if not _is_empty(base) else "self"

    # Только node валиден
    if _is_empty(base):
        return node if not _is_empty(node) else "self"

    # Оба валидны → склеиваем
    return f"{base}/{node}"


@dataclass(frozen=True)
class Locator:
    """Унифицированный локатор: kind + (origin, resource)."""
    kind: str         # "tpl" | "ctx"
    origin: str       # "self" или repo-relative путь (POSIX, без "lg-cfg" в конце)
    resource: str     # имя внутри lg-cfg (например "docs/guide" или "core-src")


def parse_locator(ph: str, expected_kind: str) -> Locator:
    """
    Универсальный парсер локаторов для kind == expected_kind.
    Поддерживаем три формы:
      • '{kind}:name'                 → origin=self
      • '{kind}@origin:name'          → явный origin
      • '{kind}@[origin]:name'        → скобочная origin с ':' внутри
    """
    if not ph.startswith(expected_kind):
        raise RuntimeError(f"Not a {expected_kind} locator: {ph}")

    # Локальная форма: '{kind}:name'
    if ph.startswith(f"{expected_kind}:"):
        resource = ph[len(expected_kind) + 1 :].strip()
        if not resource:
            raise RuntimeError(f"Invalid locator (empty resource): {ph}")
        return Locator(kind=expected_kind, origin="self", resource=resource)

    # Скобочная форма: '{kind}@[origin]:name'  
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

    # Классическая адресная форма: '{kind}@origin:name'
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
    Превращает origin → абсолютный путь к каталогу lg-cfg/.
    origin == 'self' → текущий cfg_root, иначе '<repo_root>/<origin>/lg-cfg'.
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
    """Безопасность: путь обязан быть внутри репозитория."""
    try:
        path.resolve().relative_to(repo_root.resolve())
    except Exception:
        raise RuntimeError(f"Resolved path escapes repository: {path} not under {repo_root}")


def load_from_cfg(cfg_root: Path, resource: str, *, suffix: str) -> Tuple[Path, str]:
    """
    Единая загрузка файла из lg-cfg/: <cfg_root>/<resource><suffix>.
    """
    from ..migrate import ensure_cfg_actual
    ensure_cfg_actual(cfg_root)
    p = (cfg_root / f"{resource}{suffix}").resolve()
    if not p.is_file():
        raise RuntimeError(f"Resource not found: {p}")
    return p, p.read_text(encoding="utf-8", errors="ignore")


def load_context_from(cfg_root: Path, name: str) -> Tuple[Path, str]:
    """Контекст: <cfg_root>/<name>.ctx.md"""
    return load_from_cfg(cfg_root, name, suffix=CTX_SUFFIX)


def load_template_from(cfg_root: Path, name: str) -> Tuple[Path, str]:
    """Шаблон: <cfg_root>/<name>.tpl.md"""
    return load_from_cfg(cfg_root, name, suffix=TPL_SUFFIX)


def list_contexts(root: Path) -> List[str]:
    """
    Перечислить доступные контексты (ТОЛЬКО *.ctx.md) относительно lg-cfg/.
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