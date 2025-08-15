from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Set

from . import VcsProvider


def _git(root: Path, args: list[str]) -> list[str]:
    try:
        out = subprocess.check_output(["git", "-C", str(root), *args], text=True, encoding="utf-8", errors="ignore")
        return [ln.strip() for ln in out.splitlines() if ln.strip()]
    except Exception:
        return []


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
