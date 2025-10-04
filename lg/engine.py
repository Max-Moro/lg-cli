"""
Основной пайплайн обработки.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .cache.fs_cache import Cache
from .config import process_adaptive_options
from .config.paths import cfg_root
from .migrate import ensure_cfg_actual
from .run_context import RunContext
from .section_processor import SectionProcessor
from .stats import RunResult, build_run_result_from_collector, StatsCollector, TokenService
from .template import create_template_processor, TemplateContext
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
        self.template_processor = create_template_processor(self.run_ctx)
    
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
            section_name: Имя секции для рендеринга (может быть адресной ссылкой)
            
        Returns:
            Отрендеренный документ
        """
        # Обеспечиваем актуальность конфигурации
        ensure_cfg_actual(cfg_root(self.root))
        
        # Устанавливаем target в коллекторе статистики
        self.stats_collector.set_target_name(f"sec:{section_name}")
        
        template_ctx = TemplateContext(self.run_ctx)
        
        # Парсим адресную ссылку, если это необходимо
        section_ref = self._create_section_ref(section_name)
        rendered_section = self.section_processor.process_section(section_ref, template_ctx)
        
        # Устанавливаем итоговые тексты в коллекторе (для секции они совпадают)
        self.stats_collector.set_final_texts(rendered_section.text)
        
        return rendered_section.text

    def _create_section_ref(self, section_name: str) -> SectionRef:
        """
        Создает SectionRef из имени секции, поддерживая адресные ссылки.
        
        Args:
            section_name: Имя секции (может быть адресной ссылкой типа @origin:name)
            
        Returns:
            SectionRef с правильными scope_rel и scope_dir
        """
        if section_name.startswith("@["):
            # @[origin]:name
            close = section_name.find("]:")
            if close < 0:
                raise ValueError(f"Invalid section reference (missing ']:' ): {section_name}")
            origin = section_name[2:close]
            name = section_name[close + 2:]
        elif section_name.startswith("@"):
            # @origin:name
            colon = section_name.find(":")
            if colon < 0:
                raise ValueError(f"Invalid section reference (missing ':'): {section_name}")
            origin = section_name[1:colon]
            name = section_name[colon + 1:]
        else:
            # Простая ссылка без адресности
            return SectionRef(section_name, "", self.root)
        
        # Для адресных ссылок вычисляем scope_dir
        scope_dir = (self.root / origin).resolve()
        scope_rel = origin
        
        return SectionRef(name, scope_rel, scope_dir)

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

def _parse_target(target: str, root: Optional[Path] = None) -> TargetSpec:
    """
    Парсит строку цели в TargetSpec.
    
    Args:
        target: Строка цели в формате "ctx:name", "sec:name" или "name"
        root: Корень проекта (если None, используется cwd)
        
    Returns:
        Спецификация цели
    """
    from lg.template.common import CTX_SUFFIX
    
    if root is None:
        root = Path.cwd().resolve()
    else:
        root = root.resolve()
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
    engine = Engine(options)
    target_spec = _parse_target(target, engine.root)
    return engine.render_text(target_spec)


def run_report(target: str, options: RunOptions) -> RunResult:
    """Точка входа для генерации отчета."""
    engine = Engine(options)
    target_spec = _parse_target(target, engine.root)
    return engine.generate_report(target_spec)


__all__ = [
    "Engine",
    "run_render",
    "run_report",
]