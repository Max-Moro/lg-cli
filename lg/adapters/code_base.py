"""
Базовый класс для адаптеров языков программирования.
Предоставляет общую функциональность для обработки кода.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, TypeVar, Optional

from .base import BaseAdapter
from .code_model import CodeCfg, CommentConfig
from .context import ProcessingContext
from .import_utils import ImportInfo
from .range_edits import RangeEditor, PlaceholderGenerator
from .tree_sitter_support import TreeSitterDocument, Node

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

    @abstractmethod
    def create_import_classifier(self, external_patterns: List[str] = None):
        """Создает языко-специфичный классификатор импортов. Должен быть переопределен наследниками."""
        pass

    @abstractmethod
    def create_import_analyzer(self, classifier):
        """Создает языко-специфичный анализатор импортов. Должен быть переопределен наследниками."""
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
        # Фильтрация по публичному API
        if self.cfg.public_api_only:
            self.filter_public_api(context)
        
        # Обработка тел функций - используем единый метод для избежания перекрытий
        if self.cfg.strip_function_bodies:
            self._strip_all_function_bodies(context)
            self.hook__strip_function_bodies(context)
        
        # Обработка комментариев
        self.process_comments(context)
        
        # Обработка импортов
        self.process_import(context)


    # ============= ХУКИ для вклинивания в процесс оптимизации ===========
    def hook__strip_function_bodies(self, context: ProcessingContext) -> None:
        """Хук для кастомизации удаления тел функций через контекст."""
        pass

    # ========= Оптимизации, полезные для всех/большинства языков =========
    def filter_public_api(self, context: ProcessingContext) -> None:
        """
        Фильтрация кода для показа только публичного API.
        Помечает приватные элементы для пропуска в других оптимизациях.
        """
        # Ищем все функции и методы
        functions = context.query("functions")
        private_ranges = []
        
        for node, capture_name in functions:
            if capture_name in ("function_name", "method_name"):
                function_def = node.parent
                # Проверяем публичность элемента
                is_public = self.is_public_element(function_def, context)
                is_exported = self.is_exported_element(function_def, context)
                
                # Для методов - учитываем модификаторы доступа
                # Для top-level функций - главное экспорт  
                if capture_name == "method_name":
                    # Метод удаляется если он приватный/защищенный
                    if not is_public:
                        start_byte, end_byte = context.get_node_range(function_def)
                        private_ranges.append((start_byte, end_byte, function_def))
                else:  # function_name
                    # Top-level функция удаляется если не экспортируется
                    if not is_exported:
                        start_byte, end_byte = context.get_node_range(function_def)
                        private_ranges.append((start_byte, end_byte, function_def))
        
        # Также проверяем классы
        classes = context.query("classes")
        for node, capture_name in classes:
            if capture_name == "class_name":
                class_def = node.parent
                # Проверяем экспорт класса
                is_exported = self.is_exported_element(class_def, context)
                
                # Для top-level элементов главное - экспорт, а не модификаторы доступа
                # Класс удаляется если он НЕ экспортируется (независимо от модификаторов)
                if not is_exported:
                    start_byte, end_byte = context.get_node_range(class_def)
                    private_ranges.append((start_byte, end_byte, class_def))
        
        # Сортируем по позиции (от конца к началу для безопасного удаления)
        private_ranges.sort(key=lambda x: x[0], reverse=True)
        
        # Удаляем приватные элементы целиком
        for start_byte, end_byte, element in private_ranges:
            start_line, end_line = context.get_line_range(element)
            lines_count = end_line - start_line + 1
            
            placeholder = context.placeholder_gen.create_custom_placeholder(
                "… private element omitted (−{lines})",
                {"lines": lines_count},
                style=self.cfg.placeholders.style
            )
            
            context.editor.add_replacement(
                start_byte, end_byte, placeholder,
                type="private_element_removal",
                is_placeholder=True,
                lines_removed=lines_count
            )
            
            context.metrics.increment("code.removed.private_elements")
            context.metrics.add_lines_saved(lines_count)
            context.metrics.mark_placeholder_inserted()

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
            # Поддерживаем как function_body, так и method_body
            if capture_name in ("function_body", "method_body"):
                start_line, end_line = context.get_line_range(node)
                lines_count = end_line - start_line + 1
                
                # Определяем, нужно ли удалять тело
                should_strip = self.should_strip_function_body(node, lines_count, cfg, context)
                
                if should_strip:
                    # Определяем тип (метод vs функция)
                    func_type = "method" if capture_name == "method_body" or context.is_method(node) else "function"
                    
                    context.remove_function_body(
                        node, 
                        func_type=func_type,
                        placeholder_style=self.cfg.placeholders.style
                    )

    def should_strip_function_body(
        self, 
        body_node: Node, 
        lines_count: int,
        cfg, 
        context: ProcessingContext
    ) -> bool:
        """
        Логика определения необходимости удаления тела функции.
        """
        if isinstance(cfg, bool):
            # Для булевого значения True применяем умную логику:
            # не удаляем однострочные тела (особенно важно для стрелочных функций)
            if cfg and lines_count <= 1:
                return False
            return cfg
        
        # Если конфигурация - объект, применяем более сложную логику
        if hasattr(cfg, 'mode'):
            if cfg.mode == "none":
                return False
            elif cfg.mode == "all":
                return True
            elif cfg.mode == "large_only":
                return lines_count >= getattr(cfg, 'min_lines', 5)
            elif cfg.mode == "public_only":
                # Удаляем тела только у публичных функций
                parent_function = self._find_function_definition(body_node)
                if parent_function:
                    is_public = self.is_public_element(parent_function, context)
                    is_exported = self.is_exported_element(parent_function, context)
                    return is_public or is_exported
                return False
            elif cfg.mode == "non_public":
                # Удаляем тела только у приватных функций
                parent_function = self._find_function_definition(body_node)
                if parent_function:
                    is_public = self.is_public_element(parent_function, context)
                    is_exported = self.is_exported_element(parent_function, context)
                    return not (is_public or is_exported)
                return False
        
        return False

    def _find_function_definition(self, body_node: Node) -> Optional[Node]:
        """
        Найти узел определения функции для заданного тела функции.
        """
        current = body_node.parent
        while current:
            if current.type in ("function_definition", "method_definition", "arrow_function"):
                return current
            current = current.parent
        return None

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
        
        # Обработка комплексной политики (CommentConfig)
        elif hasattr(policy, 'policy'):
            return self._process_complex_comment_policy(policy, capture_name, comment_text, context)
        
        return False, ""

    def _process_complex_comment_policy(
        self,
        policy: CommentConfig,
        capture_name: str,
        comment_text: str,
        context: ProcessingContext
    ) -> Tuple[bool, str]:
        """
        Обработка комплексной политики комментариев (CommentConfig).
        
        Returns:
            Tuple of (should_remove, replacement_text)
        """
        import re
        
        # Проверяем на принудительное удаление по strip_patterns
        for pattern in policy.strip_patterns:
            try:
                if re.search(pattern, comment_text, re.IGNORECASE):
                    placeholder = context.placeholder_gen.create_comment_placeholder(
                        capture_name, style=self.cfg.placeholders.style
                    )
                    return True, placeholder
            except re.error:
                # Игнорируем некорректные regex паттерны
                continue
        
        # Проверяем на сохранение по keep_annotations
        for pattern in policy.keep_annotations:
            try:
                if re.search(pattern, comment_text, re.IGNORECASE):
                    # Проверяем max_length для сохраняемых комментариев
                    if policy.max_length is not None and len(comment_text) > policy.max_length:
                        # Обрезаем комментарий до максимальной длины
                        truncated = comment_text[:policy.max_length].rstrip()
                        # Добавляем индикатор обрезки
                        truncated += "..."
                        return True, truncated
                    return False, ""  # Сохраняем как есть
            except re.error:
                # Игнорируем некорректные regex паттерны
                continue
        
        # Применяем базовую политику с учетом max_length
        base_policy = policy.policy
        if base_policy == "keep_all":
            # Проверяем max_length даже для keep_all
            if policy.max_length is not None and len(comment_text) > policy.max_length:
                truncated = comment_text[:policy.max_length].rstrip() + "..."
                return True, truncated
            return False, ""
        
        elif base_policy == "strip_all":
            placeholder = context.placeholder_gen.create_comment_placeholder(
                capture_name, style=self.cfg.placeholders.style
            )
            return True, placeholder
        
        elif base_policy == "keep_doc":
            if capture_name == "comment":
                placeholder = context.placeholder_gen.create_comment_placeholder(
                    capture_name, style=self.cfg.placeholders.style
                )
                return True, placeholder
            else:  # docstring
                if policy.max_length is not None and len(comment_text) > policy.max_length:
                    truncated = comment_text[:policy.max_length].rstrip() + "..."
                    return True, truncated
                return False, ""
        
        elif base_policy == "keep_first_sentence":
            if capture_name == "docstring":
                first_sentence = self._extract_first_sentence(comment_text)
                # Применяем max_length к извлеченному предложению
                if policy.max_length is not None and len(first_sentence) > policy.max_length:
                    first_sentence = first_sentence[:policy.max_length].rstrip() + "..."
                if first_sentence != comment_text:
                    return True, first_sentence
            elif capture_name == "comment":
                placeholder = context.placeholder_gen.create_comment_placeholder(
                    capture_name, style=self.cfg.placeholders.style
                )
                return True, placeholder
        
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
