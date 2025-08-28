from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Set, Tuple

from ..config.paths import context_path


class TemplateTokens:
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
    def iter_matches(cls, text: str) -> Iterable[re.Match]:
        return cls.pattern.finditer(text)

    @classmethod
    def placeholders(cls, text: str) -> Set[str]:
        out: Set[str] = set()
        for m in cls.iter_matches(text):
            name = m.group("braced") or m.group("name")
            if name:
                out.add(name)
        return out


def _ensure_inside_repo(path: Path, repo_root: Path) -> None:
    """
    Безопасность: не позволяем выходить за пределы репозитория (.., symlink-tricks).
    """
    try:
        path.resolve().relative_to(repo_root.resolve())
    except Exception:
        raise RuntimeError(f"Resolved path escapes repository: {path} not under {repo_root}")


def parse_tpl_locator(ph: str, *, current_cfg_root: Path, repo_root: Path) -> Tuple[Path, str]:
    """
    Разбор локатора шаблона:
      • 'tpl:foo/bar'             -> (current_cfg_root, 'foo/bar')
      • 'tpl@apps/web:docs/guide' -> (repo_root/apps/web/lg-cfg, 'docs/guide')
      • 'tpl@[apps/web]:foo'      -> (repo_root/apps/web/lg-cfg, 'foo')
    """
    if not ph.startswith("tpl"):
        raise RuntimeError(f"Not a template locator: {ph}")

    # Локальная форма (обратная совместимость)
    if ph.startswith("tpl:"):
        return current_cfg_root, ph[4:]

    # Скобочная форма tpl@[ORIGIN]:NAME
    if ph.startswith("tpl@["):
        close = ph.find("]:")
        if close < 0:
            raise RuntimeError(f"Invalid tpl locator (missing ']:' ): {ph}")
        origin = ph[5:close]
        name = ph[close + 2 :]
        if not origin:
            raise RuntimeError(f"Empty origin in tpl locator: {ph}")
        cfg = (repo_root / origin / "lg-cfg").resolve()
        _ensure_inside_repo(cfg, repo_root)
        if not cfg.is_dir():
            raise RuntimeError(f"Child lg-cfg not found: {cfg}")
        return cfg, name

    # Классическая адресная форма tpl@ORIGIN:NAME
    if ph.startswith("tpl@"):
        colon = ph.find(":")
        if colon < 0:
            raise RuntimeError(f"Invalid tpl locator (missing ':'): {ph}")
        origin = ph[4:colon]
        name = ph[colon + 1 :]
        if not origin:
            raise RuntimeError(f"Empty origin in tpl locator: {ph}")
        cfg = (repo_root / origin / "lg-cfg").resolve()
        _ensure_inside_repo(cfg, repo_root)
        if not cfg.is_dir():
            raise RuntimeError(f"Child lg-cfg not found: {cfg}")
        return cfg, name

    raise RuntimeError(f"Unsupported tpl locator: {ph}")


def load_template_from(cfg_root: Path, name: str) -> Tuple[Path, str]:
    """
    Читает шаблон <cfg_root>/<name>.tpl.md.
    """
    p = (cfg_root / f"{name}.tpl.md").resolve()
    if not p.is_file():
        raise RuntimeError(f"Template not found: {p}")
    return p, p.read_text(encoding="utf-8", errors="ignore")


def load_context_text(repo_root: Path, name: str) -> str:
    """
    Контексты (.ctx.md) всегда читаем из верхнего (self) cfg-root: lg-cfg/<name>.ctx.md.
    """
    p = context_path(repo_root, name)
    return p.read_text(encoding="utf-8", errors="ignore")
