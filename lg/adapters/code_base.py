"""
Базовый класс для адаптеров языков программирования.
Предоставляет общую функциональность для обработки кода и оркестрацию оптимизаций.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, TypeVar, Optional, cast

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
    def create_import_classifier(self, external_patterns: List[str]) -> ImportClassifier:
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

    def is_docstring_node(self, node, doc: TreeSitterDocument) -> bool:
        """Проверяет, является ли узел строки докстрингом."""
        return False

    def hook__extract_first_sentence(self, root_optimizer: CommentOptimizer, text: str) -> str:
        """Хук для извлечения первого предложение из текста комментария."""
        return root_optimizer.extract_first_sentence(text)

    def hook__smart_truncate_comment(self, root_optimizer: CommentOptimizer, comment_text: str, max_tokens: int, tokenizer) -> str:
        """Хук для корректного закрытия многострочных комментариев и докстрингов после обрезания."""
        return root_optimizer.smart_truncate_comment(comment_text, max_tokens, tokenizer)


    # ============= Основной пайплайн работы языковых оптимизаторов ===========

    def process(self, lightweight_ctx: LightweightContext) -> Tuple[str, Dict[str, Any]]:
        """
        Основной метод обработки кода.
        Применяет все конфигурированные оптимизации.
        """
        # Подбираем эффективный конфиг при активном бюджете (sandbox без плейсхолдеров)
        effective_cfg = self.cfg
        budget_metrics: dict[str, int] | None = None
        if self.cfg.budget and self.cfg.budget.max_tokens_per_file:
            from .budget import BudgetController
            controller = BudgetController[C](self, self.tokenizer, self.cfg.budget)
            effective_cfg, budget_metrics = controller.fit_config(lightweight_ctx, self.cfg)

        # Получаем полноценный контекст из облегченного уже для реального прогона
        context = lightweight_ctx.get_full_context(self, self.tokenizer)

        # Затем применяем оптимизации по подобранному конфигу
        # Cast for type-narrowing: effective_cfg matches adapter's config type
        self._apply_optimizations(context, cast(C, effective_cfg))

        # Финализируем плейсхолдеры
        text, meta = self._finalize_placeholders(context, effective_cfg.placeholders)

        # Примешиваем метрики бюджета
        if budget_metrics:
            meta.update(budget_metrics)

        return text, meta

    def _apply_optimizations(self, context: ProcessingContext, code_cfg: C) -> None:
        """
        Применение оптимизаций через специализированные модули.
        Каждый модуль отвечает за свой тип оптимизации.
        """
        # Фильтрация по публичному API
        if code_cfg.public_api_only:
            public_api_optimizer = PublicApiOptimizer(self)
            public_api_optimizer.apply(context)

        # Обработка тел функций
        if code_cfg.strip_function_bodies:
            function_body_optimizer = FunctionBodyOptimizer(code_cfg.strip_function_bodies, self)
            function_body_optimizer.apply(context)

        # Обработка комментариев
        comment_optimizer = CommentOptimizer(code_cfg.comment_policy, self)
        comment_optimizer.apply(context)

        # Обработка импортов
        import_optimizer = ImportOptimizer(code_cfg.imports, self)
        import_optimizer.apply(context)

        # Обработка литералов
        literal_optimizer = LiteralOptimizer(code_cfg.literals, self)
        literal_optimizer.apply(context)

    def _finalize_placeholders(self, context: ProcessingContext, ph_cfg: PlaceholderConfig) -> Tuple[str, Dict[str, Any]]:
        """
        Финализируем плейсхолдеры и применяем их к редактору, получаем финальные метрики.
        """
        collapsed_edits, placeholder_stats = context.placeholders.finalize_edits()

        min_savings_ratio = ph_cfg.min_savings_ratio
        min_abs_savings_if_none = ph_cfg.min_abs_savings_if_none

        for spec, repl in collapsed_edits:
            # Получаем исходный текст диапазона
            src = context.raw_text[spec.start_char:spec.end_char]

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
            context.editor.add_replacement(spec.start_char, spec.end_char, repl,
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
