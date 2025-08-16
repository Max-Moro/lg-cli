from __future__ import annotations

from pathlib import Path
from typing import List, Set, cast

from ..adapters import get_adapter_for_path
from ..config import SectionCfg, EmptyPolicy
from ..io.filters import FilterEngine
from ..io.fs import build_gitignore_spec, iter_files
from ..lang import get_language_for_file
from ..types import Manifest, FileRef, ContextSpec
from ..vcs import VcsProvider, NullVcs


def _auto_skip_self(root: Path, rel_posix: str) -> bool:
    """
    По умолчанию не включаем код самого инструмента (lg_vnext/**) в листинги
    — если этого явно не разрешили фильтры. Это убирает «эхо» при разработке.
    """
    return rel_posix.startswith("lg_vnext/")


def build_manifest(
    *,
    root: Path,
    spec: ContextSpec,
    sections_cfg: dict[str, SectionCfg],
    mode: str,                  # "all" | "changes"
    vcs: VcsProvider | None = None,
) -> Manifest:
    """
    Собрать Manifest из набора секций и их фильтров с учётом .gitignore и режима VCS.
    """
    vcs = vcs or NullVcs()
    changed: Set[str] = set()
    if mode == "changes":
        changed = vcs.changed_files(root)

    spec_git = build_gitignore_spec(root)
    files_out: List[FileRef] = []

    # Перебираем секции, упомянутые в контексте
    for sec_name, mult in spec.sections.by_name.items():
        cfg = sections_cfg.get(sec_name)
        if not cfg:
            # секция отсутствует в конфиге — пропускаем молча; резолвер уже проверял
            continue

        engine = FilterEngine(cfg.filters)
        exts = {e.lower() for e in cfg.extensions}

        # Простой pruner по дереву фильтров
        def _pruner(rel_dir: str) -> bool:
            # не спускаемся в служебную папку конфигурации,
            # если только её явно не разрешили фильтрами.
            if rel_dir == "lg-cfg" or rel_dir.startswith("lg-cfg/"):
                return False
            return engine.may_descend(rel_dir)

        for fp in iter_files(root, extensions=exts, spec_git=spec_git, dir_pruner=_pruner):
            rel_posix = fp.resolve().relative_to(root.resolve()).as_posix()

            if _auto_skip_self(root, rel_posix) and not engine.includes("lg_vnext/cli.py"):
                # авто-фильтр кода инструмента, если не разрешили явно
                continue

            if mode == "changes" and rel_posix not in changed:
                continue

            if not engine.includes(rel_posix):
                continue

            # ----- Политика пустых файлов: секционная + адаптерная -----
            try:
                size0 = (fp.stat().st_size == 0)
            except Exception:
                size0 = False
            if size0:
                # Определяем адаптер и его политику
                adapter = get_adapter_for_path(fp)
                # По умолчанию наследуем секционное правило
                effective_exclude_empty = bool(cfg.skip_empty)
                sec_adapter_cfg = getattr(cfg, getattr(adapter, "name", ""), None)
                empty_policy = cast(EmptyPolicy, getattr(sec_adapter_cfg, "empty_policy", "inherit") if sec_adapter_cfg else "inherit")
                if empty_policy == "include":
                    effective_exclude_empty = False
                elif empty_policy == "exclude":
                    effective_exclude_empty = True
                # Применяем решение
                if effective_exclude_empty:
                    continue

            lang = get_language_for_file(fp)
            files_out.append(
                FileRef(
                    abs_path=fp,
                    rel_path=rel_posix,
                    section=sec_name,
                    multiplicity=int(mult),
                    language_hint=lang,
                )
            )

    # стабильная сортировка
    files_out.sort(key=lambda fr: (fr.section, fr.rel_path))
    return Manifest(files=files_out)
