"""
Построитель манифеста одной секции для LG V2.

Заменяет части старого build_manifest, но работает с одной секцией
и учитывает активный контекст шаблона (режимы, теги, условия).
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..adapters.registry import get_adapter_for_path
from ..config import SectionCfg, load_config
from ..config.paths import cfg_root, is_cfg_relpath
from ..conditions.evaluator import evaluate_condition_string
from ..io.filters import FilterEngine
from ..io.fs import build_gitignore_spec, iter_files
from ..lang import get_language_for_file
from ..template.context import TemplateContext
from ..types_v2 import FileEntry, SectionManifest, SectionRef


def build_section_manifest(
    section_ref: SectionRef, 
    template_ctx: TemplateContext,
    root: Path,
    vcs,
    vcs_mode: str
) -> SectionManifest:
    """
    Строит манифест одной секции с учетом активного контекста.
    
    Args:
        section_ref: Ссылка на секцию
        template_ctx: Контекст шаблона с активными режимами/тегами
        root: Корень репозитория
        vcs: VCS провайдер
        vcs_mode: Режим VCS ("all" или "changes")
        
    Returns:
        Манифест секции с отфильтрованными файлами
        
    Raises:
        RuntimeError: Если секция не найдена
    """
    # Загружаем конфигурацию секции
    scope_dir = section_ref.cfg_path.parent
    cfg = _get_section_config(scope_dir, section_ref.name)
    if not cfg:
        raise RuntimeError(f"Section '{section_ref.name}' not found in {scope_dir}")
    
    # Получаем список измененных файлов для режима changes
    changed_files = set()
    if vcs_mode == "changes":
        changed_files = vcs.changed_files(root)
    
    # Строим список файлов с учетом фильтров и условий
    files = _collect_files(
        root=root,
        scope_dir=scope_dir,
        scope_rel="",  # Текущий скоуп - корень репозитория
        cfg=cfg,
        changed_files=changed_files,
        template_ctx=template_ctx
    )
    
    return SectionManifest(
        ref=section_ref,
        files=files,
        path_labels=cfg.path_labels,
        adapters_cfg=cfg.adapters,
        scope_dir=scope_dir,
        scope_rel=""
    )


def resolve_section_ref(section_name: str, root: Path) -> SectionRef:
    """
    Разрешает имя секции в SectionRef.
    
    В текущей реализации предполагаем, что секция находится в текущем скоупе.
    В будущем можно добавить поддержку адресных секций (@origin:name).
    
    Args:
        section_name: Имя секции
        root: Корень репозитория
        
    Returns:
        Ссылка на секцию
    """
    cfg_path = cfg_root(root)
    scope_path = ""  # Текущий скоуп
    
    return SectionRef(
        name=section_name,
        scope_path=scope_path,
        cfg_path=cfg_path
    )


# ---- Внутренние функции ----

_CONFIG_CACHE: Dict[Path, Dict[str, SectionCfg]] = {}


def _get_section_config(scope_dir: Path, section_name: str) -> Optional[SectionCfg]:
    """
    Получает конфигурацию секции с кэшированием.
    """
    if scope_dir not in _CONFIG_CACHE:
        try:
            config_model = load_config(scope_dir)
            _CONFIG_CACHE[scope_dir] = config_model.sections
        except Exception:
            _CONFIG_CACHE[scope_dir] = {}
    
    return _CONFIG_CACHE[scope_dir].get(section_name)


def _collect_files(
    root: Path,
    scope_dir: Path,
    scope_rel: str,
    cfg: SectionCfg,
    changed_files: Set[str],
    template_ctx: TemplateContext
) -> List[FileEntry]:
    """
    Собирает файлы для секции с учетом фильтров и активного контекста.
    """
    # Применяем базовые фильтры секции
    engine = FilterEngine(cfg.filters)
    exts = {e.lower() for e in cfg.extensions}
    
    # .gitignore
    spec_git = build_gitignore_spec(root)
    
    # Прунер для раннего отсечения директорий
    def _pruner(rel_dir: str) -> bool:
        if is_cfg_relpath(rel_dir):
            return False
        return engine.may_descend(rel_dir)
    
    # Собираем кандидатов файлов
    candidates: List[FileEntry] = []
    
    for fp in iter_files(root, extensions=exts, spec_git=spec_git, dir_pruner=_pruner):
        rel_posix = fp.resolve().relative_to(root.resolve()).as_posix()
        
        # Фильтр по режиму VCS
        if changed_files and rel_posix not in changed_files:
            continue
        
        # Основная фильтрация
        if not engine.includes(rel_posix):
            continue
        
        # Проверка пустых файлов
        try:
            size0 = (fp.stat().st_size == 0)
        except Exception:
            size0 = False
        
        if size0:
            adapter_cls = get_adapter_for_path(fp)
            effective_exclude_empty = cfg.skip_empty
            raw_cfg = cfg.adapters.get(adapter_cls.name, {})
            empty_policy = raw_cfg.get("empty_policy", "inherit")
            
            if empty_policy == "include":
                effective_exclude_empty = False
            elif empty_policy == "exclude":
                effective_exclude_empty = True
            
            if effective_exclude_empty:
                continue
        
        # Определяем язык и создаем FileEntry
        lang = get_language_for_file(fp)
        
        # Вычисляем адаптерные оверрайды
        overrides = _compute_adapter_overrides(rel_posix, cfg)
        
        candidates.append(FileEntry(
            abs_path=fp,
            rel_path=rel_posix,
            language_hint=lang,
            adapter_overrides=overrides,
            size_bytes=fp.stat().st_size if fp.exists() else 0
        ))
    
    # Применяем условную фильтрацию
    filtered = _apply_conditional_filters(candidates, cfg, template_ctx)
    
    # Сортируем для стабильного порядка
    filtered.sort(key=lambda f: f.rel_path)
    
    return filtered


def _compute_adapter_overrides(rel_path: str, cfg: SectionCfg) -> Dict[str, Dict]:
    """
    Вычисляет оверрайды настроек адаптеров для конкретного файла.
    """
    overrides: Dict[str, Dict] = {}
    
    # Сортируем правила по специфичности (длина паттерна без wildcards)
    target_specs = []
    for idx, target_rule in enumerate(cfg.targets):
        pat_clean_len = sum(len(p.replace("*", "").replace("?", "")) for p in target_rule.match)
        target_specs.append((pat_clean_len, idx, target_rule))
    
    # Применяем правила в порядке специфичности
    for _spec_len, _idx, target_rule in sorted(target_specs, key=lambda x: (x[0], x[1])):
        matched = False
        for pattern in target_rule.match:
            pattern_rel = pattern.lstrip("/")
            if fnmatch.fnmatch(rel_path, pattern_rel):
                matched = True
                break
        
        if not matched:
            continue
        
        # Объединяем настройки адаптеров
        for adapter_name, patch_cfg in target_rule.adapter_cfgs.items():
            base = overrides.get(adapter_name, {})
            merged = dict(base)
            merged.update(patch_cfg or {})
            overrides[adapter_name] = merged
    
    return overrides


def _apply_conditional_filters(
    candidates: List[FileEntry], 
    cfg: SectionCfg, 
    template_ctx: TemplateContext
) -> List[FileEntry]:
    """
    Применяет условную фильтрацию на основе активных тегов и режимов.
    """
    if not cfg.conditional_filters:
        return candidates
    
    # Создаем контекст для вычисления условий
    condition_context = template_ctx._create_condition_context()
    
    # Применяем каждый условный фильтр
    for cond_filter in cfg.conditional_filters:
        try:
            # Вычисляем условие
            condition_met = evaluate_condition_string(cond_filter.condition, condition_context)
            
            if condition_met:
                # Условие выполнено, применяем фильтры
                candidates = _apply_conditional_patterns(candidates, cond_filter)
        
        except Exception as e:
            # Логируем ошибку, но не прерываем обработку
            import logging
            logging.warning(f"Error evaluating condition '{cond_filter.condition}': {e}")
    
    return candidates


def _apply_conditional_patterns(
    candidates: List[FileEntry], 
    cond_filter
) -> List[FileEntry]:
    """
    Применяет allow/block паттерны из условного фильтра.
    """
    import pathspec
    
    # Создаем PathSpec для allow и block паттернов
    allow_spec = None
    if cond_filter.allow:
        allow_spec = pathspec.PathSpec.from_lines("gitwildmatch", cond_filter.allow)
    
    block_spec = None  
    if cond_filter.block:
        block_spec = pathspec.PathSpec.from_lines("gitwildmatch", cond_filter.block)
    
    filtered_candidates = []
    
    for candidate in candidates:
        rel_path = candidate.rel_path
        
        # Сначала проверяем block - если совпадает, исключаем файл
        if block_spec and block_spec.match_file(rel_path):
            continue
        
        # Если есть allow паттерны, файл должен им соответствовать
        if allow_spec and not allow_spec.match_file(rel_path):
            continue
        
        # Файл прошел фильтрацию
        filtered_candidates.append(candidate)
    
    return filtered_candidates


__all__ = [
    "build_section_manifest",
    "resolve_section_ref"
]