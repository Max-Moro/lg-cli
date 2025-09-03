"""
Базовый класс для адаптеров языков программирования.
Предоставляет общую функциональность для обработки кода.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any, TypeVar

from .base import BaseAdapter
from .code_model import CodeCfg, PlaceholderConfig, create_lang_config
from .range_edits import RangeEditor, PlaceholderGenerator
from .tree_sitter_support import (
    TreeSitterDocument, create_document, is_tree_sitter_available,
    TreeSitterError
)

C = TypeVar("C", bound=CodeCfg)

class CodeAdapter(BaseAdapter[C], ABC):
    """
    Базовый класс для всех адаптеров языков программирования.
    Предоставляет общие методы для обработки кода и системы плейсхолдеров.
    """

    @classmethod
    def load_cfg(cls, raw_cfg: dict | None) -> C:
        """
        Загружает конфигурацию с учетом специфики языка.
        Переопределяет базовый метод для создания язык-специфичной конфигурации.
        """
        # create_lang_config возвращает CodeCfg или его наследника
        config = create_lang_config(cls.name, raw_cfg)
        return config  # type: ignore[return-value]

    def process(self, text: str, group_size: int, mixed: bool) -> Tuple[str, Dict[str, Any]]:
        """
        Основной метод обработки кода.
        Применяет все конфигурированные оптимизации.
        """
        # Проверяем доступность Tree-sitter
        if not is_tree_sitter_available():
            # Fallback to simple processing without Tree-sitter
            return self._fallback_process(text, group_size, mixed)
        
        meta = self._init_meta()
        
        try:
            # Парсим исходный код с Tree-sitter
            doc = create_document(text, self.name)
            
            # Создаем редактор для range-based изменений
            editor = RangeEditor(text)
            
            # Применяем оптимизации
            self.apply_tree_sitter_optimizations(doc, editor, meta)
            
            # Применяем все изменения
            result_text, edit_stats = editor.apply_edits()
            
            # Объединяем статистики
            meta.update(edit_stats)
            
        except TreeSitterError as e:
            # Fallback при ошибках парсинга
            meta["tree_sitter_error"] = str(e)
            return self._fallback_process(text, group_size, mixed)
        
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

    def apply_tree_sitter_optimizations(
        self, 
        doc: TreeSitterDocument, 
        editor: RangeEditor, 
        meta: Dict[str, Any]
    ) -> None:
        """
        Применяет оптимизации используя Tree-sitter документ.
        Базовая реализация - наследники могут переопределить.
        """
        if self.cfg.strip_function_bodies:
            self.strip_function_bodies_ts(doc, editor, meta)
        
        # Обработка комментариев
        self.process_comments_ts(doc, editor, meta)
        
        # Обработка импортов
        self.process_imports_ts(doc, editor, meta)
        
        # Другие оптимизации можно добавить здесь
        # if self.cfg.public_api_only:
        #     self.filter_public_api_ts(doc, editor, meta)

    def get_comment_style(self) -> Tuple[str, tuple[str, str]]:
        """
        Возвращает стиль комментариев для языка (однострочный, многострочный).
        Должен быть переопределен наследниками.
        """
        return "//", ("/*", "*/")

    def strip_function_bodies_ts(
        self, 
        doc: TreeSitterDocument, 
        editor: RangeEditor, 
        meta: Dict[str, Any]
    ) -> None:
        """
        Удаляет тела функций используя Tree-sitter.
        Базовая реализация для всех языков.
        """
        cfg = self.cfg.strip_function_bodies
        if not cfg:
            return
        
        # Получаем генератор плейсхолдеров
        comment_style = self.get_comment_style()
        placeholder_gen = PlaceholderGenerator(comment_style)
        
        # Ищем функции для обработки
        functions = doc.query("functions")
        processed_ranges = set()  # Отслеживаем уже обработанные диапазоны
        
        for node, capture_name in functions:
            if capture_name == "function_body":
                # Получаем информацию о функции
                start_byte, end_byte = doc.get_node_range(node)
                
                # Пропускаем если этот диапазон уже обработан
                range_key = (start_byte, end_byte)
                if range_key in processed_ranges:
                    continue
                processed_ranges.add(range_key)
                
                function_text = doc.get_node_text(node)
                start_line, end_line = doc.get_line_range(node)
                lines_count = end_line - start_line + 1
                
                # Проверяем условия удаления
                should_strip = self._should_strip_function_body(cfg, function_text, lines_count)
                
                if should_strip:
                    # Создаем плейсхолдер
                    placeholder = placeholder_gen.create_function_placeholder(
                        name="function",
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
    
    def process_comments_ts(
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
        processed_ranges = set()
        
        for node, capture_name in comments:
            start_byte, end_byte = doc.get_node_range(node)
            range_key = (start_byte, end_byte)
            
            if range_key in processed_ranges:
                continue
            processed_ranges.add(range_key)
            
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
    
    def process_imports_ts(
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
        
        processed_ranges = set()
        
        if config.policy == "external_only":
            # Удаляем локальные импорты, оставляем внешние
            self._process_external_only(
                grouped["local"], editor, placeholder_gen, meta, processed_ranges
            )
        
        elif config.policy == "summarize_long":
            # Суммаризируем длинные списки импортов
            if analyzer.should_summarize(imports, config.max_items_before_summary):
                self._process_summarize_long(
                    grouped, analyzer, editor, placeholder_gen, meta, processed_ranges
                )
    
    def _process_external_only(
        self,
        local_imports: List,
        editor: RangeEditor,
        placeholder_gen: PlaceholderGenerator,
        meta: Dict[str, Any],
        processed_ranges: set
    ) -> None:
        """Удаляет локальные импорты, оставляя только внешние."""

        if not local_imports:
            return
        
        for imp in local_imports:
            start_byte, end_byte = imp.start_byte, imp.end_byte
            range_key = (start_byte, end_byte)
            
            if range_key in processed_ranges:
                continue
            processed_ranges.add(range_key)
            
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
        processed_ranges: set
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
                
                range_key = (start_byte, end_byte)
                if range_key in processed_ranges:
                    continue
                processed_ranges.add(range_key)
                
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
    
    def _fallback_process(self, text: str, group_size: int, mixed: bool) -> Tuple[str, Dict[str, Any]]:
        """
        Fallback обработка без Tree-sitter.
        Возвращает исходный текст с минимальными метаданными.
        """
        meta = self._init_meta()
        meta.update({
            "_group_size": group_size,
            "_group_mixed": mixed,
            "_adapter": self.name,
            "_fallback_mode": True,
        })
        return text, meta
    
    @abstractmethod 
    def parse_code(self, text: str) -> "CodeDocument":
        """
        DEPRECATED: Используется только для совместимости.
        Новые адаптеры должны переопределять apply_tree_sitter_optimizations.
        """
        pass

    def apply_optimizations(self, parsed: "CodeDocument", meta: Dict[str, Any]) -> "CodeDocument":
        """
        Применяет все конфигурированные оптимизации к распарсенному коду.
        """
        if self.cfg.public_api_only:
            parsed = self.filter_public_api(parsed, meta)
        
        if self.cfg.strip_function_bodies:
            parsed = self.strip_function_bodies(parsed, meta)
        
        parsed = self.process_comments(parsed, meta)
        parsed = self.process_imports(parsed, meta)
        parsed = self.process_literals(parsed, meta)
        parsed = self.process_fields(parsed, meta)
        
        if self.cfg.budget:
            parsed = self.apply_budget(parsed, meta)
        
        return parsed

    def generate_output(self, optimized: "CodeDocument", meta: Dict[str, Any]) -> str:
        """
        Генерирует финальный текст из оптимизированного представления.
        Вставляет плейсхолдеры для удаленных частей.
        """
        return optimized.to_text(self.cfg.placeholders, meta)

    # ---- Методы оптимизации (базовые реализации) ----
    
    def filter_public_api(self, parsed: "CodeDocument", meta: Dict[str, Any]) -> "CodeDocument":
        """Фильтрует только публичный API."""
        # Базовая реализация - наследники должны переопределить
        return parsed

    def strip_function_bodies(self, parsed: "CodeDocument", meta: Dict[str, Any]) -> "CodeDocument":
        """Удаляет тела функций согласно конфигурации."""
        cfg = self.cfg.strip_function_bodies
        if not cfg:
            return parsed
        
        # Логика удаления тел функций
        # Наследники должны реализовать специфичную логику
        return parsed

    def process_comments(self, parsed: "CodeDocument", meta: Dict[str, Any]) -> "CodeDocument":
        """Обрабатывает комментарии согласно политике."""
        policy = self.cfg.comment_policy
        if isinstance(policy, str) and policy == "keep_all":
            return parsed
        
        # Базовая логика обработки комментариев
        return parsed

    def process_imports(self, parsed: "CodeDocument", meta: Dict[str, Any]) -> "CodeDocument":
        """Обрабатывает импорты согласно конфигурации."""
        cfg = self.cfg.import_config
        if cfg.policy == "keep_all":
            return parsed
        
        # Логика обработки импортов
        return parsed

    def process_literals(self, parsed: "CodeDocument", meta: Dict[str, Any]) -> "CodeDocument":
        """Обрабатывает литералы данных."""
        cfg = self.cfg.literal_config
        # Логика усечения/схлопывания литералов
        return parsed

    def process_fields(self, parsed: "CodeDocument", meta: Dict[str, Any]) -> "CodeDocument":
        """Обрабатывает поля/свойства."""
        cfg = self.cfg.field_config
        # Логика обработки полей
        return parsed

    def apply_budget(self, parsed: "CodeDocument", meta: Dict[str, Any]) -> "CodeDocument":
        """Применяет бюджетное ограничение токенов."""
        budget_cfg = self.cfg.budget
        if not budget_cfg or not budget_cfg.max_tokens_per_file:
            return parsed
        
        # Логика бюджетирования
        return parsed

    # ---- Утилиты для плейсхолдеров ----
    
    def create_placeholder(
        self,
        kind: str,
        name: str = "",
        lines_removed: int = 0,
        bytes_removed: int = 0,
        template_override: Optional[str] = None
    ) -> str:
        """
        Создает плейсхолдер для удаленного кода.
        
        Args:
            kind: тип удаленного элемента (function, method, class, import, etc.)
            name: имя элемента
            lines_removed: количество удаленных строк
            bytes_removed: количество удаленных байт
            template_override: переопределение шаблона
        """
        if self.cfg.placeholders.mode == "none":
            return ""
        
        template = template_override or self.cfg.placeholders.template
        
        # Подстановка переменных
        placeholder = template.format(
            kind=kind,
            name=name,
            lines=lines_removed,
            bytes=bytes_removed,
        )
        
        return placeholder


# ---- Промежуточное представление кода ----

class CodeElement(ABC):
    """Базовый класс для элементов кода."""
    
    def __init__(self, start_line: int, end_line: int, text: str):
        self.start_line = start_line
        self.end_line = end_line
        self.original_text = text
        self.removed = False
        self.placeholder: Optional[str] = None

    @property
    def line_count(self) -> int:
        return self.end_line - self.start_line + 1

    @property
    def byte_count(self) -> int:
        return len(self.original_text.encode('utf-8'))


class ImportElement(CodeElement):
    """Элемент импорта."""
    
    def __init__(self, start_line: int, end_line: int, text: str, 
                 module_name: str, is_external: bool = False):
        super().__init__(start_line, end_line, text)
        self.module_name = module_name
        self.is_external = is_external


class FunctionElement(CodeElement):
    """Элемент функции/метода."""
    
    def __init__(self, start_line: int, end_line: int, text: str,
                 name: str, is_public: bool = True, signature: str = ""):
        super().__init__(start_line, end_line, text)
        self.name = name
        self.is_public = is_public
        self.signature = signature
        self.body_removed = False


class ClassElement(CodeElement):
    """Элемент класса/структуры."""
    
    def __init__(self, start_line: int, end_line: int, text: str,
                 name: str, is_public: bool = True):
        super().__init__(start_line, end_line, text)
        self.name = name
        self.is_public = is_public
        self.methods: List[FunctionElement] = []
        self.fields: List[CodeElement] = []


class CommentElement(CodeElement):
    """Элемент комментария."""
    
    def __init__(self, start_line: int, end_line: int, text: str,
                 is_doc: bool = False):
        super().__init__(start_line, end_line, text)
        self.is_doc = is_doc


class LiteralElement(CodeElement):
    """Элемент литерала данных."""
    
    def __init__(self, start_line: int, end_line: int, text: str,
                 literal_type: str = "unknown"):
        super().__init__(start_line, end_line, text)
        self.literal_type = literal_type  # string, array, object, etc.


class CodeDocument:
    """
    Промежуточное представление документа с кодом.
    Содержит разобранные элементы кода для обработки.
    """
    
    def __init__(self, original_lines: List[str]):
        self.original_lines = original_lines
        self.imports: List[ImportElement] = []
        self.functions: List[FunctionElement] = []
        self.classes: List[ClassElement] = []
        self.comments: List[CommentElement] = []
        self.literals: List[LiteralElement] = []
        self.other_elements: List[CodeElement] = []

    def to_text(self, placeholder_cfg: PlaceholderConfig, meta: Dict[str, Any]) -> str:
        """
        Генерирует финальный текст с учетом удаленных элементов и плейсхолдеров.
        """
        if placeholder_cfg.mode == "none":
            # Простое удаление без плейсхолдеров
            return self._generate_simple_output()
        
        return self._generate_output_with_placeholders(placeholder_cfg, meta)

    def _generate_simple_output(self) -> str:
        """Генерирует вывод без плейсхолдеров."""
        # Собираем все элементы, которые не помечены как удаленные
        result_lines = []
        for line in self.original_lines:
            # Упрощенная логика - в реальной реализации нужна более сложная обработка
            result_lines.append(line)
        
        return "\n".join(result_lines)

    def _generate_output_with_placeholders(
        self, 
        placeholder_cfg: PlaceholderConfig, 
        meta: Dict[str, Any]
    ) -> str:
        """Генерирует вывод с плейсхолдерами."""
        # Более сложная логика с учетом плейсхолдеров
        # В реальной реализации нужно пройти по всем элементам,
        # заменить удаленные на плейсхолдеры
        result_lines = []
        placeholders_count = 0
        
        for line in self.original_lines:
            # Упрощенная логика - реальная реализация будет зависеть от языка
            result_lines.append(line)
        
        meta["code.placeholders"] = placeholders_count
        return "\n".join(result_lines)
