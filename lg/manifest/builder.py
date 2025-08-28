from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import List, Set, cast, Dict, Tuple

from ..adapters import get_adapter_for_path
from ..config import SectionCfg, EmptyPolicy, load_config
from ..config.paths import is_cfg_relpath
from ..io.filters import FilterEngine
from ..io.fs import build_gitignore_spec, iter_files
from ..lang import get_language_for_file
from ..types import Manifest, FileRef, ContextSpec
from ..vcs import VcsProvider, NullVcs


def build_manifest(
    *,
    root: Path,
    spec: ContextSpec,
    mode: str, # "all" | "changes"
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

    # КЭШ конфигов по cfg_root.parent
    _cfg_cache: Dict[Path, Dict[str, SectionCfg]] = {}
    section_refs = spec.section_refs

    # Перебираем адресные секции
    for sref in section_refs:
        scope_dir = sref.cfg_root.parent.resolve()      # каталог пакета/приложения
        # Относительный префикс скопа от корня репо (POSIX)
        try:
            scope_rel = scope_dir.relative_to(root.resolve()).as_posix()
        except Exception:
            # Если пакет не внутри репо — пропускаем молча (или можно поднять ошибку)
            continue

        # Нормализуем '.' → '' (корень репо)
        if scope_rel == ".":
            scope_rel = ""

        def in_scope(path_posix: str) -> bool:
            # Путь path_posix (repo-root relative) находится в скоупе?
            if scope_rel == "":
                return True
            return path_posix == scope_rel or path_posix.startswith(scope_rel + "/")

        def rel_for_engine(path_posix: str) -> str:
            # Путь для сопоставления фильтров секции (относительно scope_dir)
            if scope_rel == "":
                return path_posix
            return path_posix[len(scope_rel):].lstrip("/")

        # Загрузим (или возьмём из кэша) конфиг секций для ЭТОГО cfg_root
        if scope_dir not in _cfg_cache:
            cfg_model = load_config(scope_dir)  # load_config ожидает "repo root" рядом с lg-cfg
            _cfg_cache[scope_dir] = cfg_model.sections
        local_sections = _cfg_cache.get(scope_dir, {})
        cfg = local_sections.get(sref.name)
        if not cfg:
            continue

        engine = FilterEngine(cfg.filters)
        exts = {e.lower() for e in cfg.extensions}

        # Предподготовка: список таргетов и их "вес" специфичности
        # Простейшая метрика специфичности: сумма длин строчек без '*' и '?'.
        # Чем больше — тем специфичнее.
        target_specs: List[Tuple[int, int, List[str], Dict[str, dict]]] = []
        for idx, tr in enumerate(cfg.targets):
            pat_clean_len = sum(len(p.replace("*", "").replace("?", "")) for p in tr.match)
            target_specs.append((pat_clean_len, idx, tr.match, tr.adapter_cfgs))

        # Pruner: не выходим за пределы скопа и учитываем фильтры на поддиректории СКОПА
        def _pruner(rel_dir: str) -> bool:
            # Отсекаем всё, что вне скопа
            if not in_scope(rel_dir) and rel_dir != "":
                return False
            # Относительный путь ДЛЯ фильтров секции (относительно scope_dir)
            sub_rel = rel_for_engine(rel_dir)
            if is_cfg_relpath(sub_rel):
                return False
            return engine.may_descend(sub_rel)

        for fp in iter_files(root, extensions=exts, spec_git=spec_git, dir_pruner=_pruner):
            rel_posix = fp.resolve().relative_to(root.resolve()).as_posix()

            if mode == "changes" and rel_posix not in changed:
                continue

            # ограничиваемся файлами внутри scope_rel
            if not in_scope(rel_posix):
                continue

            # Относительный путь ДЛЯ фильтров секции (относительно scope_dir)
            rel_engine = rel_for_engine(rel_posix)
            if not engine.includes(rel_engine):
                continue

            # ----- Политика пустых файлов: секционная + адаптерная -----
            try:
                size0 = (fp.stat().st_size == 0)
            except Exception:
                size0 = False
            if size0:
                # Определяем адаптер и его политику
                adapter_cls = get_adapter_for_path(fp)
                effective_exclude_empty = bool(cfg.skip_empty)
                raw_cfg: dict | None = cfg.adapters.get(adapter_cls.name)
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

            # --- Определяем адресные оверрайды конфигов адаптеров для данного пути ---
            overrides: Dict[str, dict] = {}
            # Сортируем по специфичности, затем по порядковому номеру: менее специфичные применяются первыми,
            # более специфичные — позже и перезаписывают ключи.
            for _spec_len, _idx, patterns, acfgs in sorted(target_specs, key=lambda x: (x[0], x[1])):
                matched = False
                for pat in patterns:
                    # Конфиг использует абсолютный стиль "/path/**". Нормализуем к относительному.
                    pat_rel = pat.lstrip("/")
                    # Сопоставляем относительно СКОПА
                    if fnmatch.fnmatch(rel_engine, pat_rel):
                        matched = True
                        break
                if not matched:
                    continue
                # Применяем shallow-merge по именам адаптеров
                for adapter_name, patch_cfg in acfgs.items():
                    base = overrides.get(adapter_name, {})
                    merged = dict(base)
                    merged.update(patch_cfg or {})
                    overrides[adapter_name] = merged

            files_out.append(
                FileRef(
                    abs_path=fp,
                    rel_path=rel_posix,
                    section=sref.name,
                    multiplicity=int(sref.multiplicity),
                    language_hint=lang,
                    adapter_overrides=overrides,
                )
            )

    # стабильная сортировка
    files_out.sort(key=lambda fr: (fr.section, fr.rel_path))
    return Manifest(files=files_out)
