from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Set, Optional

from . import VcsProvider


def _git(root: Path, args: list[str]) -> list[str]:
    try:
        out = subprocess.check_output(["git", "-C", str(root), *args], text=True, encoding="utf-8", errors="ignore")
        return [ln.strip() for ln in out.splitlines() if ln.strip()]
    except Exception:
        return []


def _find_merge_base_or_parent(root: Path, target_branch: Optional[str]) -> Optional[str]:
    """
    Находит базовую точку для сравнения с целевой веткой.
    
    Если target_branch указана - ищет merge-base с ней.
    Иначе пытается найти ближайшую родительскую ветку через различные эвристики:
    - origin/main, origin/master
    - upstream/main, upstream/master  
    - main, master (локальные ветки)
    """
    if target_branch:
        # Проверяем, существует ли указанная ветка
        refs = _git(root, ["show-ref", "--verify", f"refs/heads/{target_branch}"])
        if not refs:
            # Пробуем remote ветку
            refs = _git(root, ["show-ref", "--verify", f"refs/remotes/origin/{target_branch}"])
            if refs:
                target_branch = f"origin/{target_branch}"
        
        if refs or target_branch.startswith(("origin/", "upstream/")):
            # Находим merge-base с указанной веткой
            merge_base = _git(root, ["merge-base", "HEAD", target_branch])
            return merge_base[0] if merge_base else target_branch
    
    # Эвристический поиск родительской ветки
    candidates = [
        "origin/main", "origin/master",
        "upstream/main", "upstream/master", 
        "main", "master"
    ]
    
    for candidate in candidates:
        refs = _git(root, ["show-ref", "--verify", f"refs/remotes/{candidate}"])
        if not refs and not candidate.startswith(("origin/", "upstream/")):
            refs = _git(root, ["show-ref", "--verify", f"refs/heads/{candidate}"])
        
        if refs:
            merge_base = _git(root, ["merge-base", "HEAD", candidate])
            if merge_base:
                return merge_base[0]
    
    return None


class GitVcs(VcsProvider):
    """
    Сбор изменённых файлов:
      • git diff --name-only        (unstaged)
      • git diff --name-only --cached (staged)
      • git ls-files --others --exclude-standard (untracked)
    """
    def changed_files(self, root: Path) -> Set[str]:
        s: Set[str] = set()
        s.update(_git(root, ["diff", "--name-only"]))
        s.update(_git(root, ["diff", "--name-only", "--cached"]))
        s.update(_git(root, ["ls-files", "--others", "--exclude-standard"]))
        # Приводим к POSIX
        return {str(Path(p).as_posix()) for p in s}
    
    def branch_changed_files(self, root: Path, target_branch: Optional[str] = None) -> Set[str]:
        """
        Возвращает файлы, изменённые в текущей ветке относительно целевой ветки.
        
        Args:
            root: Корень git репозитория
            target_branch: Целевая ветка для сравнения (если None, ищется автоматически)
            
        Returns:
            Множество POSIX путей файлов, изменённых в текущей ветке
        """
        base_ref = _find_merge_base_or_parent(root, target_branch)
        if not base_ref:
            # Фоллбек к обычным изменениям если не можем найти базу
            return self.changed_files(root)
        
        s: Set[str] = set()
        # Файлы, изменённые между базовой точкой и HEAD
        s.update(_git(root, ["diff", "--name-only", f"{base_ref}..HEAD"]))
        # Добавляем также текущие рабочие изменения
        s.update(_git(root, ["diff", "--name-only"]))
        s.update(_git(root, ["diff", "--name-only", "--cached"]))
        s.update(_git(root, ["ls-files", "--others", "--exclude-standard"]))
        
        # Приводим к POSIX
        return {str(Path(p).as_posix()) for p in s}
