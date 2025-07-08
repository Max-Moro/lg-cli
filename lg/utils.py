"""Общие вспомогательные функции (работа с путями, .gitignore и т. п.)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def read_file_text(path: Path) -> str:
    """Читаем файл целиком в UTF-8 (не падаем на битых байтах)."""
    with path.open(encoding="utf-8", errors="ignore") as f:
        return f.read()


# ---------------------------------------------------------------------------
# .gitignore + собственные шаблоны  → PathSpec
# ---------------------------------------------------------------------------

def build_pathspec(root: Path, extra_patterns: list[str] | None = None):
    """
    Собираем PathSpec из .gitignore + доп-шаблонов.
    Если пакет *pathspec* не установлен, вернём None (вызов должен это учесть).
    """
    patterns: List[str] = []

    gitignore = root / ".gitignore"
    if gitignore.is_file():
        for ln in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                patterns.append(ln)

    if extra_patterns:
        patterns.extend(extra_patterns)

    try:
        import pathspec  # type: ignore
    except ImportError:
        return None

    return pathspec.PathSpec.from_lines(
        pathspec.patterns.GitWildMatchPattern,
        patterns,
    )


# ---------------------------------------------------------------------------
# Рекурсивный обход исходников
# ---------------------------------------------------------------------------

def iter_files(root: Path, extensions: set[str], spec=None) -> Iterable[Path]:
    """
    Итератор всех файлов *root* с требуемыми расширениями.
    • пропускает .git
    • исключает пути, подходящие под PathSpec (если передан)
    """
    root = root.resolve()

    for dirpath, dirnames, filenames in os.walk(root):
        # Не заходим в .git
        if ".git" in dirnames:
            dirnames.remove(".git")

        for fn in filenames:
            p = Path(dirpath, fn)

            if p.suffix.lower() not in extensions:
                continue

            rel_posix = p.relative_to(root).as_posix()
            if spec and spec.match_file(rel_posix):
                continue

            yield p
