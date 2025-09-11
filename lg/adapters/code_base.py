"""
Базовый класс для адаптеров языков программирования.
Предоставляет общую функциональность для обработки кода и оркестрацию оптимизаций.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, TypeVar, Optional

from .base import BaseAdapter
from .code_analysis import CodeAnalyzer
from .code_model import CodeCfg, PlaceholderConfig
from .context import ProcessingContext, LightweightContext
from .optimizations import (
    PublicApiOptimizer,
    FunctionBodyOptimizer,
    CommentOptimizer,
    ImportOptimizer,
    LiteralOptimizer,
    TreeSitterImportAnalyzer,
    ImportClassifier
)
from .tree_sitter_support import TreeSitterDocument, Node

C = TypeVar("C", bound=CodeCfg)

class CodeAdapter(BaseAdapter[C], ABC):
    """
    Базовый класс для всех адаптеров языков программирования.
    Предоставляет общие методы для обработки кода и системы плейсхолдеров.
    """

    @abstractmethod
    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        """Create a parsed Tree-sitter document."""
        pass

    @abstractmethod
    def create_import_classifier(self, external_patterns: List[str] = None) -> ImportClassifier:
        """Создает языко-специфичный классификатор импортов. Должен быть переопределен наследниками."""
        pass

    @abstractmethod
    def create_import_analyzer(self, classifier: ImportClassifier) -> TreeSitterImportAnalyzer:
        """Создает языко-специфичный анализатор импортов. Должен быть переопределен наследниками."""
        pass

    @abstractmethod
    def create_code_analyzer(self, doc: TreeSitterDocument) -> CodeAnalyzer:
        """Создает языко-специфичный унифицированный анализатор кода."""
        pass

    # ============= ХУКИ для вклинивания в процесс оптимизации ===========

    def hook__remove_function_body(
            self,
            root_optimizer: FunctionBodyOptimizer,
            context: ProcessingContext,
            func_def: Optional[Node],
            body_node: Node,
            func_type: str
    ) -> None:
        """Хук для кастомизации удаления тел функций."""
        root_optimizer.remove_function_body(context, body_node, func_type)

    def get_comment_style(self) -> Tuple[str, tuple[str, str], tuple[str, str]]:
        """Cтиль комментариев для языка (однострочный, многострочный, докстринг)."""
        return "//", ("/*", "*/"), ('/**', '*/')

    def is_documentation_comment(self, comment_text: str) -> bool:
        """Является ли этот комментарий частью системы документирования."""
        return comment_text.strip().startswith('/**')

    def hook__extract_first_sentence(self, root_optimizer: CommentOptimizer, text: str) -> str:
        """Хук для извлечения первого предложение из текста комментария."""
        return root_optimizer.extract_first_sentence(text)

    def hook__smart_truncate_comment(self, root_optimizer: CommentOptimizer, comment_text: str, max_length: int) -> str:
        """Хук для корректного закрытия многострочных комментариев и докстрингов после обрезания."""
        return root_optimizer.smart_truncate_comment(comment_text, max_length)


    # ============= Основной пайплайн работы языковых оптимизаторов ===========

    def process(self, lightweight_ctx: LightweightContext) -> Tuple[str, Dict[str, Any]]:
        """
        Основной метод обработки кода.
        Применяет все конфигурированные оптимизации.
        """
        # Получаем полноценный контекст из облегченного
        context = lightweight_ctx.get_full_context(self, self.tokenizer)

        # Применяем оптимизации
        self._apply_optimizations(context)

        # Финализируем плейсхолдеры
        return self._finalize_placeholders(context, self.cfg.placeholders)

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
        literal_optimizer = LiteralOptimizer(self)
        literal_optimizer.apply(context)

    def _finalize_placeholders(self, context: ProcessingContext, ph_cfg: PlaceholderConfig) -> Tuple[str, Dict[str, Any]]:
        """
        Финализируем плейсхолдеры и применяем их к редактору, получаем финальные метрики.
        """
        collapsed_edits, placeholder_stats = context.placeholders.finalize_edits()

        # Текст исходного диапазона нужен для экономической проверки
        original_bytes = context.raw_text.encode('utf-8')

        min_savings_ratio = ph_cfg.min_savings_ratio
        min_abs_savings_if_none = ph_cfg.min_abs_savings_if_none

        for spec, repl in collapsed_edits:
            # Получаем исходный текст диапазона
            src = original_bytes[spec.start_byte:spec.end_byte].decode('utf-8', errors='ignore')

            # Определяем флаг "пустой" замены
            is_none = (repl == "")

            # Проверка целесообразности
            if not self.tokenizer.is_economical(
                    src,
                    repl,
                    min_ratio=min_savings_ratio,
                    replacement_is_none=is_none,
                    min_abs_savings_if_none=min_abs_savings_if_none,
            ):
                # Пропускаем замену, оставляем оригинал
                continue

            # Применяем уместные плейсхолдеры к редактору
            context.editor.add_replacement(spec.start_byte, spec.end_byte, repl,
                # Тип специально не указываем, так как контекст сам собирает метаинформацию по плейсхолдерам
                edit_type=None
            )

        # Обновляем метрики из плейсхолдеров
        for key, value in placeholder_stats.items():
            if isinstance(value, (int, float)):
                context.metrics.set(key, value)

        # Применяем все изменения в редакторе текста и возвращаем статистику
        result_text, edit_stats = context.editor.apply_edits()

        # Объединяем метрики из редактора и контекста
        metrics = context.metrics.to_dict()
        metrics.update(edit_stats)
        return result_text, metrics
