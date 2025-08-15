from __future__ import annotations

from pathlib import Path
from typing import List, Set

from ..types import Manifest, FileRef, ContextSpec
from ..lang import get_language_for_file
from ..io.fs import build_gitignore_spec, iter_files
from ..io.filters import FilterEngine
from ..config.model import SectionCfg
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

            # фильтруем пустые файлы грубо (глобальная эвристика секции)
            if cfg.skip_empty:
                try:
                    if fp.stat().st_size == 0:
                        continue
                except Exception:
                    pass

            lang = get_language_for_file(fp)
            files_out.append(
                FileRef(
                    abs_path=fp,
                    rel_path=rel_posix,
                    section=sec_name,
                    multiplicity=int(mult),
                    adapter_name="base",    # окончательный адаптер подставится на стадии adapters.engine
                    language_hint=lang,
                )
            )

    # стабильная сортировка
    files_out.sort(key=lambda fr: (fr.section, fr.rel_path))
    return Manifest(files=files_out)
