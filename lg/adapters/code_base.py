"""
Базовый класс для адаптеров языков программирования.
Предоставляет общую функциональность для обработки кода.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, TypeVar

from .base import BaseAdapter
from .code_model import CodeCfg
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
        meta = self._init_meta()
        
        # Парсим исходный код с Tree-sitter
        doc = self.create_document(text, ext)

        # Создаем редактор для range-based изменений
        editor = RangeEditor(text)

        # Применяем оптимизации
        self._apply_optimizations(doc, editor, meta)

        # Применяем все изменения
        result_text, edit_stats = editor.apply_edits()

        # Объединяем статистики
        meta.update(edit_stats)
        
        # Добавляем метаданные группы
        meta.update({
            "_group_size": group_size,
            "_group_mixed": mixed,
            "_adapter": self.name,
        })
        
        return result_text, meta

    def _init_meta(self) -> Dict[str, Any]:
        """Инициализирует метаданные для отслеживания изменений."""
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

        # Обработка тел функций
        if self.cfg.strip_function_bodies:
            self.strip_function_bodies(doc, editor, meta)
            if self.lang_flag__is_oop():
                self.strip_methods_bodies(doc, editor, meta)
            self.hook__strip_function_bodies(doc, editor, meta)
        
        # Обработка комментариев
        self.process_comments(doc, editor, meta)
        
        # Обработка импортов
        self.process_import(doc, editor, meta)
        
        # Другие оптимизации можно добавить здесь
        # if self.cfg.public_api_only:
        #     self.filter_public_api_ts(doc, editor, meta)

    # ============= ХУКИ для вклинивания в процесс оптимизации ===========
    def hook__strip_function_bodies(
        self,
        doc: TreeSitterDocument,
        editor: RangeEditor,
        meta: Dict[str, Any]
    ) -> None:
        pass

    # ========= Оптимизации, полезные для всех/большинства языков =========
    def strip_function_bodies(
        self, 
        doc: TreeSitterDocument, 
        editor: RangeEditor, 
        meta: Dict[str, Any]
    ) -> None:
        """
        Удаляет тела функций.
        """
        cfg = self.cfg.strip_function_bodies
        if not cfg:
            return
        
        # Получаем генератор плейсхолдеров
        comment_style = self.get_comment_style()
        placeholder_gen = PlaceholderGenerator(comment_style)
        
        # Ищем функции для обработки
        functions = doc.query("functions")
        
        for node, capture_name in functions:
            if capture_name == "function_body":
                # Получаем информацию о функции
                start_byte, end_byte = doc.get_node_range(node)
                
                function_text = doc.get_node_text(node)
                start_line, end_line = doc.get_line_range(node)
                lines_count = end_line - start_line + 1
                
                # Проверяем условия удаления
                should_strip = self._should_strip_function_body(cfg, function_text, lines_count)
                
                if should_strip:
                    # Создаем плейсхолдер
                    placeholder = placeholder_gen.create_function_placeholder(
                        lines_removed=lines_count,
                        bytes_removed=end_byte - start_byte,
                        style=self.cfg.placeholders.style
                    )
                    
                    # Добавляем правку
                    editor.add_replacement(
                        start_byte, end_byte, placeholder,
                        type="function_body_removal",
                        is_placeholder=True,
                        lines_removed=lines_count
                    )
                    
                    meta["code.removed.functions"] += 1

    def strip_methods_bodies(
            self,
            doc: TreeSitterDocument,
            editor: RangeEditor,
            meta: Dict[str, Any]
    ) -> None:
        """
        Обрабатывает методы классов.
        """
        cfg = self.cfg.strip_function_bodies
        if not cfg:
            return

        # Получаем генератор плейсхолдеров
        comment_style = self.get_comment_style()
        placeholder_gen = PlaceholderGenerator(comment_style)

        # Ищем методы в классах
        methods = doc.query("methods")

        for node, capture_name in methods:
            if capture_name == "method_body":
                # Получаем информацию о функции
                start_byte, end_byte = doc.get_node_range(node)

                method_text = doc.get_node_text(node)
                start_line, end_line = doc.get_line_range(node)
                lines_count = end_line - start_line + 1

                # Проверяем условия удаления
                should_strip = self._should_strip_function_body(cfg, method_text, lines_count)

                if should_strip:
                    # Создаем плейсхолдер
                    placeholder = placeholder_gen.create_method_placeholder(
                        lines_removed=lines_count,
                        bytes_removed=end_byte - start_byte,
                        style=self.cfg.placeholders.style
                    )

                    # Добавляем правку
                    editor.add_replacement(
                        start_byte, end_byte, placeholder,
                        type="method_body_removal",
                        is_placeholder=True,
                        lines_removed=lines_count
                    )

                    meta["code.removed.methods"] += 1

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
        classifier = self._create_import_classifier(config.external_only_patterns)
        analyzer = self._create_import_analyzer(classifier)
        
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
    
    def _find_consecutive_import_groups(self, import_ranges: List[Tuple[int, int, 'ImportInfo']]) -> List[List]:
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
    
    def _create_import_classifier(self, external_patterns: List[str] = None):
        """Создает языко-специфичный классификатор импортов. Должен быть переопределен наследниками."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement _create_import_classifier")
    
    def _create_import_analyzer(self, classifier):
        """Создает языко-специфичный анализатор импортов. Должен быть переопределен наследниками."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement _create_import_analyzer")

    def _should_strip_function_body(self, cfg, function_text: str, lines_count: int) -> bool:
        """Определяет, нужно ли удалять тело функции."""
        if isinstance(cfg, bool):
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
