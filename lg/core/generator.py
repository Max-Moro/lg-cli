from __future__ import annotations

import subprocess
import sys
from itertools import groupby
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
    *,
    root: Path,
    cfg: Config,
    mode: str = "all",
    list_only: bool = False,
    _return_stats: bool = False,            # ← внутр. флаг для stats-режима
):
    # 1. подготовка
    # → если каких-то полей нет в cfg, берём безопасные дефолты
    exts = {e.lower() for e in cfg.extensions}
    spec_git = build_pathspec(root)  # только .gitignore

    engine = FilterEngine(cfg.filters)
    changed = _collect_changed_files(root) if mode == "changes" else None

    # Путь до установленного пакета инструмента (…/lg/)
    tool_dir = Path(__file__).resolve().parent.parent

    # Определяем, хотим ли мы исключать собственный код инструмента.
    # По умолчанию – да (режим сабмодуля/симлинка), но если конфиг ЯВНО
    # разрешает папку самого инструмента (например, allow: "/lg/"),
    # то выключаем авто-игнор.
    skip_self_code = True
    try:
        # Если пакет лежит внутри текущего проекта, получаем его относительный путь
        rel_tool = tool_dir.resolve().relative_to(root.resolve()).as_posix()
        # Явное разрешение: достаточно, чтобы фильтры включали любой реальный файл из пакета.
        # Проверяем типичные имена, присутствующие в проекте.
        if (
            engine.includes(f"{rel_tool}/cli.py")
            or engine.includes(f"{rel_tool}/__init__.py")
        ):
            skip_self_code = False
    except ValueError:
        # Пакет установлен вне root (site-packages и т. п.) — дополнительной фильтрации не требуется.
        # Оставляем skip_self_code=True, но условие ниже всё равно не сработает,
        # так как tool_dir не является родителем ни одного файла в проекте.
        pass

    # 2. обход проекта: собираем данные или пути
    entries: List[tuple[Path, str, object, str]] = []
    listed_paths: List[str] = []
    for fp in iter_files(root, exts, spec_git):
        # Пропускаем self-код инструмента только если это не было явно разрешено конфигом
        if skip_self_code and (tool_dir in fp.resolve().parents):
            continue

        rel_posix = fp.relative_to(root).as_posix()
        if changed is not None and rel_posix not in changed:
            continue

        if not engine.includes(rel_posix):
            continue

        if list_only:
            if _return_stats:
                size_bytes = fp.stat().st_size
                # token counting переедет в stats.collect() — здесь немедленно не нужно
                listed_paths.append((fp, rel_posix, size_bytes))
            else:
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

    # 3. режим «--list-included»: выводим статистику или просто пути
    if list_only:
        if _return_stats:
            # stats-режим: возвращаем собранные данные о файлах
            return listed_paths          # list[(Path, rel_path, size_bytes)]
        else:
            listing = "\n".join(sorted(listed_paths))
            if listed_paths:
                listing += "\n"
            sys.stdout.write(listing)
            return

    # 4. генерация вывода: fenced или простая склейка

    # собираем базовые флаги: чисто Markdown? какие языки?
    md_only = all(adapter.name == "markdown" for _, _, adapter, _ in entries)
    # fenced работает только если code_fence=True и не чисто MD
    use_fence = cfg.code_fence and not md_only
    # mixed = True, если в секции несколько языков и без fenced
    langs = { get_language_for_file(fp) for fp, *_ in entries }
    mixed = not use_fence and len(langs) > 1

    out_lines: List[str] = []

    if use_fence:
        # разбиваем подряд по языку fenced-блока
        for lang, group_iter in groupby(entries, key=lambda e: get_language_for_file(e[0])):
            group = list(group_iter)
            group_size = len(group)
            # открываем fenced-блок
            out_lines.append(f"```{lang}\n")

            for idx, (fp, rel_posix, adapter, text) in enumerate(group):
                # универсальный вызов адаптера
                adapter_cfg = getattr(cfg, adapter.name, None)
                text = adapter.process(text, adapter_cfg, group_size, False)
                # убираем дублированные переносы в конце — оставляем один
                text = text.rstrip("\n") + "\n"
                # разделитель НЕ рисуем для Markdown в fenced-блоке
                if adapter.name != "markdown":
                    out_lines.append(f"# —— FILE: {rel_posix} ——\n")
                out_lines.append(text)
                # добавляем разделитель только между файлами, но не после последнего
                if idx < group_size - 1:
                    out_lines.append("\n\n")

            # закрываем fenced-блок
            out_lines.append("```\n\n")
    else:
        # единый «смешанный» листинг без fenced-блоков
        group_size = len(entries)
        for idx, (fp, rel_posix, adapter, text) in enumerate(entries):
            # универсальный вызов адаптера
            adapter_cfg = getattr(cfg, adapter.name, None)
            text = adapter.process(text, adapter_cfg, group_size, mixed)
            # убираем дублированные переносы в конце — оставляем ровно один
            text = text.rstrip("\n") + "\n"

            # разделитель рисуем только если не чисто MD и не Markdown
            if not (md_only or adapter.name == "markdown"):
                out_lines.append(f"# —— FILE: {rel_posix} ——\n")
            out_lines.append(text)
            # добавляем разделитель только между файлами, но не после последнего
            if idx < group_size - 1:
                out_lines.append("\n\n")

    sys.stdout.write("".join(out_lines))
