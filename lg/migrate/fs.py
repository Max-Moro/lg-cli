from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Iterable, List


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
    Mini-FS for migrations: operations are limited to the scope of lg-cfg/.
    """
    def __init__(self, repo_root: Path, cfg_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.cfg_root = cfg_root.resolve()

    # ---------- reading ----------
    def exists(self, rel: str) -> bool:
        return (self.cfg_root / rel).exists()

    def read_text(self, rel: str, encoding: str = "utf-8") -> str:
        return (self.cfg_root / rel).read_text(encoding=encoding, errors="ignore")

    # ---------- writing (atomically) ----------
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
        # For simplicity — copy content as text (files in lg-cfg/ are text by contract)
        text = src.read_text(encoding="utf-8", errors="ignore")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(dst)
        try:
            src.unlink()
        except Exception:
            pass

    def remove_file(self, rel: str) -> None:
        try:
            (self.cfg_root / rel).unlink()
        except Exception:
            pass

    # ---------- directories ----------
    def dir_has_files(self, rel: str) -> bool:
        """
        True if the directory (or its subdirectories) contains at least one file.
        False if the directory does not exist.
        """
        p = self.cfg_root / rel
        if not p.exists() or not p.is_dir():
            return False
        for q in p.rglob("*"):
            try:
                if q.is_file():
                    return True
            except Exception:
                continue
        return False

    def remove_dir_tree(self, rel: str) -> None:
        """
        Removes an empty directory and all its empty subdirectories (bottom-up).
        Does nothing if there are files inside.
        """
        p = self.cfg_root / rel
        if not p.exists() or not p.is_dir():
            return
        # if there are files — exit
        if self.dir_has_files(rel):
            return
        # walk from bottom to top and try rmdir
        items = sorted(p.rglob("*"), key=lambda x: len(x.as_posix().split("/")), reverse=True)
        for q in items:
            try:
                if q.is_dir():
                    q.rmdir()
            except Exception:
                pass
        try:
            p.rmdir()
        except Exception:
            pass

    # ---------- search ----------
    def glob_rel(self, pattern: str) -> List[str]:
        """
        Returns a list of relative paths under lg-cfg/ matching the glob pattern.
        Example: "*.sec.yaml", "**/*.sec.yaml"
        """
        out: List[str] = []
        for p in self.cfg_root.rglob(pattern):
            try:
                out.append(p.relative_to(self.cfg_root).as_posix())
            except Exception:
                continue
        out.sort()
        return out

    # ---------- utilities ----------
    def git_tracked_index(self) -> list[str]:
        """`git ls-files -s lg-cfg` — stable index (mode, hash, path)."""
        rel = self.cfg_root.relative_to(self.repo_root).as_posix()
        return _git(self.repo_root, ["ls-files", "-s", rel])

    def git_untracked(self) -> list[str]:
        """List of untracked paths under lg-cfg/."""
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
