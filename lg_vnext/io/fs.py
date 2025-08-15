from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Set

import pathspec


def read_text(path: Path) -> str:
    with path.open(encoding="utf-8", errors="ignore") as f:
        return f.read()


def build_gitignore_spec(root: Path) -> Optional[pathspec.PathSpec]:
    """
    Собрать PathSpec из .gitignore. Если .gitignore отсутствует — вернуть None.
    """
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return None
    lines = []
    for ln in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#"):
            lines.append(ln)
    return pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, lines)


def iter_files(
    root: Path,
    *,
    extensions: Set[str],
    spec_git: Optional[pathspec.PathSpec],
    dir_pruner: Optional[Callable[[str], bool]] = None,
) -> Iterable[Path]:
    """
    Рекурсивный итератор по файлам с учётом .gitignore и раннего прунинга директорий.
    Все пути приводятся к rel_posix вне этой функции.
    """
    root = root.resolve()
    for dirpath, dirnames, filenames in os.walk(root):
        # не заходим в .git
        if ".git" in dirnames:
            dirnames.remove(".git")

        # ранний прунинг (in-place модификация dirnames)
        if dir_pruner:
            keep: List[str] = []
            for d in dirnames:
                rel_dir = Path(dirpath, d).resolve().relative_to(root).as_posix()
                # .gitignore может скрыть ветку целиком
                if spec_git and spec_git.match_file(rel_dir + "/"):
                    continue
                if dir_pruner(rel_dir):
                    keep.append(d)
            dirnames[:] = keep

        for fn in filenames:
            p = Path(dirpath, fn)
            if p.suffix.lower() not in extensions:
                # спец-имена без суффикса (README, Dockerfile и т. п.) пусть проходят слоем выше
                if p.name not in {"README", "Dockerfile", "Makefile", "pyproject.toml"}:
                    continue
            rel_posix = p.resolve().relative_to(root).as_posix()
            if spec_git and spec_git.match_file(rel_posix):
                continue
            yield p
