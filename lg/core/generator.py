from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Dict, List, Set

from ..utils import iter_files, read_file_text, build_pathspec
from ..adapters import get_adapter_for_path

def _collect_changed_files(root: Path) -> Set[str]:
    """Вернуть posix-пути изменённых/staged/untracked файлов относительно root."""
    def _git(args: List[str]) -> List[str]:
        return subprocess.check_output(
            ["git", "-C", str(root), *args],
            text=True, encoding="utf-8", errors="ignore"
        ).splitlines()

    files: Set[str] = set()
    files.update(_git(["diff", "--name-only"]))
    files.update(_git(["diff", "--name-only", "--cached"]))
    files.update(_git(["ls-files", "--others", "--exclude-standard"]))
    return {Path(p).as_posix() for p in files if p}

def generate_listing(*, root: Path, cfg: Dict, mode: str = "all") -> None:
    # 1. подготовка
    # → если каких-то полей нет в cfg, берём безопасные дефолты
    exts = {e.lower() for e in cfg.get("extensions", [".py"])}
    spec = build_pathspec(root, cfg.get("exclude", []))
    changed = _collect_changed_files(root) if mode == "changes" else None

    tool_dir = Path(__file__).resolve().parent.parent  # …/lg/

    # 2. обход проекта
    output: List[str] = []
    for fp in iter_files(root, exts, spec):
        # пропускаем self-код
        if tool_dir in fp.resolve().parents:
            continue

        rel_posix = fp.relative_to(root).as_posix()
        if changed is not None and rel_posix not in changed:
            continue

        text = read_file_text(fp)
        adapter = get_adapter_for_path(fp)

        # секция языка, если она есть
        lang_cfg = cfg.get(adapter.name, {})

        if adapter.name != "base":
            # ⇒ язык определён; глобальные правила игнорируем
            if adapter.should_skip(fp, text, lang_cfg):
                continue
        else:
            # нет адаптера → используется только глобальный skip_empty
            if cfg.get("skip_empty") and not text.strip():
                continue

        output.append(f"# —— FILE: {rel_posix} ——\n")
        output.append(text)
        output.append("\n\n")

    # 3. печать
    import sys
    sys.stdout.write("".join(output))
