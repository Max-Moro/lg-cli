"""
Основной пайплайн обработки.
"""

from __future__ import annotations

from pathlib import Path

from .api_schema import RunResult
from .cache.fs_cache import Cache
from .config import process_adaptive_options
from .config.paths import cfg_root
from .migrate import ensure_cfg_actual
from .run_context import RunContext
from .section_processor import SectionProcessor
from .stats import build_run_result_from_collector, StatsCollector, TokenService
from .template import TemplateProcessor, TemplateProcessingError, TemplateContext
from .types import RunOptions, TargetSpec, SectionRef
from .vcs import NullVcs
from .vcs.git import GitVcs
from .version import tool_version


class Engine:
    """
    Координирующий класс движка.
    
    Управляет взаимодействием между компонентами:
    - TemplateProcessor для обработки шаблонов
    - SectionProcessor для обработки секций 
    - StatsCollector для сбора статистики
    """
    
    def __init__(self, options: RunOptions):
        """
        Инициализирует движок с указанными опциями.
        
        Args:
            options: Опции выполнения
        """
        self.options = options
        self.root = Path.cwd().resolve()
        
        # Инициализируем сервисы
        self._init_services()
        
        # Создаем процессоры
        self._init_processors()
        
        # Настраиваем взаимодействие между компонентами
        self._setup_component_integration()
    
    def _init_services(self) -> None:
        """Инициализирует базовые сервисы."""
        # Кэш
        tool_ver = tool_version()
        self.cache = Cache(self.root, enabled=None, fresh=False, tool_version=tool_ver)
        
        # VCS
        self.vcs = GitVcs() if (self.root / ".git").is_dir() else NullVcs()
        
        self.tokenizer = TokenService(self.root, self.options.model, cache=self.cache)
        active_tags, mode_options, adaptive_loader = process_adaptive_options(
            self.root,
            self.options.modes,
            self.options.extra_tags
        )
        
        self.run_ctx = RunContext(
            root=self.root,
            options=self.options,
            cache=self.cache,
            vcs=self.vcs,
            tokenizer=self.tokenizer,
            adaptive_loader=adaptive_loader,
            mode_options=mode_options,
            active_tags=active_tags,
        )
    
    def _init_processors(self) -> None:
        """Создает основные процессоры."""
        # Коллектор статистики
        self.stats_collector = StatsCollector(tokenizer=self.tokenizer)
        
        # Процессор секций
        self.section_processor = SectionProcessor(
            run_ctx=self.run_ctx,
            stats_collector=self.stats_collector
        )
        
        # Процессор шаблонов
        self.template_processor = TemplateProcessor(self.run_ctx)
    
    def _setup_component_integration(self) -> None:
        """Настраивает взаимодействие между компонентами."""
        # Связываем процессор шаблонов с обработчиком секций
        def section_handler(section_ref: SectionRef, template_ctx: TemplateContext) -> str:
            rendered_section = self.section_processor.process_section(section_ref, template_ctx)
            return rendered_section.text
        
        self.template_processor.set_section_handler(section_handler)
    
    def render_context(self, context_name: str) -> str:
        """
        Рендерит контекст из шаблона.
        
        Args:
            context_name: Имя контекста для рендеринга
            
        Returns:
            Отрендеренный документ
            
        Raises:
            TemplateProcessingError: При ошибке обработки шаблона
            FileNotFoundError: Если шаблон контекста не найден
        """
        # Обеспечиваем актуальность конфигурации
        ensure_cfg_actual(cfg_root(self.root))
        
        # Устанавливаем target в коллекторе статистики
        self.stats_collector.set_target_name(f"ctx:{context_name}")
        
        # Обрабатываем шаблон
        final_text = self.template_processor.process_template_file(context_name)

        # Устанавливаем итоговые тексты в коллекторе
        self.stats_collector.set_final_texts(final_text)

        return final_text

    def render_section(self, section_name: str) -> str:
        """
        Рендерит отдельную секцию.
        
        Args:
            section_name: Имя секции для рендеринга
            
        Returns:
            Отрендеренный документ
        """
        # Обеспечиваем актуальность конфигурации
        ensure_cfg_actual(cfg_root(self.root))
        
        # Устанавливаем target в коллекторе статистики
        self.stats_collector.set_target_name(f"sec:{section_name}")
        
        template_ctx = TemplateContext(self.run_ctx)
        
        # Обрабатываем секцию
        section_ref = SectionRef(section_name, "", self.root)
        rendered_section = self.section_processor.process_section(section_ref, template_ctx)
        
        # Устанавливаем итоговые тексты в коллекторе (для секции они совпадают)
        self.stats_collector.set_final_texts(rendered_section.text)
        
        return rendered_section.text

    def render_text(self, target_spec: TargetSpec) -> str:
        """
        Рендерит финальный текст.

        Args:
            target_spec: Спецификация цели для отчета

        Returns:
            Отрендеренный контекст или секция
        """
        # Рендерим цель в зависимости от типа
        if target_spec.kind == "context":
            return self.render_context(target_spec.name)
        else:
            return self.render_section(target_spec.name)

    def generate_report(self, target_spec: TargetSpec) -> RunResult:
        """
        Генерирует полный отчет с статистикой.
        
        Args:
            target_spec: Спецификация цели для отчета
            
        Returns:
            Модель RunResult в формате API v4
        """
        # Рендерим цель в зависимости от типа
        if target_spec.kind == "context":
            self.render_context(target_spec.name)
        else:
            self.render_section(target_spec.name)
        
        # Генерируем отчет из коллектора статистики
        return build_run_result_from_collector(
            collector=self.stats_collector,
            target_spec=target_spec,
        )


# ----------------------------- Entry Points ----------------------------- #

def _parse_target(target: str) -> TargetSpec:
    """
    Парсит строку цели в TargetSpec.
    
    Args:
        target: Строка цели в формате "ctx:name", "sec:name" или "name"
        
    Returns:
        Спецификация цели
    """
    from lg.template.common import CTX_SUFFIX
    
    root = Path.cwd().resolve()
    cfg_path = cfg_root(root)
    
    kind = "auto"
    name = target.strip()
    
    if name.startswith("ctx:"):
        kind, name = "context", name[4:]
    elif name.startswith("sec:"):
        kind, name = "section", name[4:]
    
    # Для auto режима проверяем наличие контекста
    if kind in ("auto", "context"):
        template_path = cfg_path / f"{name}{CTX_SUFFIX}"
        if template_path.is_file():
            return TargetSpec(
                kind="context", 
                name=name, 
                template_path=template_path
            )
        if kind == "context":
            raise FileNotFoundError(f"Context template not found: {template_path}")
    
    # Fallback к секции
    return TargetSpec(
        kind="section",
        name=name,
        template_path=Path()  # Не используется для секций
    )


def run_render(target: str, options: RunOptions) -> str:
    """Точка входа для рендеринга."""
    target_spec = _parse_target(target)
    engine = Engine(options)
    return engine.render_text(target_spec)


def run_report(target: str, options: RunOptions) -> RunResult:
    """Точка входа для генерации отчета."""
    target_spec = _parse_target(target)
    engine = Engine(options)
    return engine.generate_report(target_spec)


__all__ = [
    "Engine",
    "run_render",
    "run_report",
    "TemplateProcessingError"
]