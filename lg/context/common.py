from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from ..config.paths import cfg_root
from ..migrate import ensure_cfg_actual

# Унифицированные суффиксы документов
TPL_SUFFIX = ".tpl.md"
CTX_SUFFIX = ".ctx.md"


# ---------------------------- Locators (generic) ----------------------------- #

@dataclass(frozen=True)
class Locator:
    """Унифицированный локатор: kind + (origin, resource)."""
    kind: str         # "tpl" | "ctx"
    origin: str       # "self" или repo-relative путь (POSIX, без "lg-cfg" в конце)
    resource: str     # имя внутри lg-cfg (например "docs/guide" или "core-src")


def _ensure_inside_repo(path: Path, repo_root: Path) -> None:
    """Безопасность: путь обязан быть внутри репозитория."""
    try:
        path.resolve().relative_to(repo_root.resolve())
    except Exception:
        raise RuntimeError(f"Resolved path escapes repository: {path} not under {repo_root}")


def _split_at(s: str, sep: str) -> Tuple[str, str]:
    """Безопасный split по первому вхождению sep; если нет — ошибка."""
    i = s.find(sep)
    if i < 0:
        raise RuntimeError(f"Invalid locator (missing '{sep}'): {s}")
    return s[:i], s[i + len(sep):]


def parse_locator(ph: str, expected_kind: str) -> Locator:
    """
    Универсальный парсер локаторов для kind == expected_kind.
    Поддерживаем три формы:
      • '{kind}:name'                 → origin=self
      • '{kind}@origin:name'          → явный origin
      • '{kind}@[origin]:name'        → скобочная origin с ':' внутри
    Пример: 'tpl:docs/guide', 'tpl@apps/web:docs/guide', 'tpl@[apps/web]:x:y'
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
        left, resource = _split_at(ph, "]:")
        resource = resource.strip()
        origin = left[len(expected_kind) + 2 :]  # после '{kind}@['
        if not origin:
            raise RuntimeError(f"Empty origin in {expected_kind} locator: {ph}")
        if not resource:
            raise RuntimeError(f"Invalid locator (empty resource): {ph}")
        return Locator(kind=expected_kind, origin=origin, resource=resource)

    # Классическая адресная форма: '{kind}@origin:name'
    if ph.startswith(f"{expected_kind}@"):
        left, resource = _split_at(ph, ":")
        resource = resource.strip()
        origin = left[len(expected_kind) + 1 :]  # после '{kind}@'
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
    # Перед любой загрузкой из чужого lg-cfg/ — актуализировать
    ensure_cfg_actual(cfg)
    return cfg


def load_from_cfg(cfg_root: Path, resource: str, *, suffix: str) -> Tuple[Path, str]:
    """
    Единая загрузка файла из lg-cfg/: <cfg_root>/<resource><suffix>.
    """
    ensure_cfg_actual(cfg_root)
    p = (cfg_root / f"{resource}{suffix}").resolve()
    if not p.is_file():
        raise RuntimeError(f"Resource not found: {p}")
    return p, p.read_text(encoding="utf-8", errors="ignore")


# ---------------------- Public helpers & compatibility ----------------------- #

def list_contexts(root: Path) -> List[str]:
    """
    Перечислить доступные контексты (ТОЛЬКО *.ctx.md) относительно lg-cfg/.
    """
    base = cfg_root(root)
    if not base.is_dir():
        return []
    out: List[str] = []
    for p in base.rglob(f"*{CTX_SUFFIX}"):
        rel = p.relative_to(base).as_posix()
        out.append(rel[: -len(CTX_SUFFIX)])
    out.sort()
    return out


def load_context_from(cfg_root: Path, name: str) -> Tuple[Path, str]:
    """Контекст: <cfg_root>/<name>.ctx.md"""
    return load_from_cfg(cfg_root, name, suffix=CTX_SUFFIX)


def load_template_from(cfg_root: Path, name: str) -> Tuple[Path, str]:
    """Шаблон: <cfg_root>/<name>.tpl.md"""
    return load_from_cfg(cfg_root, name, suffix=TPL_SUFFIX)
