"""
Обработчик секций.

Реализует обработку отдельных секций по запросу от движка шаблонов.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from .adapters.processor import process_files
from .config import Config, load_config
from .io.manifest import build_section_manifest
from .plan.planner import build_section_plan
from .render.renderer import render_section
from .run_context import RunContext
from .stats.collector import StatsCollector
from .template.context import TemplateContext
from .types import RenderedSection, SectionRef, SectionManifest


class SectionProcessor:
    """
    Обрабатывает одну секцию по запросу.
    """
    
    def __init__(self, run_ctx: RunContext, stats_collector: StatsCollector):
        """
        Инициализирует обработчик секций.
        
        Args:
            run_ctx: Контекст выполнения с настройками и сервисами
            stats_collector: Коллектор статистики для делегирования всех расчетов
        """
        self.run_ctx = run_ctx
        self.stats_collector = stats_collector
        # Кэшируем конфигурации для каждого scope_dir
        self._config_cache: Dict[Path, Config] = {}

    def _get_config(self, scope_dir: Path) -> Config:
        """
        Получает конфигурацию для указанного scope_dir с кэшированием.
        
        Args:
            scope_dir: Директория с конфигурацией
            
        Returns:
            Загруженная конфигурация
        """
        if scope_dir not in self._config_cache:
            self._config_cache[scope_dir] = load_config(scope_dir)
        return self._config_cache[scope_dir]

    def _build_manifest(self, section_ref: SectionRef, template_ctx: TemplateContext) -> SectionManifest:
        """
        Строит манифест секции с использованием кэшированной конфигурации.
        
        Args:
            section_ref: Ссылка на секцию
            template_ctx: Контекст шаблона
            
        Returns:
            Манифест секции
        """
        # Проверяем, есть ли в контексте виртуальная секция
        virtual_section_config = template_ctx.get_virtual_section()
        
        if virtual_section_config is not None:
            # Используем виртуальную секцию
            section_config = virtual_section_config
        else:
            # Получаем конфигурацию с кэшированием
            config = self._get_config(section_ref.scope_dir)
            section_config = config.sections.get(section_ref.name)
            
            if not section_config:
                available = list(config.sections.keys())
                raise RuntimeError(
                    f"Section '{section_ref.name}' not found in {section_ref.scope_dir}. "
                    f"Available: {', '.join(available) if available else '(none)'}"
                )
        
        manifest = build_section_manifest(
            section_ref=section_ref,
            section_config=section_config,
            template_ctx=template_ctx,
            root=self.run_ctx.root,
            vcs=self.run_ctx.vcs,
            vcs_mode=template_ctx.current_state.mode_options.vcs_mode
        )

        # Для виртуальных секций (md-плейсхолдеров) проверяем наличие файлов
        if virtual_section_config is not None and not manifest.files:
            # Это наша виртуальная секция для md-плейсхолдера
            # Попробуем восстановить информацию о плейсхолдере из фильтров
            if manifest.ref.scope_rel:
                # Адресный плейсхолдер
                raise RuntimeError(f"No markdown files found for `md@{manifest.ref.scope_rel}:` placeholder")
            else:
                # Обычный плейсхолдер, пробуем получить путь из конфигурации секции
                virtual_cfg = template_ctx.get_virtual_section()
                if virtual_cfg and virtual_cfg.filters.allow:
                    file_path = virtual_cfg.filters.allow[0].lstrip('/')
                    if file_path.startswith('lg-cfg/'):
                        raise RuntimeError(f"No markdown files found for `md@self:{file_path[7:]}` placeholder")
                    else:
                        raise RuntimeError(f"No markdown files found for `md:{file_path}` placeholder")
                else:
                    raise RuntimeError("No markdown files found for `md:` placeholder")

        return manifest

    def process_section(self, section_ref: SectionRef, template_ctx: TemplateContext) -> RenderedSection:
        """
        Обрабатывает одну секцию и возвращает её отрендеренное содержимое.
        
        Args:
            section_ref: Ссылка на секцию
            template_ctx: Текущий контекст шаблона (содержит активные режимы, теги)
            
        Returns:
            Отрендеренная секция
        """
        manifest = self._build_manifest(section_ref, template_ctx)
        
        plan = build_section_plan(manifest, template_ctx)
        
        processed_files = process_files(plan, template_ctx)
        
        # Регистрируем обработанные файлы в коллекторе статистики
        for pf in processed_files:
            self.stats_collector.register_processed_file(
                file=pf,
                section_ref=section_ref
            )
        
        rendered = render_section(plan, processed_files)

        # Регистрируем отрендеренную секцию в коллекторе статистики
        self.stats_collector.register_section_rendered(rendered)
        
        return rendered

__all__ = ["SectionProcessor"]