from __future__ import annotations
import subprocess
from pathlib import Path
from typing import List, Set

from ..utils import iter_files, read_file_text, build_pathspec
from ..adapters import get_adapter_for_path
from ..config.model import Config
from ..filters.engine import FilterEngine

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

def generate_listing(
    *, root: Path, cfg: Config, mode: str = "all", list_only: bool = False
) -> None:
    # 1. подготовка
    # → если каких-то полей нет в cfg, берём безопасные дефолты
    exts = {e.lower() for e in cfg.extensions}
    spec_git = build_pathspec(root)  # только .gitignore

    engine = FilterEngine(cfg.filters)
    changed = _collect_changed_files(root) if mode == "changes" else None

    tool_dir = Path(__file__).resolve().parent.parent  # …/lg/

    # 2. обход проекта
    output: List[str] = []
    listed_paths: List[str] = []
    for fp in iter_files(root, exts, spec_git):
        # пропускаем self-код
        if tool_dir in fp.resolve().parents:
            continue

        rel_posix = fp.relative_to(root).as_posix()
        if changed is not None and rel_posix not in changed:
            continue

        if not engine.includes(rel_posix):
            continue

        # Если нужен лишь список — откладываем путь и продолжаем.
        if list_only:
            listed_paths.append(rel_posix)
            continue

        text = read_file_text(fp)
        adapter = get_adapter_for_path(fp)

        # секция языка, если она есть
        lang_cfg = getattr(cfg, adapter.name, None)

        if adapter.name != "base":
            if adapter.should_skip(fp, text, lang_cfg):
                continue
        else:
            # «базовый» адаптер → смотрим глобальный флаг
            if cfg.skip_empty and not text.strip():
                continue

        output.append(f"# —— FILE: {rel_posix} ——\n")
        output.append(text)
        output.append("\n\n")

    # 3. печать
    import sys
    if list_only:
        sys.stdout.write("\n".join(sorted(listed_paths)) + ("\n" if listed_paths else ""))
    else:
        sys.stdout.write("".join(output))
