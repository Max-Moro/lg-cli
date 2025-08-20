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
                effective_exclude_empty = bool(cfg.skip_empty)
                raw_cfg: dict | None = cfg.adapters.get(adapter.name)
                empty_policy: EmptyPolicy = "inherit"
                if raw_cfg is not None and "empty_policy" in raw_cfg:
                    empty_policy = cast(EmptyPolicy, raw_cfg["empty_policy"])

                if empty_policy == "include":
                    effective_exclude_empty = False
                elif empty_policy == "exclude":
                    effective_exclude_empty = True

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
