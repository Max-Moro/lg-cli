"""
Обработчик секций для LG V2.

Реализует обработку отдельных секций по запросу от движка шаблонов,
заменяя части старой цепочки build_manifest -> build_plan -> process_groups -> render_by_section
для одной секции за раз.
"""

from __future__ import annotations

import fnmatch
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set, cast

from .adapters import get_adapter_for_path, process_groups
from .config import SectionCfg, EmptyPolicy, load_config
from .config.paths import cfg_root, is_cfg_relpath
from .conditions.evaluator import evaluate_condition_string
from .io.filters import FilterEngine
from .io.fs import build_gitignore_spec, iter_files
from .lang import get_language_for_file
from .paths import build_labels
from .render.renderer import render_document
from .run_context import RunContext
from .types import (
    CanonSectionId, Group, ManifestFile, 
    ProcessedBlob, RepoRelPath, SectionPlan
)
from .types import LangName as OldLangName, LANG_NONE as OLD_LANG_NONE
from .types_v2 import (
    FileEntry, FileGroup, ProcessedFile, RenderedSection, 
    SectionManifest, SectionPlan as SectionPlanV2, SectionRef
)
from .template.context import TemplateContext


class SectionProcessor:
    """
    Обрабатывает одну секцию по запросу.
    
    Это заменяет части старой цепочки build_manifest -> build_plan -> process_groups -> render_by_section,
    но для одной секции за раз с учетом активного контекста шаблона.
    """
    
    def __init__(self, run_ctx: RunContext):
        """
        Инициализирует обработчик секций.
        
        Args:
            run_ctx: Контекст выполнения с настройками и сервисами
        """
        self.run_ctx = run_ctx
        self.cache = run_ctx.cache
        self.vcs = run_ctx.vcs
        self.tokenizer = run_ctx.tokenizer
        
        # Кэш результатов обработки секций
        self.section_cache: Dict[str, RenderedSection] = {}
        
        # Кэш конфигураций секций по scope_dir
        self._config_cache: Dict[Path, Dict[str, SectionCfg]] = {}
    
    def process_section(self, section_name: str, template_ctx: TemplateContext) -> RenderedSection:
        """
        Обрабатывает одну секцию и возвращает её отрендеренное содержимое.
        
        Args:
            section_name: Имя секции для обработки
            template_ctx: Текущий контекст шаблона (содержит активные режимы, теги)
            
        Returns:
            Отрендеренная секция
        """
        # Сначала проверяем кэш
        cache_key = self._compute_cache_key(section_name, template_ctx)
        if cache_key in self.section_cache:
            return self.section_cache[cache_key]
        
        # Обрабатываем секцию через конвейер
        section_ref = self._resolve_section_ref(section_name)
        manifest = self._build_section_manifest(section_ref, template_ctx)
        plan = self._build_section_plan(manifest, template_ctx)
        processed_files = self._process_files(plan, template_ctx)
        rendered = self._render_section(plan, processed_files)
        
        # Кэшируем результат
        self.section_cache[cache_key] = rendered
        
        return rendered
    
    def _compute_cache_key(self, section_name: str, template_ctx: TemplateContext) -> str:
        """
        Вычисляет ключ кэша для секции на основе:
        - Имени секции
        - Активных режимов
        - Активных тегов
        - Режима VCS (all vs changes)
        """
        key_parts = [
            section_name,
            template_ctx.current_state.mode_options.vcs_mode,
        ]
        
        # Добавляем активные режимы
        for modeset, mode in sorted(template_ctx.current_state.active_modes.items()):
            key_parts.append(f"mode:{modeset}:{mode}")
        
        # Добавляем активные теги
        for tag in sorted(template_ctx.current_state.active_tags):
            key_parts.append(f"tag:{tag}")
        
        # Создаем хэш от всех параметров
        key_string = ":".join(key_parts)
        return hashlib.sha256(key_string.encode("utf-8")).hexdigest()[:16]
    
    def _resolve_section_ref(self, section_name: str) -> SectionRef:
        """
        Разрешает имя секции в SectionRef.
        
        В текущей реализации предполагаем, что секция находится в текущем скоупе.
        В будущем можно добавить поддержку адресных секций (@origin:name).
        """
        cfg_path = cfg_root(self.run_ctx.root)
        scope_path = ""  # Текущий скоуп
        
        return SectionRef(
            name=section_name,
            scope_path=scope_path,
            cfg_path=cfg_path
        )
    
    def _build_section_manifest(self, section_ref: SectionRef, template_ctx: TemplateContext) -> SectionManifest:
        """
        Строит манифест секции с учетом активного контекста.
        
        Включает фильтрацию файлов по условиям, режимам VCS и активным тегам.
        """
        # Загружаем конфигурацию секции
        scope_dir = section_ref.cfg_path.parent
        cfg = self._get_section_config(scope_dir, section_ref.name)
        if not cfg:
            raise RuntimeError(f"Section '{section_ref.name}' not found in {scope_dir}")
        
        # Получаем список измененных файлов для режима changes
        changed_files = set()
        if template_ctx.current_state.mode_options.vcs_mode == "changes":
            changed_files = self.vcs.changed_files(self.run_ctx.root)
        
        # Строим список файлов с учетом фильтров и условий
        files = self._collect_files(
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
    
    def _get_section_config(self, scope_dir: Path, section_name: str) -> Optional[SectionCfg]:
        """
        Получает конфигурацию секции с кэшированием.
        """
        if scope_dir not in self._config_cache:
            try:
                config_model = load_config(scope_dir)
                self._config_cache[scope_dir] = config_model.sections
            except Exception:
                self._config_cache[scope_dir] = {}
        
        return self._config_cache[scope_dir].get(section_name)
    
    def _collect_files(
        self, 
        scope_dir: Path,
        scope_rel: str,
        cfg: SectionCfg,
        changed_files: Set[str],
        template_ctx: TemplateContext
    ) -> List[FileEntry]:
        """
        Собирает файлы для секции с учетом фильтров и активного контекста.
        """
        root = self.run_ctx.root
        
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
            overrides = self._compute_adapter_overrides(rel_posix, cfg)
            
            candidates.append(FileEntry(
                abs_path=fp,
                rel_path=rel_posix,
                language_hint=lang,
                adapter_overrides=overrides,
                size_bytes=fp.stat().st_size if fp.exists() else 0
            ))
        
        # Применяем условную фильтрацию
        filtered = self._apply_conditional_filters(candidates, cfg, template_ctx)
        
        # Сортируем для стабильного порядка
        filtered.sort(key=lambda f: f.rel_path)
        
        return filtered
    
    def _compute_adapter_overrides(self, rel_path: str, cfg: SectionCfg) -> Dict[str, Dict]:
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
        self, 
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
                    candidates = self._apply_conditional_patterns(candidates, cond_filter)
            
            except Exception as e:
                # Логируем ошибку, но не прерываем обработку
                import logging
                logging.warning(f"Error evaluating condition '{cond_filter.condition}': {e}")
        
        return candidates
    
    def _apply_conditional_patterns(
        self, 
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
    
    def _build_section_plan(self, manifest: SectionManifest, template_ctx: TemplateContext) -> SectionPlanV2:
        """
        Строит план рендеринга для секции.
        """
        files = manifest.files
        
        if not files:
            return SectionPlanV2(
                manifest=manifest,
                groups=[],
                md_only=True,
                use_fence=False,
                labels={}
            )
        
        # Определяем, все ли файлы - markdown/plain text
        md_only = all(f.language_hint == "" for f in files)
        
        # Определяем, использовать ли fenced блоки
        code_fence_enabled = (
            self.run_ctx.options.code_fence and 
            template_ctx.current_state.mode_options.code_fence
        )
        use_fence = code_fence_enabled and not md_only
        
        # Группируем файлы по языку
        groups = self._group_files_by_language(files, use_fence)
        
        # Строим метки файлов
        labels = build_labels(
            (f.rel_path for f in files),
            mode=manifest.path_labels
        )
        
        return SectionPlanV2(
            manifest=manifest,
            groups=groups,
            md_only=md_only,
            use_fence=use_fence,
            labels=labels
        )
    
    def _group_files_by_language(self, files: List[FileEntry], use_fence: bool) -> List[FileGroup]:
        """
        Группирует файлы по языку для рендеринга.
        """
        if not files:
            return []
        
        if use_fence:
            # Группируем по языкам для fenced блоков
            groups = []
            current_lang = files[0].language_hint
            current_group = [files[0]]
            
            for f in files[1:]:
                if f.language_hint == current_lang:
                    current_group.append(f)
                else:
                    groups.append(FileGroup(
                        lang=current_lang,
                        entries=current_group,
                        mixed=False
                    ))
                    current_lang = f.language_hint
                    current_group = [f]
            
            # Добавляем последнюю группу
            groups.append(FileGroup(
                lang=current_lang,
                entries=current_group,
                mixed=False
            ))
            
            return groups
        else:
            # Одна группа без языка
            languages = {f.language_hint for f in files}
            mixed = len(languages) > 1
            
            return [FileGroup(
                lang=OLD_LANG_NONE,
                entries=list(files),
                mixed=mixed
            )]
    
    def _process_files(self, plan: SectionPlanV2, template_ctx: TemplateContext) -> List[ProcessedFile]:
        """
        Обрабатывает файлы через языковые адаптеры напрямую с новой IR-моделью.
        
        Это адаптированная версия process_groups, работающая с FileEntry вместо ManifestFile.
        """
        from .adapters.context import LightweightContext
        from .io.fs import read_text
        
        processed_files = []
        cache = self.run_ctx.cache
        
        # Кэш связанных адаптеров для эффективности
        bound_cache: Dict[tuple[str, tuple[tuple[str, object], ...]], object] = {}
        
        for group in plan.groups:
            group_size = len(group.entries)
            
            for file_entry in group.entries:
                fp = file_entry.abs_path
                adapter_cls = get_adapter_for_path(fp)
                
                # Получаем конфигурацию адаптера (секционная + оверрайды)
                sec_raw_cfg = plan.manifest.adapters_cfg.get(adapter_cls.name)
                override_cfg = file_entry.adapter_overrides.get(adapter_cls.name)
                
                raw_cfg = None
                if sec_raw_cfg or override_cfg:
                    raw_cfg = dict(sec_raw_cfg or {})
                    raw_cfg.update(dict(override_cfg or {}))
                
                # Создаем или получаем связанный адаптер
                cfg_key = self._freeze_cfg(raw_cfg or {})
                bkey = (adapter_cls.name, cfg_key)
                adapter = bound_cache.get(bkey)
                if adapter is None:
                    adapter = adapter_cls.bind(raw_cfg, self.run_ctx.tokenizer)
                    bound_cache[bkey] = adapter
                
                # Читаем содержимое файла
                raw_text = read_text(fp)
                
                # Создаем контекст для адаптера
                lightweight_ctx = LightweightContext(
                    file_path=fp,
                    raw_text=raw_text,
                    group_size=group_size,
                    mixed=bool(group.mixed)
                )
                
                # Проверяем эвристики пропуска
                if adapter.name != "base" and adapter.should_skip(lightweight_ctx):
                    continue
                
                # Строим ключи кэша
                k_proc, p_proc = cache.build_processed_key(
                    abs_path=fp,
                    adapter_name=adapter.name,
                    adapter_cfg=raw_cfg,
                    group_size=group_size,
                    mixed=bool(group.mixed),
                )
                k_raw, p_raw = cache.build_raw_tokens_key(abs_path=fp)
                
                # Пытаемся получить из кэша
                cached = cache.get_processed(p_proc)
                if cached and "processed_text" in cached:
                    processed_text = cached["processed_text"]
                    meta = cached.get("meta", {}) or {}
                else:
                    # Обрабатываем файл адаптером
                    processed_text, meta = adapter.process(lightweight_ctx)
                    
                    # Добавляем диагностическую информацию
                    if raw_cfg:
                        keys = sorted(raw_cfg.keys())
                        meta = dict(meta or {})
                        meta["_adapter_cfg_keys"] = ",".join(keys)
                    
                    # Метки группы для диагностики
                    meta = dict(meta or {})
                    meta["_group_size"] = group_size
                    meta["_group_mixed"] = group.mixed
                    meta["_group_lang"] = group.lang
                    meta["_section"] = plan.manifest.ref.canon_key()
                    
                    # Кэшируем результат
                    cache.put_processed(p_proc, processed_text=processed_text, meta=meta)
                
                # Вычисляем токены (простая аппроксимация, будет улучшено в задаче 4)
                tokens_raw = len(raw_text.split())
                tokens_processed = len(processed_text.split())
                
                # Создаем ProcessedFile
                processed_file = ProcessedFile(
                    abs_path=fp,
                    rel_path=file_entry.rel_path,
                    processed_text=processed_text.rstrip("\n") + "\n",
                    meta=meta,
                    raw_text=raw_text,
                    cache_key=k_proc,
                    tokens_raw=tokens_raw,
                    tokens_processed=tokens_processed
                )
                processed_files.append(processed_file)
        
        # Сортируем для стабильного порядка
        processed_files.sort(key=lambda f: f.rel_path)
        return processed_files
    
    def _freeze_cfg(self, obj) -> tuple:
        """
        Делает объект хэшируемым и детерминированным для кэширования адаптеров.
        """
        if isinstance(obj, dict):
            return tuple((k, self._freeze_cfg(v)) for k, v in sorted(obj.items(), key=lambda kv: kv[0]))
        if isinstance(obj, (list, tuple)):
            return tuple(self._freeze_cfg(x) for x in obj)
        if isinstance(obj, set):
            return tuple(sorted(self._freeze_cfg(x) for x in obj))
        return obj
    
    def _render_section(self, plan: SectionPlanV2, processed_files: List[ProcessedFile]) -> RenderedSection:
        """
        Рендерит секцию в финальный текст.
        """
        # Конвертируем ProcessedFile обратно в ProcessedBlob для совместимости
        blobs = []
        for pf in processed_files:
            blob = ProcessedBlob(
                abs_path=pf.abs_path,
                rel_path=pf.rel_path,
                size_bytes=pf.abs_path.stat().st_size if pf.abs_path.exists() else 0,
                processed_text=pf.processed_text,
                meta=pf.meta,
                raw_text=pf.raw_text,
                cache_key_processed=pf.cache_key,
                cache_key_raw=f"raw_{pf.cache_key}"
            )
            blobs.append(blob)
        
        # Создаем временный SectionPlan для рендеринга
        temp_section_plan = SectionPlan(
            section_id=CanonSectionId(
                scope_rel=plan.manifest.scope_rel,
                name=plan.manifest.ref.name
            ),
            groups=[],  # Будет заполнено ниже
            md_only=plan.md_only,
            use_fence=plan.use_fence,
            labels=plan.labels,
            adapters_cfg=plan.manifest.adapters_cfg
        )
        
        # Заполняем группы для совместимости
        for group in plan.groups:
            manifest_files = []
            for file_entry in group.entries:
                manifest_file = ManifestFile(
                    abs_path=file_entry.abs_path,
                    rel_path=RepoRelPath(file_entry.rel_path),
                    section_id=temp_section_plan.section_id,
                    multiplicity=1,
                    language_hint=OldLangName(file_entry.language_hint),
                    adapter_overrides=file_entry.adapter_overrides
                )
                manifest_files.append(manifest_file)
            
            temp_section_plan.groups.append(Group(
                lang=OldLangName(group.lang),
                entries=manifest_files,
                mixed=group.mixed
            ))
        
        # Используем существующий рендерер
        rendered_doc = render_document(temp_section_plan, blobs)
        
        # Создаем RenderedSection
        rendered_section = RenderedSection(
            ref=plan.manifest.ref,
            text=rendered_doc.text,
            files=processed_files
        )
        
        # Обновляем статистику
        rendered_section.update_stats()
        
        return rendered_section


__all__ = ["SectionProcessor"]