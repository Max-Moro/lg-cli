from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Set, Tuple

from ..config.paths import cfg_root

# Унифицированные суффиксы документов
TPL_SUFFIX = ".tpl.md"
CTX_SUFFIX = ".ctx.md"


# ---------------------------- Tokens/Placeholders ---------------------------- #

class TemplateTokens:
    """
    Минимальный парсер плейсхолдеров по семантике:
      - разрешаем буквы/цифры/подчёркивание/дефис/слеш и двоеточие в идентификаторах
      - добавляем `@`, `[` и `]` для локаторов вида `tpl@child:res` и `tpl@[child]:res`
      - распознаём `${name}` и `$name`
    """
    _idpattern = r"[A-Za-z0-9_@:/\-\[\]\.]+"
    _pattern = re.compile(
        r"""
        \$\{
            (?P<braced>""" + _idpattern + r""")
        \}
        |
        \$
            (?P<name>""" + _idpattern + r""")
        """,
        re.VERBOSE,
    )

    @classmethod
    def iter_matches(cls, text: str) -> Iterable[re.Match]:
        return cls._pattern.finditer(text)

    @classmethod
    def placeholders(cls, text: str) -> Set[str]:
        out: Set[str] = set()
        for m in cls.iter_matches(text):
            name = m.group("braced") or m.group("name")
            if name:
                out.add(name)
        return out


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
    return cfg


def load_from_cfg(cfg_root: Path, resource: str, *, suffix: str) -> Tuple[Path, str]:
    """
    Единая загрузка файла из lg-cfg/: <cfg_root>/<resource><suffix>.
    """
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


def context_path(root: Path, name: str) -> Path:
    """Путь к контексту: lg-cfg/<name>.ctx.md (поддиректории поддерживаются)."""
    return cfg_root(root) / f"{name}{CTX_SUFFIX}"


def load_context_from(cfg_root: Path, name: str) -> Tuple[Path, str]:
    """Контекст: <cfg_root>/<name>.ctx.md"""
    return load_from_cfg(cfg_root, name, suffix=CTX_SUFFIX)


def load_template_from(cfg_root: Path, name: str) -> Tuple[Path, str]:
    """Шаблон: <cfg_root>/<name>.tpl.md"""
    return load_from_cfg(cfg_root, name, suffix=TPL_SUFFIX)


def parse_tpl_locator(ph: str, *, current_cfg_root: Path, repo_root: Path) -> Tuple[Path, str]:
    """Совместимость: парсер specifically для шаблонов ('tpl')."""
    loc = parse_locator(ph, expected_kind="tpl")
    cfg = resolve_cfg_root(loc.origin, current_cfg_root=current_cfg_root, repo_root=repo_root)
    return cfg, loc.resource


def parse_ctx_locator(ph: str, *, current_cfg_root: Path, repo_root: Path) -> Tuple[Path, str]:
    """Совместимость: парсер specifically для контекстов ('ctx')."""
    loc = parse_locator(ph, expected_kind="ctx")
    cfg = resolve_cfg_root(loc.origin, current_cfg_root=current_cfg_root, repo_root=repo_root)
    return cfg, loc.resource
