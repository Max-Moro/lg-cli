from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Iterable


def _sha1_bytes(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def _git(root: Path, args: list[str]) -> list[str]:
    try:
        out = subprocess.check_output(["git", "-C", str(root), *args], text=True, encoding="utf-8", errors="ignore")
        return [ln.strip() for ln in out.splitlines() if ln.strip()]
    except Exception:
        return []


class CfgFs:
    """
    Мини-FS для миграций: операции ограничены пределами lg-cfg/.
    """
    def __init__(self, repo_root: Path, cfg_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.cfg_root = cfg_root.resolve()

    # ---------- чтение ----------
    def exists(self, rel: str) -> bool:
        return (self.cfg_root / rel).exists()

    def read_text(self, rel: str, encoding: str = "utf-8") -> str:
        return (self.cfg_root / rel).read_text(encoding=encoding, errors="ignore")

    # ---------- запись (атомарно) ----------
    def write_text_atomic(self, rel: str, content: str, encoding: str = "utf-8") -> None:
        path = self.cfg_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(content, encoding=encoding)
        tmp.replace(path)

    def move_atomic(self, src_rel: str, dst_rel: str) -> None:
        src = self.cfg_root / src_rel
        dst = self.cfg_root / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix(dst.suffix + ".tmp-mv")
        # В простоте — копируем содержимое текстом (файлы в lg-cfg/ текстовые по договору)
        text = src.read_text(encoding="utf-8", errors="ignore")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(dst)
        try:
            src.unlink()
        except Exception:
            pass

    # ---------- утилиты ----------
    def git_tracked_index(self) -> list[str]:
        """`git ls-files -s lg-cfg` — стабильный индекс (mode, hash, path)."""
        rel = self.cfg_root.relative_to(self.repo_root).as_posix()
        return _git(self.repo_root, ["ls-files", "-s", rel])

    def git_untracked(self) -> list[str]:
        """Список неотслеживаемых путей под lg-cfg/."""
        rel = self.cfg_root.relative_to(self.repo_root).as_posix()
        return _git(self.repo_root, ["ls-files", "--others", "--exclude-standard", rel])

    def sha1_untracked_files(self, rel_paths: Iterable[str]) -> list[str]:
        out = []
        base = self.repo_root
        for rel in rel_paths:
            p = (base / rel).resolve()
            try:
                data = p.read_bytes()
            except Exception:
                data = b""
            out.append(f"U {rel} { _sha1_bytes(data) }")
        return out
