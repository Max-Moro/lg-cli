"""
Контекст рендеринга для движка шаблонизации LG V2.

Управляет состоянием во время обработки шаблона, включая активные теги,
режимы и их переопределения через блоки {% mode %}.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set, List, Optional

from .evaluator import TemplateConditionEvaluator
from ..config.adaptive_model import ModeOptions
from ..run_context import RunContext, ConditionContext


@dataclass
class TemplateState:
    """
    Снимок состояния шаблона для сохранения/восстановления.
    
    Используется для реализации стека состояний при входе/выходе
    из блоков {% mode %}.
    """
    origin: str
    mode_options: ModeOptions
    active_tags: Set[str]
    active_modes: Dict[str, str]  # modeset -> mode_name
    
    def copy(self) -> TemplateState:
        """Создает глубокую копию состояния."""
        return TemplateState(
            origin=self.origin,
            mode_options=self.mode_options,
            active_tags=set(self.active_tags),
            active_modes=dict(self.active_modes)
        )


class TemplateContext:
    """
    Контекст рендеринга шаблона с управлением состоянием.
    
    Отслеживает активные теги, режимы и их переопределения во время
    обработки шаблона. Поддерживает стек состояний для корректной
    обработки вложенных блоков {% mode %}.
    """
    
    def __init__(self, run_ctx: RunContext):
        """
        Инициализирует контекст шаблона.
        
        Args:
            run_ctx: Контекст выполнения с базовыми настройками
        """
        self.run_ctx = run_ctx
        self.adaptive_loader = run_ctx.adaptive_loader
        
        # Текущее состояние (инициализируется из run_ctx)
        self.current_state = TemplateState(
            origin="self",
            mode_options=run_ctx.mode_options,
            active_tags=set(run_ctx.active_tags),
            active_modes=dict(run_ctx.options.modes)
        )
        
        # Стек состояний для вложенных блоков режимов
        self.state_stack: List[TemplateState] = []
        
        # Кэш наборов тегов для оценки условий
        self._tagsets_cache: Optional[Dict[str, Set[str]]] = None
        
        # Оценщик условий (создается лениво)
        self._condition_evaluator: Optional[TemplateConditionEvaluator] = None
        
    def get_condition_evaluator(self) -> TemplateConditionEvaluator:
        """
        Возвращает оценщик условий для текущего состояния.
        
        Создает новый оценщик или обновляет существующий при изменении состояния.
        """
        if self._condition_evaluator is None:
            self._condition_evaluator = self._create_condition_evaluator()
        else:
            # Обновляем контекст оценщика при изменении состояния
            condition_context = self._create_condition_context()
            self._condition_evaluator.update_context(condition_context)
        
        return self._condition_evaluator
    
    def enter_mode_block(self, modeset: str, mode: str) -> None:
        """
        Входит в блок режима {% mode modeset:mode %}.
        
        Сохраняет текущее состояние и применяет новый режим,
        активируя связанные с ним теги и опции.
        
        Args:
            modeset: Имя набора режимов
            mode: Имя режима в наборе
            
        Raises:
            ValueError: Если режим не найден в конфигурации
        """
        # Сохраняем текущее состояние в стек
        self.state_stack.append(self.current_state.copy())
        
        # Получаем информацию о режиме
        modes_config = self.adaptive_loader.get_modes_config()
        mode_set = modes_config.mode_sets.get(modeset)
        
        if not mode_set:
            raise ValueError(f"Unknown mode set '{modeset}'")
        
        mode_info = mode_set.modes.get(mode)
        if not mode_info:
            available_modes = list(mode_set.modes.keys())
            raise ValueError(
                f"Unknown mode '{mode}' in mode set '{modeset}'. "
                f"Available modes: {', '.join(available_modes)}"
            )
        
        # Применяем новый режим
        self.current_state.active_modes[modeset] = mode
        
        # Активируем теги режима
        self.current_state.active_tags.update(mode_info.tags)
        
        # Обновляем опции режима
        self.current_state.mode_options = ModeOptions.merge_from_modes(
            modes_config, 
            self.current_state.active_modes
        )
        
        # Сбрасываем кэш оценщика условий
        self._condition_evaluator = None
    
    def exit_mode_block(self) -> None:
        """
        Выходит из блока режима {% endmode %}.
        
        Восстанавливает предыдущее состояние из стека.
        
        Raises:
            RuntimeError: Если стек состояний пуст (нет соответствующего входа)
        """
        if not self.state_stack:
            raise RuntimeError("No mode block to exit (state stack is empty)")
        
        # Восстанавливаем предыдущее состояние
        self.current_state = self.state_stack.pop()
        
        # Сбрасываем кэш оценщика условий
        self._condition_evaluator = None
    
    def enter_include_scope(self, origin: str) -> None:
        """
        Входит в скоуп включаемого шаблона.
        
        Сохраняет текущее состояние и обновляет origin для корректной
        обработки условий scope:local и scope:parent.
        
        Args:
            origin: Origin включаемого шаблона ('self' или путь к области)
        """
        # Сохраняем текущее состояние в стек
        self.state_stack.append(self.current_state.copy())
        
        # Обновляем origin в текущем состоянии
        self.current_state = TemplateState(
            origin=origin,
            mode_options=self.current_state.mode_options,
            active_tags=set(self.current_state.active_tags),
            active_modes=dict(self.current_state.active_modes)
        )
        
        # Сбрасываем кэш оценщика условий
        self._condition_evaluator = None
    
    def exit_include_scope(self) -> None:
        """
        Выходит из скоупа включаемого шаблона.
        
        Восстанавливает предыдущее состояние из стека.
        
        Raises:
            RuntimeError: Если стек состояний пуст (нет соответствующего входа)
        """
        if not self.state_stack:
            raise RuntimeError("No include scope to exit (state stack is empty)")
        
        # Восстанавливаем предыдущее состояние
        self.current_state = self.state_stack.pop()
        
        # Сбрасываем кэш оценщика условий
        self._condition_evaluator = None
    
    def evaluate_condition(self, condition_ast) -> bool:
        """
        Вычисляет условие в текущем контексте.
        
        Args:
            condition_ast: AST условия для вычисления
            
        Returns:
            Результат вычисления условия
        """
        evaluator = self.get_condition_evaluator()
        return evaluator.evaluate(condition_ast)
    
    def evaluate_condition_text(self, condition_text: str) -> bool:
        """
        Вычисляет условие из текстового представления.
        
        Args:
            condition_text: Текстовое представление условия
            
        Returns:
            Результат вычисления условия
        """
        evaluator = self.get_condition_evaluator()
        return evaluator.evaluate_condition_text(condition_text)
    
    
    def _create_condition_evaluator(self) -> TemplateConditionEvaluator:
        """Создает новый оценщик условий для текущего состояния."""
        condition_context = self._create_condition_context()
        return TemplateConditionEvaluator(condition_context)
    
    def _create_condition_context(self) -> ConditionContext:
        """Создает контекст условий из текущего состояния шаблона."""
        tagsets = self._get_tagsets()
        
        return ConditionContext(
            active_tags=self.current_state.active_tags,
            tagsets=tagsets,
            origin=self.current_state.origin,
        )
    
    def _get_tagsets(self) -> Dict[str, Set[str]]:
        """
        Возвращает карту наборов тегов.
        
        Кэширует результат для избежания повторной загрузки.
        """
        if self._tagsets_cache is None:
            tags_config = self.adaptive_loader.get_tags_config()
            
            self._tagsets_cache = {}
            
            # Добавляем наборы тегов
            for set_name, tag_set in tags_config.tag_sets.items():
                self._tagsets_cache[set_name] = set(tag_set.tags.keys())
            
            # Добавляем глобальные теги как отдельный набор
            if tags_config.global_tags:
                self._tagsets_cache["global"] = set(tags_config.global_tags.keys())
        
        return self._tagsets_cache
    
    def __enter__(self):
        """Поддержка контекстного менеджера."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Очистка при выходе из контекстного менеджера.
        
        Проверяет, что все режимные блоки корректно закрыты.
        """
        if self.state_stack:
            import warnings
            warnings.warn(
                f"Template context exiting with {len(self.state_stack)} "
                f"unclosed mode blocks. This may indicate missing {{% endmode %}} directives.",
                RuntimeWarning,
                stacklevel=2
            )
