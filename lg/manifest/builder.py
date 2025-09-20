"""
Построитель манифеста одной секции.

Учитывает активный контекст шаблона (режимы, теги, условия).
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Dict, List, Set, cast

from ..adapters.registry import get_adapter_for_path
from ..config import SectionCfg, load_config, EmptyPolicy
from ..config.paths import is_cfg_relpath
from ..io.filters import FilterEngine
from ..io.fs import build_gitignore_spec, iter_files
from ..io.model import FilterNode
from ..render import get_language_for_file
from ..template.context import TemplateContext
from ..types import FileEntry, SectionManifest, SectionRef
from ..vcs import VcsProvider, NullVcs


def build_section_manifest(
    section_ref: SectionRef, 
    template_ctx: TemplateContext,
    root: Path,
    vcs: VcsProvider,
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
    vcs = vcs or NullVcs()
    
    # Получаем изменённые файлы для режима changes
    changed: Set[str] = set()
    if vcs_mode == "changes":
        changed = vcs.changed_files(root)
    
    # Загружаем конфигурацию секции
    scope_dir = section_ref.scope_dir
    config = load_config(scope_dir)
    section_cfg = config.sections.get(section_ref.name)
    
    if not section_cfg:
        available = list(config.sections.keys())
        raise RuntimeError(
            f"Section '{section_ref.name}' not found in {scope_dir}. "
            f"Available: {', '.join(available) if available else '(none)'}"
        )
    
    # Создаем базовый фильтр с условными дополнениями
    filter_engine = _create_enhanced_filter_engine(section_cfg, template_ctx)

    # Вычисляем финальные опции адаптеров с учетом условий
    adapters_cfg = _compute_final_adapter_configs(section_cfg, template_ctx)

    # Получаем файлы секции
    files = _collect_section_files(
        section_ref=section_ref,
        section_cfg=section_cfg,
        filter_engine=filter_engine,
        changed_files=changed,
        vcs_mode=vcs_mode,
        root=root,
        adapters_cfg=adapters_cfg
    )

    # Создаем манифест
    return SectionManifest(
        ref=section_ref,
        files=files,
        path_labels=section_cfg.path_labels,
        adapters_cfg=adapters_cfg
    )


def _compute_final_adapter_configs(section_cfg: SectionCfg, template_ctx: TemplateContext) -> Dict[str, Dict]:
    """
    Вычисляет финальные опции адаптеров с учетом условных правил.
    
    Args:
        section_cfg: Конфигурация секции с AdapterConfig объектами
        template_ctx: Контекст шаблона с активными тегами
        
    Returns:
        Словарь финальных опций адаптеров (имя_адаптера -> опции)
    """
    final_configs = {}
    for adapter_name, adapter_config in section_cfg.adapters.items():
        # Начинаем с базовых опций
        final_options = dict(adapter_config.base_options)

        # Применяем условные опции в порядке их определения
        # Более поздние правила переопределяют более ранние
        for conditional_option in adapter_config.conditional_options:
            # Вычисляем условие
            condition_met = template_ctx.evaluate_condition_text(conditional_option.condition)

            if condition_met:
                # Применяем опции из этого условного блока
                final_options.update(conditional_option.options)

        final_configs[adapter_name] = final_options
    
    return final_configs


def _create_enhanced_filter_engine(section_cfg: SectionCfg, template_ctx: TemplateContext) -> FilterEngine:
    """
    Создает движок фильтрации с учетом условных фильтров из контекста шаблона.
    
    Применяет активные условные фильтры к базовому FilterNode секции,
    добавляя дополнительные allow/block правила при выполнении условий.
    """
    # Начинаем с базового фильтра секции
    base_filter = section_cfg.filters
    
    # Если нет условных фильтров, возвращаем базовый движок
    if not section_cfg.conditional_filters:
        return FilterEngine(base_filter)
    
    # Создаем копию базового фильтра для модификации
    enhanced_filter = FilterNode(
        mode=base_filter.mode,
        allow=list(base_filter.allow),
        block=list(base_filter.block),
        children=dict(base_filter.children)  # Shallow copy достаточно для наших целей
    )
    
    # Применяем условные фильтры
    for conditional_filter in section_cfg.conditional_filters:
        try:
            # Вычисляем условие в контексте шаблона
            condition_met = template_ctx.evaluate_condition_text(conditional_filter.condition)
            
            if condition_met:
                # Добавляем дополнительные правила фильтрации
                enhanced_filter.allow.extend(conditional_filter.allow)
                enhanced_filter.block.extend(conditional_filter.block)
        except Exception as e:
            # Логируем ошибку оценки условия, но не прерываем обработку
            import logging
            logging.warning(
                f"Failed to evaluate conditional filter condition '{conditional_filter.condition}': {e}"
            )
    
    return FilterEngine(enhanced_filter)


def _collect_section_files(
    section_ref: SectionRef,
    section_cfg: SectionCfg,
    filter_engine: FilterEngine,
    changed_files: Set[str],
    vcs_mode: str,
    root: Path,
    adapters_cfg: dict[str, dict]
) -> List[FileEntry]:
    """
    Собирает файлы для секции с применением всех фильтров.
    """
    scope_rel = section_ref.scope_rel

    # Функция проверки принадлежности файла к скоупу секции
    def in_scope(path_posix: str) -> bool:
        if scope_rel == "":
            return True
        return path_posix == scope_rel or path_posix.startswith(f"{scope_rel}/")
    
    def rel_for_engine(path_posix: str) -> str:
        """Путь относительно scope_dir для применения фильтров секции."""
        if scope_rel == "":
            return path_posix
        return path_posix[len(scope_rel):].lstrip("/")
    
    # Расширения файлов
    extensions = {e.lower() for e in section_cfg.extensions}
    
    # Gitignore спецификация
    spec_git = build_gitignore_spec(root)
    
    # Подготовка правил targets для адресных оверрайдов
    target_specs = _prepare_target_specs(section_cfg)
    
    # Pruner для раннего отсечения директорий
    def _pruner(rel_dir: str) -> bool:
        """Решаем, углубляться ли в каталог rel_dir (repo-root relative, POSIX)."""
        if scope_rel == "":
            # Глобальный скоуп (корень репо): применяем фильтры везде
            sub_rel = rel_dir
            if is_cfg_relpath(sub_rel):
                return False
            return filter_engine.may_descend(sub_rel)
        
        if rel_dir == "":
            # корень репо — всегда можно спуститься
            return True
        
        is_ancestor_of_scope = scope_rel.startswith(rel_dir + "/") or scope_rel == rel_dir
        is_inside_scope = rel_dir.startswith(scope_rel + "/") or rel_dir == scope_rel
        
        if not (is_ancestor_of_scope or is_inside_scope):
            # Ветка гарантированно вне интереса данной секции
            return False
        
        if is_ancestor_of_scope and not is_inside_scope:
            # Мы выше scope_rel: фильтры секции ещё не применимы
            return True
        
        # Мы в пределах scope_rel: применяем фильтры секции
        sub_rel = rel_for_engine(rel_dir)
        if is_cfg_relpath(sub_rel):
            return False
        return filter_engine.may_descend(sub_rel)
    
    # Собираем файлы
    files: List[FileEntry] = []
    
    for fp in iter_files(root, extensions=extensions, spec_git=spec_git, dir_pruner=_pruner):
        rel_posix = fp.resolve().relative_to(root.resolve()).as_posix()
        
        # Фильтр по режиму VCS
        if vcs_mode == "changes" and rel_posix not in changed_files:
            continue
        
        # Ограничиваемся файлами внутри scope_rel
        if not in_scope(rel_posix):
            continue
        
        # Применяем фильтры секции
        rel_engine = rel_for_engine(rel_posix)
        if not filter_engine.includes(rel_engine):
            continue
        
        # Обработка пустых файлов
        if _should_skip_empty_file(fp, bool(section_cfg.skip_empty), adapters_cfg):
            continue
        
        # Определяем язык файла
        lang = get_language_for_file(fp)
        
        # Определяем адресные оверрайды адаптеров
        overrides = _calculate_adapter_overrides(rel_engine, target_specs)
        
        # Создаем FileEntry
        files.append(FileEntry(
            abs_path=fp,
            rel_path=rel_posix,
            language_hint=lang,
            adapter_overrides=overrides
        ))

    # Сортируем по rel_path для стабильности
    files.sort(key=lambda f: f.rel_path)
    
    return files


def _prepare_target_specs(section_cfg: SectionCfg) -> List[tuple]:
    """
    Подготавливает спецификации целей с метрикой специфичности.
    """
    target_specs = []
    for idx, target_rule in enumerate(section_cfg.targets):
        # Простейшая метрика специфичности: сумма длин строк без '*' и '?'
        pat_clean_len = sum(len(p.replace("*", "").replace("?", "")) for p in target_rule.match)
        target_specs.append((pat_clean_len, idx, target_rule.match, target_rule.adapter_cfgs))
    
    return target_specs


def _should_skip_empty_file(file_path: Path, effective_exclude_empty: bool, adapters_cfg: dict[str, dict]) -> bool:
    """
    Определяет, следует ли пропустить пустой файл.
    
    Учитывает политику секции и адаптера с учетом условных правил.
    """
    try:
        size0 = (file_path.stat().st_size == 0)
    except Exception:
        size0 = False
    
    if not size0:
        return False  # Файл не пустой
    
    # Определяем адаптер и его политику
    adapter_cls = get_adapter_for_path(file_path)

    # Проверяем политику адаптера
    raw_cfg = adapters_cfg.get(adapter_cls.name)
    if raw_cfg and "empty_policy" in raw_cfg:
        empty_policy = cast(EmptyPolicy, raw_cfg["empty_policy"])
        
        if empty_policy == "include":
            effective_exclude_empty = False
        elif empty_policy == "exclude":
            effective_exclude_empty = True
    
    return effective_exclude_empty


def _calculate_adapter_overrides(rel_path: str, target_specs: List[tuple]) -> Dict[str, dict]:
    """
    Вычисляет адресные оверрайды конфигураций адаптеров.
    """
    overrides: Dict[str, dict] = {}
    
    # Сортируем по специфичности, затем по порядковому номеру
    for _spec_len, _idx, patterns, acfgs in sorted(target_specs, key=lambda x: (x[0], x[1])):
        matched = False
        for pat in patterns:
            # Нормализуем паттерн к относительному стилю
            pat_rel = pat.lstrip("/")
            if fnmatch.fnmatch(rel_path, pat_rel):
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
    
    return overrides
