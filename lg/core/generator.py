from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List, Set

from ..adapters import get_adapter_for_path
from ..config.model import Config
from ..filters.engine import FilterEngine
from ..lang import get_language_for_file
from ..utils import iter_files, read_file_text, build_pathspec


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

    # 2. обход проекта: собираем данные или пути
    entries: List[tuple[Path, str, object, str]] = []
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

        # полный текст и адаптер для этого файла
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

        # накапливаем запись для генерации
        entries.append((fp, rel_posix, adapter, text))

    # 3. режим «--list-included»: выводим только пути и выходим
    if list_only:
        listing = "\n".join(sorted(listed_paths))
        if listed_paths:
            listing += "\n"
        sys.stdout.write(listing)
        return

    # 4. генерация вывода: fenced или простая склейка
    if cfg.code_fence:
        out_lines: List[str] = []
        prev_lang: str | None = None
        for fp, rel_posix, adapter, text in entries:
            # определяем язык fenced-блока
            lang = get_language_for_file(fp)
            # при смене языка закрываем предыдущий fenced-блок
            if lang != prev_lang:
                if prev_lang is not None:
                    out_lines.append("```\n\n")
                # открываем новый fenced-блок (без указания напр. "```" если lang=="")
                out_lines.append(f"```{lang}\n")
                prev_lang = lang
            # вставляем маркер файла и содержимое
            out_lines.append(f"# —— FILE: {rel_posix} ——\n")
            out_lines.append(text)
            out_lines.append("\n\n")
        # закрываем последний fenced-блок
        if prev_lang is not None:
            out_lines.append("```\n")
        sys.stdout.write("".join(out_lines))
    else:
        # старое поведение: простая последовательная склейка
        out_lines: List[str] = []
        for fp, rel_posix, adapter, text in entries:
            out_lines.append(f"# —— FILE: {rel_posix} ——\\n")
            out_lines.append(text)
            out_lines.append("\\n\\n")
        sys.stdout.write("".join(out_lines))
