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
        context = ProcessingContext(doc, editor, placeholder_gen, self.cfg)

        # Применяем оптимизации
        self._apply_optimizations_v2(context)

        # Применяем все изменения
        result_text, edit_stats = editor.apply_edits()

        # Получаем финальные метрики
        final_metrics = context.finalize(group_size, mixed)
        
        # Объединяем статистики из редактора и контекста
        final_metrics.update(edit_stats)
        final_metrics["_adapter"] = self.name
        
        return result_text, final_metrics

    def _apply_optimizations_v2(self, context: ProcessingContext) -> None:
        """
        Новая версия применения оптимизаций через ProcessingContext.
        Решает проблему прокидывания состояния (doc, editor, meta).
        """
        # Обработка тел функций - используем единый метод для избежания перекрытий
        if self.cfg.strip_function_bodies:
            self._strip_all_function_bodies_v2(context)
            self.hook__strip_function_bodies_v2(context)
        
        # Обработка комментариев
        self.process_comments_v2(context)
        
        # Обработка импортов
        self.process_import_v2(context)
        
        # Другие оптимизации можно добавить здесь
        # if self.cfg.public_api_only:
        #     self.filter_public_api_v2(context)

    def _init_meta(self) -> Dict[str, Any]:
        """
        DEPRECATED: Инициализирует метаданные для отслеживания изменений.
        Используйте ProcessingContext.metrics для новой логики.
        """
        return {
            "code.removed.functions": 0,
            "code.removed.methods": 0,
            "code.removed.comments": 0,
            "code.removed.imports": 0,
            "code.removed.literals": 0,
            "code.trimmed.fields": 0,
            "code.placeholders": 0,
            "code.lines_saved": 0,
            "code.bytes_saved": 0,
        }

    def _apply_optimizations(
        self, 
        doc: TreeSitterDocument, 
        editor: RangeEditor, 
        meta: Dict[str, Any]
    ) -> None:
        """
        Применяет оптимизации используя Tree-sitter документ.
        Конкретные адаптеры не должны переопределять данный метод.
        Для кастомизации логики необходимо использовать языковые флаги или дополнительные хуки.
        """

        # Обработка тел функций - используем единый метод для избежания перекрытий
        if self.cfg.strip_function_bodies:
            self._strip_all_function_bodies(doc, editor, meta)
            self.hook__strip_function_bodies(doc, editor, meta)
        
        # Обработка комментариев
        self.process_comments(doc, editor, meta)
        
        # Обработка импортов
        self.process_import(doc, editor, meta)
        
        # Другие оптимизации можно добавить здесь
        # if self.cfg.public_api_only:
        #     self.filter_public_api_ts(doc, editor, meta)

    # ============= НОВЫЕ ХУКИ с ProcessingContext ===========
    def hook__strip_function_bodies_v2(self, context: ProcessingContext) -> None:
        """Хук для кастомизации удаления тел функций через контекст."""
        pass

    # ============= УСТАРЕВШИЕ ХУКИ (для обратной совместимости) ===========
    def hook__strip_function_bodies(
        self,
        doc: TreeSitterDocument,
        editor: RangeEditor,
        meta: Dict[str, Any]
    ) -> None:
        """DEPRECATED: используйте hook__strip_function_bodies_v2."""
        pass

    # ========= НОВЫЕ ОПТИМИЗАЦИИ с ProcessingContext =========
    def _strip_all_function_bodies_v2(self, context: ProcessingContext) -> None:
        """
        Новая версия удаления тел функций через ProcessingContext.
        Решает проблему прокидывания состояния и ленивых метрик.
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
                    
                    # Используем удобный метод контекста
                    context.remove_function_body(
                        node, 
                        func_type=func_type,
                        placeholder_style=self.cfg.placeholders.style
                    )

    def process_comments_v2(self, context: ProcessingContext) -> None:
        """
        Новая версия обработки комментариев через ProcessingContext.
        """
        policy = self.cfg.comment_policy
        
        # Если политика keep_all, ничего не делаем
        if isinstance(policy, str) and policy == "keep_all":
            return
        
        # Ищем комментарии
        comments = context.query("comments")

        for node, capture_name in comments:
            comment_text = context.get_node_text(node)
            
            should_remove, replacement = self._should_process_comment_v2(
                policy, capture_name, comment_text, context
            )
            
            if should_remove:
                context.remove_comment(
                    node,
                    comment_type=capture_name,
                    replacement=replacement,
                    placeholder_style=self.cfg.placeholders.style
                )

    def _should_process_comment_v2(
        self, 
        policy, 
        capture_name: str, 
        comment_text: str, 
        context: ProcessingContext
    ) -> Tuple[bool, str]:
        """
        Новая версия определения обработки комментария через ProcessingContext.
        
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

    def process_import_v2(self, context: ProcessingContext) -> None:
        """
        Новая версия обработки импортов через ProcessingContext.
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
            self._process_external_only_v2(grouped["local"], context)
        
        elif config.policy == "summarize_long":
            # Суммаризируем длинные списки импортов
            if analyzer.should_summarize(imports, config.max_items_before_summary):
                self._process_summarize_long_v2(grouped, analyzer, context)

    def _process_external_only_v2(
        self,
        local_imports: List,
        context: ProcessingContext
    ) -> None:
        """Новая версия удаления локальных импортов через ProcessingContext."""
        if not local_imports:
            return
        
        for imp in local_imports:
            context.remove_import(
                imp.node,
                import_type="local_import",
                placeholder_style=self.cfg.placeholders.style
            )

    def _process_summarize_long_v2(
        self,
        grouped_imports: Dict[str, List],
        analyzer,
        context: ProcessingContext,
    ) -> None:
        """Новая версия суммаризации длинных импортов через ProcessingContext."""
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

    # ========= УСТАРЕВШИЕ ОПТИМИЗАЦИИ (для обратной совместимости) =========
    def _strip_all_function_bodies(
        self, 
        doc: TreeSitterDocument, 
        editor: RangeEditor, 
        meta: Dict[str, Any]
    ) -> None:
        """
        Единый метод для удаления тел функций и методов без дублирования правок.
        """
        cfg = self.cfg.strip_function_bodies
        if not cfg:
            return
        
        # Получаем генератор плейсхолдеров
        comment_style = self.get_comment_style()
        placeholder_gen = PlaceholderGenerator(comment_style)
        
        # Ищем все функции и классифицируем их как функции или методы
        functions = doc.query("functions")
        for node, capture_name in functions:
            if capture_name == "function_body":
                # Определяем, является ли это методом (находится ли внутри класса)
                func_type = "method" if self._is_method(node, doc) else "function"
                self._process_function_body(
                    node, doc, editor, meta,
                    placeholder_gen, cfg, func_type
                )

    def _process_function_body(
        self, 
        node, 
        doc: TreeSitterDocument,
        editor: RangeEditor, 
        meta: Dict[str, Any],
        placeholder_gen: PlaceholderGenerator,
        cfg,
        func_type: str  # "function" or "method"
    ) -> None:
        """Обрабатывает одно тело функции/метода."""
        start_byte, end_byte = doc.get_node_range(node)
        
        function_text = doc.get_node_text(node)
        start_line, end_line = doc.get_line_range(node)
        lines_count = end_line - start_line + 1
        
        # Проверяем условия удаления
        should_strip = self._should_strip_function_body(cfg, function_text, lines_count)
        
        if should_strip:
            # Создаем плейсхолдер
            if func_type == "method":
                placeholder = placeholder_gen.create_method_placeholder(
                    lines_removed=lines_count,
                    bytes_removed=end_byte - start_byte,
                    style=self.cfg.placeholders.style
                )
                meta["code.removed.methods"] += 1
            else:
                placeholder = placeholder_gen.create_function_placeholder(
                    lines_removed=lines_count,
                    bytes_removed=end_byte - start_byte,
                    style=self.cfg.placeholders.style
                )
                meta["code.removed.functions"] += 1
            
            # Добавляем правку
            editor.add_replacement(
                start_byte, end_byte, placeholder,
                type=f"{func_type}_body_removal",
                is_placeholder=True,
                lines_removed=lines_count
            )

    def _is_method(self, function_body_node, doc: TreeSitterDocument) -> bool:
        """
        Определяет, является ли узел function_body методом класса.
        Проходит вверх по дереву в поисках class_definition или class_declaration.
        """
        current = function_body_node.parent
        while current:
            if current.type in ("class_definition", "class_declaration"):
                return True
            current = current.parent
        return False

    def process_comments(
        self, 
        doc: TreeSitterDocument, 
        editor: RangeEditor, 
        meta: Dict[str, Any]
    ) -> None:
        """
        Обрабатывает комментарии согласно политике comment_policy.
        """
        policy = self.cfg.comment_policy
        
        # Если политика keep_all, ничего не делаем
        if isinstance(policy, str) and policy == "keep_all":
            return
        
        # Получаем генератор плейсхолдеров
        comment_style = self.get_comment_style()
        placeholder_gen = PlaceholderGenerator(comment_style)
        
        # Ищем комментарии
        comments = doc.query("comments")

        for node, capture_name in comments:
            start_byte, end_byte = doc.get_node_range(node)

            comment_text = doc.get_node_text(node)
            start_line, end_line = doc.get_line_range(node)
            lines_count = end_line - start_line + 1
            
            should_remove, replacement = self._should_process_comment(
                policy, capture_name, comment_text, placeholder_gen
            )
            
            if should_remove:
                editor.add_replacement(
                    start_byte, end_byte, replacement,
                    type=f"{capture_name}_removal",
                    is_placeholder=bool(replacement),
                    lines_removed=lines_count
                )
                
                if capture_name == "comment":
                    meta["code.removed.comments"] += 1
                elif capture_name == "docstring":
                    # Count docstrings separately if needed
                    meta["code.removed.comments"] += 1
    
    def _should_process_comment(
        self, 
        policy, 
        capture_name: str, 
        comment_text: str, 
        placeholder_gen: PlaceholderGenerator
    ) -> Tuple[bool, str]:
        """
        Определяет нужно ли обрабатывать комментарий и какую замену использовать.
        
        Returns:
            Tuple of (should_remove, replacement_text)
        """
        # Простая строковая политика
        if isinstance(policy, str):
            if policy == "keep_all":
                return False, ""
            elif policy == "strip_all":
                # Удаляем все комментарии с плейсхолдером
                placeholder = placeholder_gen.create_comment_placeholder(
                    capture_name, style=self.cfg.placeholders.style
                )
                return True, placeholder
            elif policy == "keep_doc":
                # Удаляем обычные комментарии, сохраняем докстринги
                if capture_name == "comment":
                    placeholder = placeholder_gen.create_comment_placeholder(
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
                    placeholder = placeholder_gen.create_comment_placeholder(
                        capture_name, style=self.cfg.placeholders.style
                    )
                    return True, placeholder
        
        # TODO: Обработка комплексной политики (CommentConfig)
        
        return False, ""
    
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
    
    def process_import(
        self, 
        doc: TreeSitterDocument, 
        editor: RangeEditor, 
        meta: Dict[str, Any]
    ) -> None:
        """
        Обрабатывает импорты согласно политике import_config.
        """
        config = self.cfg.import_config
        
        # Если политика keep_all, ничего не делаем
        if config.policy == "keep_all":
            return
        
        # Языковые адаптеры должны предоставлять свои реализации
        classifier = self.create_import_classifier(config.external_only_patterns)
        analyzer = self.create_import_analyzer(classifier)
        
        # Анализируем все импорты
        imports = analyzer.analyze_imports(doc)
        if not imports:
            return
        
        # Группируем по типу
        grouped = analyzer.group_imports(imports)
        
        # Получаем генератор плейсхолдеров
        comment_style = self.get_comment_style()
        placeholder_gen = PlaceholderGenerator(comment_style)
        
        if config.policy == "external_only":
            # Удаляем локальные импорты, оставляем внешние
            self._process_external_only(grouped["local"], editor, placeholder_gen, meta)
        
        elif config.policy == "summarize_long":
            # Суммаризируем длинные списки импортов
            if analyzer.should_summarize(imports, config.max_items_before_summary):
                self._process_summarize_long(grouped, analyzer, editor, placeholder_gen, meta)
    
    def _process_external_only(
        self,
        local_imports: List,
        editor: RangeEditor,
        placeholder_gen: PlaceholderGenerator,
        meta: Dict[str, Any]
    ) -> None:
        """Удаляет локальные импорты, оставляя только внешние."""

        if not local_imports:
            return
        
        for imp in local_imports:
            start_byte, end_byte = imp.start_byte, imp.end_byte

            # Создаем плейсхолдер для удаленных локальных импортов
            placeholder = placeholder_gen.create_import_placeholder(
                count=1, style=self.cfg.placeholders.style
            )
            
            editor.add_replacement(
                start_byte, end_byte, placeholder,
                type="local_import_removal",
                is_placeholder=True,
                lines_removed=imp.line_count
            )
            
            meta["code.removed.imports"] += 1
    
    def _process_summarize_long(
        self,
        grouped_imports: Dict[str, List],
        analyzer,
        editor: RangeEditor,
        placeholder_gen: PlaceholderGenerator,
        meta: Dict[str, Any],
    ) -> None:
        """Суммаризирует длинные списки импортов."""

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
                
                # Получаем диапазон всей группы
                start_byte = group[0][0]
                end_byte = group[-1][1]

                # Создаем суммарный плейсхолдер
                module_names = [imp[2].module_name for imp in group]
                summary = self._create_import_summary(module_names, group_type)
                
                placeholder = f"# {summary}"  # Используем простой формат
                if self.cfg.placeholders.style == "block":
                    placeholder = placeholder_gen.create_custom_placeholder(
                        summary, {}, style="block"
                    )
                
                total_lines = sum(imp[2].line_count for imp in group)
                
                editor.add_replacement(
                    start_byte, end_byte, placeholder,
                    type="import_summarization",
                    is_placeholder=True,
                    lines_removed=total_lines
                )
                
                meta["code.removed.imports"] += len(group)
    
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
    
    def _create_import_summary(self, module_names: List[str], group_type: str) -> str:
        """Создает краткое описание суммаризированных импортов."""
        count = len(module_names)
        
        if group_type == "external":
            if count <= 3:
                return f"… {count} external imports: {', '.join(module_names[:3])}"
            else:
                return f"… {count} external imports: {', '.join(module_names[:2])}, ..."
        else:
            return f"… {count} local imports"
    
    def create_import_classifier(self, external_patterns: List[str] = None):
        """Создает языко-специфичный классификатор импортов. Должен быть переопределен наследниками."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement _create_import_classifier")
    
    def create_import_analyzer(self, classifier):
        """Создает языко-специфичный анализатор импортов. Должен быть переопределен наследниками."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement _create_import_analyzer")

    def _should_strip_function_body(self, cfg, function_text: str, lines_count: int) -> bool:
        """Определяет, нужно ли удалять тело функции."""
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
            # TODO: реализовать public_only, non_public после добавления семантики
        
        return False
