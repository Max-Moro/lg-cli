"""
Базовый класс для адаптеров языков программирования.
Предоставляет общую функциональность для обработки кода и оркестрацию оптимизаций.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, TypeVar, Optional

from .base import BaseAdapter
from .code_model import CodeCfg
from .context import ProcessingContext, LightweightContext
from .tree_sitter_support import TreeSitterDocument, Node
from .optimizations import (
    PublicApiOptimizer,
    FunctionBodyOptimizer,
    CommentOptimizer,
    ImportOptimizer,
    LiteralOptimizer,
    FieldOptimizer,
    FieldsClassifier,
    ImportAnalyzer,
    ImportClassifier
)

C = TypeVar("C", bound=CodeCfg)

class CodeAdapter(BaseAdapter[C], ABC):
    """
    Базовый класс для всех адаптеров языков программирования.
    Предоставляет общие методы для обработки кода и системы плейсхолдеров.
    """

    @abstractmethod
    def get_comment_style(self) -> Tuple[str, tuple[str, str]]:
        """Cтиль комментариев для языка (однострочный, многострочный)."""
        pass

    def is_documentation_comment(self, comment_text: str) -> bool:
        """Является ли этот комментарий частью системы документирования."""
        return False

    @abstractmethod
    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        """Create a parsed Tree-sitter document."""
        pass

    @abstractmethod
    def create_import_classifier(self, external_patterns: List[str] = None) -> ImportClassifier:
        """Создает языко-специфичный классификатор импортов. Должен быть переопределен наследниками."""
        pass

    @abstractmethod
    def create_import_analyzer(self, classifier: ImportClassifier) -> ImportAnalyzer:
        """Создает языко-специфичный анализатор импортов. Должен быть переопределен наследниками."""
        pass

    @abstractmethod
    def create_fields_classifier(self, doc: TreeSitterDocument) -> FieldsClassifier:
        """Создает языко-специфичный классификатор конструкторов и полей."""
        pass

    @abstractmethod
    def is_public_element(self, node: Node, context: ProcessingContext) -> bool:
        """
        Определяет, является ли элемент кода публичным.
        
        Args:
            node: Узел Tree-sitter для анализа
            context: Контекст обработки с доступом к документу
            
        Returns:
            True если элемент публичный, False если приватный/защищенный
        """
        pass

    @abstractmethod
    def is_exported_element(self, node: Node, context: ProcessingContext) -> bool:
        """
        Определяет, экспортируется ли элемент из модуля.
        
        Args:
            node: Узел Tree-sitter для анализа
            context: Контекст обработки с доступом к документу
            
        Returns:
            True если элемент экспортируется, False если только для внутреннего использования
        """
        pass

    def process(self, lightweight_ctx: LightweightContext) -> Tuple[str, Dict[str, Any]]:
        """
        Основной метод обработки кода.
        Применяет все конфигурированные оптимизации.
        """
        # Получаем полноценный контекст из облегченного (ленивая инициализация)
        context = lightweight_ctx.get_full_context(self)

        # Применяем оптимизации
        self._apply_optimizations(context)

        # Применяем все изменения
        result_text, edit_stats = context.editor.apply_edits()

        # Получаем финальные метрики
        final_metrics = context.finalize(lightweight_ctx)
        
        # Объединяем статистики из редактора и контекста
        final_metrics.update(edit_stats)
        final_metrics["_adapter"] = self.name
        
        return result_text, final_metrics

    def _apply_optimizations(self, context: ProcessingContext) -> None:
        """
        Применение оптимизаций через специализированные модули.
        Каждый модуль отвечает за свой тип оптимизации.
        """
        # Фильтрация по публичному API
        if self.cfg.public_api_only:
            public_api_optimizer = PublicApiOptimizer(self)
            public_api_optimizer.apply(context)
        
        # Обработка тел функций
        if self.cfg.strip_function_bodies:
            function_body_optimizer = FunctionBodyOptimizer(self)
            function_body_optimizer.apply(context)
        
        # Обработка комментариев
        comment_optimizer = CommentOptimizer(self)
        comment_optimizer.apply(context)
        
        # Обработка импортов
        import_optimizer = ImportOptimizer(self)
        import_optimizer.apply(context)
        
        # Обработка литералов
        if self.cfg.strip_literals:
            literal_optimizer = LiteralOptimizer(self)
            literal_optimizer.apply(context)
        
        # Обработка полей (конструкторы, геттеры, сеттеры)
        field_optimizer = FieldOptimizer(self)
        field_optimizer.apply(context)

    # ============= ХУКИ для вклинивания в процесс оптимизации ===========

    def hook__remove_function_body(
            self,
            root_optimizer: FunctionBodyOptimizer,
            context: ProcessingContext,
            func_def: Optional[Node],
            body_node: Node,
            func_type: str,
            placeholder_style,
    ) -> None:
        """Хук для кастомизации удаления тел функций."""
        root_optimizer.remove_function_body(context, body_node, func_type, placeholder_style)