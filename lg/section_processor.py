"""
Обработчик секций для LG V2.

Реализует обработку отдельных секций по запросу от движка шаблонов,
заменяя части старой цепочки build_manifest -> build_plan -> process_groups -> render_by_section
для одной секции за раз.
"""

from __future__ import annotations

from .adapters.processor import process_files
from .manifest.builder import build_section_manifest
from .plan.planner import build_section_plan
from .render.renderer_v2 import render_section
from .run_context import RunContext
from .stats.collector import StatsCollector
from .template.context import TemplateContext
from .types_v2 import RenderedSection, SectionRef


class SectionProcessor:
    """
    Обрабатывает одну секцию по запросу.
    
    Это заменяет части старой цепочки build_manifest -> build_plan -> process_groups -> render_by_section,
    но для одной секции за раз с учетом активного контекста шаблона.
    
    Теперь работает как оркестратор отдельных модулей:
    - manifest/builder.py - построение манифеста секции
    - plan/planner.py - планирование рендеринга
    - adapters/processor.py - обработка файлов
    - render/renderer_v2.py - рендеринг секции
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

    def process_section(self, section_ref: SectionRef, template_ctx: TemplateContext) -> RenderedSection:
        """
        Обрабатывает одну секцию и возвращает её отрендеренное содержимое.
        
        Args:
            section_ref: Ссылка на секцию
            template_ctx: Текущий контекст шаблона (содержит активные режимы, теги)
            
        Returns:
            Отрендеренная секция
        """

        manifest = build_section_manifest(
            section_ref=section_ref,
            template_ctx=template_ctx,
            root=self.run_ctx.root,
            vcs=self.run_ctx.vcs,
            vcs_mode=template_ctx.current_state.mode_options.vcs_mode
        )
        
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