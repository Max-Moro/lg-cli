"""
Базовый класс для адаптеров языков программирования.
Предоставляет общую функциональность для обработки кода.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, TypeVar

from .base import BaseAdapter
from .code_model import CodeCfg
from .context import ProcessingContext
from .import_utils import ImportInfo
from .range_edits import RangeEditor, PlaceholderGenerator
from .tree_sitter_support import TreeSitterDocument

C = TypeVar("C", bound=CodeCfg)

class CodeAdapter(BaseAdapter[C], ABC):
    """
    Базовый класс для всех адаптеров языков программирования.
    Предоставляет общие методы для обработки кода и системы плейсхолдеров.
    """

    @abstractmethod
    def lang_flag__is_oop(self) -> bool:
        """В языке есть как функции, так и методы классов."""
        pass

    @abstractmethod
    def lang_flag__with_access_modifiers(self) -> bool:
        """В языке есть модификаторы доступа."""
        pass

    @abstractmethod
    def get_comment_style(self) -> Tuple[str, tuple[str, str]]:
        """Cтиль комментариев для языка (однострочный, многострочный)."""
        pass

    @abstractmethod
    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        """Create a parsed Tree-sitter document."""
        pass

    def process(self, text: str, ext: str, group_size: int, mixed: bool) -> Tuple[str, Dict[str, Any]]:
        """
        Основной метод обработки кода.
        Применяет все конфигурированные оптимизации.
        """
        # Парсим исходный код с Tree-sitter
        doc = self.create_document(text, ext)

        # Создаем редактор для range-based изменений
        editor = RangeEditor(text)

        # Создаем генератор плейсхолдеров
        placeholder_gen = PlaceholderGenerator(self.get_comment_style())

        # Создаем контекст обработки
        context = ProcessingContext(doc, editor, placeholder_gen)

        # Применяем оптимизации
        self._apply_optimizations(context)

        # Применяем все изменения
        result_text, edit_stats = editor.apply_edits()

        # Получаем финальные метрики
        final_metrics = context.finalize(group_size, mixed)
        
        # Объединяем статистики из редактора и контекста
        final_metrics.update(edit_stats)
        final_metrics["_adapter"] = self.name
        
        return result_text, final_metrics

    def _apply_optimizations(self, context: ProcessingContext) -> None:
        """
        Применение оптимизаций.
        """
        # Обработка тел функций - используем единый метод для избежания перекрытий
        if self.cfg.strip_function_bodies:
            self._strip_all_function_bodies(context)
            self.hook__strip_function_bodies(context)
        
        # Обработка комментариев
        self.process_comments(context)
        
        # Обработка импортов
        self.process_import(context)
        
        # Другие оптимизации можно добавить здесь
        # if self.cfg.public_api_only:
        #     self.filter_public_api(context)


    # ============= ХУКИ для вклинивания в процесс оптимизации ===========
    def hook__strip_function_bodies(self, context: ProcessingContext) -> None:
        """Хук для кастомизации удаления тел функций через контекст."""
        pass

    # ========= Оптимизации, полезные для всех/большинства языков =========
    def _strip_all_function_bodies(self, context: ProcessingContext) -> None:
        """
        Удаление тел функций.
        """
        cfg = self.cfg.strip_function_bodies
        if not cfg:
            return
        
        # Ищем все функции и классифицируем их как функции или методы
        functions = context.query("functions")
        for node, capture_name in functions:
            if capture_name == "function_body":
                function_text = context.get_node_text(node)
                start_line, end_line = context.get_line_range(node)
                lines_count = end_line - start_line + 1
                
                # Определяем, нужно ли удалять тело
                should_strip = context.should_strip_function_body(function_text, lines_count, cfg)
                
                if should_strip:
                    # Определяем тип (метод vs функция)
                    func_type = "method" if context.is_method(node) else "function"
                    
                    context.remove_function_body(
                        node, 
                        func_type=func_type,
                        placeholder_style=self.cfg.placeholders.style
                    )

    def process_comments(self, context: ProcessingContext) -> None:
        """
        Обработка комментариев.
        """
        policy = self.cfg.comment_policy
        
        # Если политика keep_all, ничего не делаем
        if isinstance(policy, str) and policy == "keep_all":
            return
        
        # Ищем комментарии
        comments = context.query("comments")

        for node, capture_name in comments:
            comment_text = context.get_node_text(node)
            
            should_remove, replacement = self._should_process_comment(
                policy, capture_name, comment_text, context
            )
            
            if should_remove:
                context.remove_comment(
                    node,
                    comment_type=capture_name,
                    replacement=replacement,
                    placeholder_style=self.cfg.placeholders.style
                )

    def _should_process_comment(
        self, 
        policy, 
        capture_name: str, 
        comment_text: str, 
        context: ProcessingContext
    ) -> Tuple[bool, str]:
        """
        Определение обработки комментария.
        
        Returns:
            Tuple of (should_remove, replacement_text)
        """
        # Простая строковая политика
        if isinstance(policy, str):
            if policy == "keep_all":
                return False, ""
            elif policy == "strip_all":
                # Удаляем все комментарии с плейсхолдером
                placeholder = context.placeholder_gen.create_comment_placeholder(
                    capture_name, style=self.cfg.placeholders.style
                )
                return True, placeholder
            elif policy == "keep_doc":
                # Удаляем обычные комментарии, сохраняем докстринги
                if capture_name == "comment":
                    placeholder = context.placeholder_gen.create_comment_placeholder(
                        capture_name, style=self.cfg.placeholders.style
                    )
                    return True, placeholder
                else:
                    return False, ""
            elif policy == "keep_first_sentence":
                # Для докстрингов оставляем первое предложение
                if capture_name == "docstring":
                    first_sentence = self._extract_first_sentence(comment_text)
                    if first_sentence != comment_text:
                        return True, first_sentence
                # Обычные комментарии удаляем
                elif capture_name == "comment":
                    placeholder = context.placeholder_gen.create_comment_placeholder(
                        capture_name, style=self.cfg.placeholders.style
                    )
                    return True, placeholder
        
        # TODO: Обработка комплексной политики (CommentConfig)
        
        return False, ""

    def process_import(self, context: ProcessingContext) -> None:
        """
        Обработка импортов.
        """
        config = self.cfg.import_config
        
        # Если политика keep_all, ничего не делаем
        if config.policy == "keep_all":
            return
        
        # Языковые адаптеры должны предоставлять свои реализации
        classifier = self.create_import_classifier(config.external_only_patterns)
        analyzer = self.create_import_analyzer(classifier)
        
        # Анализируем все импорты
        imports = analyzer.analyze_imports(context.doc)
        if not imports:
            return
        
        # Группируем по типу
        grouped = analyzer.group_imports(imports)
        
        if config.policy == "external_only":
            # Удаляем локальные импорты, оставляем внешние
            self._process_external_only(grouped["local"], context)
        
        elif config.policy == "summarize_long":
            # Суммаризируем длинные списки импортов
            if analyzer.should_summarize(imports, config.max_items_before_summary):
                self._process_summarize_long(grouped, context)

    def _process_external_only(
        self,
        local_imports: List,
        context: ProcessingContext
    ) -> None:
        """Удаление локальных импортов."""
        if not local_imports:
            return
        
        for imp in local_imports:
            context.remove_import(
                imp.node,
                import_type="local_import",
                placeholder_style=self.cfg.placeholders.style
            )

    def _process_summarize_long(
        self,
        grouped_imports: Dict[str, List],
        context: ProcessingContext,
    ) -> None:
        """Суммаризация длинных импортов."""
        # Обрабатываем каждую группу отдельно
        for group_type, imports in grouped_imports.items():
            if not imports or len(imports) <= self.cfg.import_config.max_items_before_summary:
                continue
            
            # Группируем последовательные импорты для суммаризации
            import_ranges = []
            for imp in imports:
                import_ranges.append((imp.start_byte, imp.end_byte, imp))
            
            # Сортируем по позиции в файле
            import_ranges.sort(key=lambda x: x[0])
            
            # Ищем группы последовательных импортов
            groups = self._find_consecutive_import_groups(import_ranges)
            
            for group in groups:
                if len(group) <= 2:  # Не суммаризируем маленькие группы
                    continue
                
                # Используем метод контекста для группового удаления
                context.remove_consecutive_imports(
                    group, group_type, self.cfg.placeholders.style
                )

    def _extract_first_sentence(self, text: str) -> str:
        """Извлекает первое предложение из текста."""
        # Убираем кавычки для Python docstrings
        clean_text = text.strip('"\'')
        
        # Ищем первое предложение (заканчивается на . ! ?)
        import re
        sentences = re.split(r'[.!?]+', clean_text)
        if sentences and sentences[0].strip():
            first = sentences[0].strip()
            # Восстанавливаем кавычки если это Python docstring
            if text.startswith('"""') or text.startswith("'''"):
                return f'"""{first}."""'
            elif text.startswith('"') or text.startswith("'"):
                quote = text[0]
                return f'{quote}{first}.{quote}'
            else:
                return f"{first}."
        
        return text  # Fallback к оригинальному тексту
    
    def _find_consecutive_import_groups(self, import_ranges: List[Tuple[int, int, ImportInfo]]) -> List[List]:
        """Находит группы последовательных импортов."""
        if not import_ranges:
            return []
        
        groups = []
        current_group = [import_ranges[0]]
        
        for i in range(1, len(import_ranges)):
            prev_end = current_group[-1][1]
            curr_start = import_ranges[i][0]
            
            # Если между импортами мало пространства (только пробелы/переносы), считаем их последовательными
            if curr_start - prev_end < 50:  # Эвристика: 50 байт
                current_group.append(import_ranges[i])
            else:
                if len(current_group) > 1:
                    groups.append(current_group)
                current_group = [import_ranges[i]]
        
        if len(current_group) > 1:
            groups.append(current_group)
        
        return groups
    
    def create_import_classifier(self, external_patterns: List[str] = None):
        """Создает языко-специфичный классификатор импортов. Должен быть переопределен наследниками."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement _create_import_classifier")
    
    def create_import_analyzer(self, classifier):
        """Создает языко-специфичный анализатор импортов. Должен быть переопределен наследниками."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement _create_import_analyzer")
