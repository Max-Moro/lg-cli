"""
Literal optimization.
Processes and trims literal data (strings, arrays, objects) with simplified logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast, List

from ..context import ProcessingContext
from ..tree_sitter_support import Node


@dataclass
class LiteralInfo:
    """Информация о структуре литерала для умного тримминга."""
    type: str  # "string", "array", "object", "set", "tuple"
    opening: str  # "[", "{", "(", '"""', etc.
    closing: str  # "]", "}", ")", '"""', etc.
    content: str  # содержимое без границ
    is_multiline: bool
    language: str  # "python", "typescript", etc.


@dataclass
class CommentPlacement:
    """Информация о размещении комментария."""
    position: int
    text: str


class LiteralOptimizer:
    """Handles literal data processing optimization with simplified logic."""

    def __init__(self, adapter):
        """Initialize with parent adapter for language-specific checks."""
        from ..code_base import CodeAdapter
        self.adapter = cast(CodeAdapter, adapter)

    def apply(self, context: ProcessingContext) -> None:
        """Apply literal processing based on configuration."""
        max_tokens = self.adapter.cfg.literals.max_tokens
        if max_tokens is None:
            return  # Оптимизация отключена

        # Находим все литералы в коде
        literals = context.doc.query("literals")

        for node, capture_name in literals:
            literal_text = context.doc.get_node_text(node)
            token_count = context.tokenizer.count_text(literal_text)

            if token_count > max_tokens:
                self._trim_literal(context, node, capture_name, literal_text, max_tokens)

    def _trim_literal(
        self,
        context: ProcessingContext,
        node: Node,
        capture_name: str,
        literal_text: str,
        max_tokens: int
    ) -> None:
        """Умно урезает литерал с сохранением валидности AST."""
        # Анализируем структуру литерала
        literal_info = self._analyze_literal_structure(literal_text, capture_name, self.adapter.name)

        # Умно урезаем содержимое
        trimmed_content = self._smart_trim_content(context, literal_info, max_tokens, node)

        # Формируем корректную замену
        replacement = f"{literal_info.opening}{trimmed_content}{literal_info.closing}"

        # Вычисляем экономию токенов
        original_tokens = context.tokenizer.count_text(literal_text)
        saved_tokens = original_tokens - context.tokenizer.count_text(replacement)

        # Применяем замену литерала
        start_byte, end_byte = context.doc.get_node_range(node)
        context.editor.add_replacement(
            start_byte, end_byte, replacement,
            edit_type="literal_trimmed"
        )

        # Добавляем комментарий
        self._add_comment(context, literal_info, saved_tokens, end_byte)

        # Обновляем метрики
        context.metrics.mark_element_removed("literal")
        context.metrics.add_bytes_saved(len(literal_text.encode('utf-8')) - len(replacement.encode('utf-8')))

    def _analyze_literal_structure(self, literal_text: str, capture_name: str, language: str) -> LiteralInfo:
        """Анализирует структуру литерала для умного тримминга."""
        stripped = literal_text.strip()
        is_multiline = '\n' in literal_text

        # Определяем тип и границы литерала
        if capture_name == "string":
            return self._analyze_string_literal(stripped, is_multiline, language)
        elif capture_name == "set":
            content = self._extract_content(literal_text, "{", "}")
            return LiteralInfo("set", "{", "}", content, is_multiline, language)
        elif capture_name in ("array", "list"):
            return self._analyze_array_literal(stripped, literal_text, is_multiline, language)
        elif capture_name in ("object", "dictionary"):
            content = self._extract_content(literal_text, "{", "}")
            return LiteralInfo("object", "{", "}", content, is_multiline, language)
        else:
            # Универсальный анализ по символам
            return self._analyze_by_syntax(stripped, literal_text, is_multiline, language)

    def _analyze_string_literal(self, stripped: str, is_multiline: bool, language: str) -> LiteralInfo:
        """Анализирует строковые литералы."""
        if stripped.startswith('"""') or stripped.startswith("'''"):
            # Python triple quotes
            quote = stripped[:3]
            content = self._extract_content(stripped, quote, quote)
            return LiteralInfo("string", quote, quote, content, is_multiline, language)
        elif stripped.startswith('`'):
            # Template strings (TypeScript)
            content = self._extract_content(stripped, "`", "`")
            return LiteralInfo("string", "`", "`", content, is_multiline, language)
        elif stripped.startswith('"'):
            content = self._extract_content(stripped, '"', '"')
            return LiteralInfo("string", '"', '"', content, is_multiline, language)
        elif stripped.startswith("'"):
            content = self._extract_content(stripped, "'", "'")
            return LiteralInfo("string", "'", "'", content, is_multiline, language)
        else:
            # Fallback
            return LiteralInfo("string", '"', '"', stripped, is_multiline, language)

    def _analyze_array_literal(self, stripped: str, literal_text: str, is_multiline: bool, language: str) -> LiteralInfo:
        """Анализирует массивы/списки."""
        if stripped.startswith('[') and stripped.endswith(']'):
            content = self._extract_content(literal_text, "[", "]")
            return LiteralInfo("array", "[", "]", content, is_multiline, language)
        elif stripped.startswith('(') and stripped.endswith(')'):
            # Tuple в Python
            content = self._extract_content(literal_text, "(", ")")
            return LiteralInfo("tuple", "(", ")", content, is_multiline, language)
        elif stripped.startswith('{') and stripped.endswith('}'):
            content = self._extract_content(literal_text, "{", "}")
            return LiteralInfo("object", "{", "}", content, is_multiline, language)
        else:
            # Fallback к массиву
            content = self._extract_content(literal_text, "[", "]")
            return LiteralInfo("array", "[", "]", content, is_multiline, language)

    def _analyze_by_syntax(self, stripped: str, literal_text: str, is_multiline: bool, language: str) -> LiteralInfo:
        """Универсальный анализ по синтаксису."""
        if stripped.startswith('[') and stripped.endswith(']'):
            content = self._extract_content(literal_text, "[", "]")
            return LiteralInfo("array", "[", "]", content, is_multiline, language)
        elif stripped.startswith('{') and stripped.endswith('}'):
            content = self._extract_content(literal_text, "{", "}")
            return LiteralInfo("object", "{", "}", content, is_multiline, language)
        elif stripped.startswith('(') and stripped.endswith(')'):
            content = self._extract_content(literal_text, "(", ")")
            return LiteralInfo("tuple", "(", ")", content, is_multiline, language)
        else:
            return LiteralInfo("literal", "", "", stripped, is_multiline, language)

    def _extract_content(self, literal_text: str, opening: str, closing: str) -> str:
        """Извлекает содержимое литерала без открывающих/закрывающих символов."""
        stripped = literal_text.strip()

        if opening and closing and stripped.startswith(opening) and stripped.endswith(closing):
            return stripped[len(opening):-len(closing)]

        return stripped

    def _smart_trim_content(self, context: ProcessingContext, literal_info: LiteralInfo, max_tokens: int, node: Node) -> str:
        """Умно урезает содержимое с учетом структуры литерала."""
        if literal_info.type == "string":
            return self._trim_string_content(context, literal_info, max_tokens)
        elif literal_info.type in ("array", "tuple", "set"):
            return self._trim_array_content(context, literal_info, max_tokens, node)
        elif literal_info.type == "object":
            return self._trim_object_content(context, literal_info, max_tokens, node)
        else:
            return self._trim_simple_content(context, literal_info.content, max_tokens)

    def _trim_string_content(self, context: ProcessingContext, literal_info: LiteralInfo, max_tokens: int) -> str:
        """Урезает строковые литералы."""
        content = literal_info.content

        # Резервируем место для границ и символа урезания
        overhead_text = f"{literal_info.opening}…{literal_info.closing}"
        overhead_tokens = context.tokenizer.count_text(overhead_text)
        content_budget = max(1, max_tokens - overhead_tokens)

        # Урезаем содержимое до бюджета
        trimmed = self._trim_simple_content(context, content, content_budget)
        return f"{trimmed}…"

    def _trim_array_content(self, context: ProcessingContext, literal_info: LiteralInfo, max_tokens: int, node: Node) -> str:
        """Урезает массивы/списки с добавлением корректного элемента-заглушки."""
        content = literal_info.content.strip()

        # Резервируем место для границ и заглушки
        placeholder_element = '"…"'
        overhead = f"{literal_info.opening}{placeholder_element},{literal_info.closing}"
        overhead_tokens = context.tokenizer.count_text(overhead)
        content_budget = max(10, max_tokens - overhead_tokens)

        # Парсим элементы
        elements = self._parse_elements(content)

        # Находим элементы, которые помещаются в бюджет
        included_elements = self._select_elements_within_budget(context, elements, content_budget)

        if not included_elements:
            # Если не помещается ни один элемент, берем первый частично
            first_element = elements[0] if elements else '""'
            trimmed_element = self._trim_simple_content(context, first_element, content_budget - 10)
            return f"{trimmed_element}, \"…\""

        # Формируем результат
        if literal_info.is_multiline:
            # Определяем правильные отступы из контекста
            element_indent, base_indent = self._get_base_indentations(context, node)
            # Добавляем отступы к каждому элементу
            indented_elements = [f"{element_indent}{element}" for element in included_elements]
            joined = f",\n".join(indented_elements)
            return f"\n{joined},\n{element_indent}\"…\",\n{base_indent}"
        else:
            joined = ", ".join(included_elements)
            return f"{joined}, \"…\""

    def _trim_object_content(self, context: ProcessingContext, literal_info: LiteralInfo, max_tokens: int, node: Node) -> str:
        """Урезает объекты/словари с добавлением корректной заглушки."""
        content = literal_info.content.strip()

        # Резервируем место для границ и заглушки
        placeholder_pair = '"…": "…"'
        overhead = f"{literal_info.opening}{placeholder_pair},{literal_info.closing}"
        overhead_tokens = context.tokenizer.count_text(overhead)
        content_budget = max(10, max_tokens - overhead_tokens)

        # Парсим пары ключ-значение
        pairs = self._parse_elements(content)

        # Находим пары, которые помещаются в бюджет
        included_pairs = self._select_elements_within_budget(context, pairs, content_budget)

        if not included_pairs:
            # Если не помещается ни одна пара, используем только заглушку
            if literal_info.is_multiline:
                # Определяем правильные отступы из контекста
                element_indent, base_indent = self._get_base_indentations(context, node)
                return f"\n{element_indent}\"…\": \"…\",\n{base_indent}"
            else:
                return '"…": "…"'

        # Формируем результат
        if literal_info.is_multiline:
            # Определяем правильные отступы из контекста
            element_indent, base_indent = self._get_base_indentations(context, node)
            # Добавляем отступы к каждому элементу
            indented_pairs = [f"{element_indent}{pair}" for pair in included_pairs]
            joined = f",\n".join(indented_pairs)
            return f"\n{joined},\n{element_indent}\"…\": \"…\",\n{base_indent}"
        else:
            joined = ", ".join(included_pairs)
            return f"{joined}, \"…\": \"…\""

    def _select_elements_within_budget(self, context: ProcessingContext, elements: List[str], budget: int) -> List[str]:
        """Выбирает элементы, которые помещаются в бюджет токенов."""
        included_elements = []
        current_tokens = 0

        for element in elements:
            element_tokens = context.tokenizer.count_text(element + ",")
            if current_tokens + element_tokens <= budget:
                included_elements.append(element)
                current_tokens += element_tokens
            else:
                break

        return included_elements

    def _trim_simple_content(self, context: ProcessingContext, content: str, token_budget: int) -> str:
        """Простое урезание содержимого по токенам."""
        if not content:
            return ""

        current_tokens = context.tokenizer.count_text(content)
        if current_tokens <= token_budget:
            return content

        # Простое урезание по символам (более эффективно чем бинарный поиск)
        ratio = token_budget / current_tokens
        target_length = int(len(content) * ratio)

        # Урезаем до целевой длины, но не меньше 1 символа
        target_length = max(1, target_length)
        trimmed = content[:target_length].rstrip()

        return trimmed

    def _parse_elements(self, content: str) -> List[str]:
        """
        Универсальный парсер элементов с учетом вложенности.
        Работает как для массивов, так и для объектов.
        """
        if not content.strip():
            return []

        elements = []
        current_element = ""
        depth = 0
        in_string = False
        string_char = None

        for i, char in enumerate(content):
            # Обработка строк
            if char in ('"', "'", "`") and not in_string:
                in_string = True
                string_char = char
                current_element += char
            elif char == string_char and in_string:
                # Проверяем экранирование
                if i > 0 and content[i-1] != '\\':
                    in_string = False
                    string_char = None
                current_element += char
            elif in_string:
                current_element += char
            # Обработка вложенности вне строк
            elif char in ('(', '[', '{'):
                depth += 1
                current_element += char
            elif char in (')', ']', '}'):
                depth -= 1
                current_element += char
            elif char == ',' and depth == 0:
                # Найден разделитель на верхнем уровне
                if current_element.strip():
                    elements.append(current_element.strip())
                current_element = ""
            else:
                current_element += char

        # Добавляем последний элемент
        if current_element.strip():
            elements.append(current_element.strip())

        return elements

    def _get_base_indentations(self, context: ProcessingContext, node: Node) -> tuple[str, str]:
        """
        Определяет правильные отступы для элементов и базовый отступ литерала.
        
        Returns:
            Tuple of (element_indent, base_indent)
        """
        # Получаем полный текст литерала из исходного файла
        start_byte, end_byte = context.doc.get_node_range(node)
        full_literal_text = context.raw_text[start_byte:end_byte]
        
        # Определяем базовый отступ (отступ строки, где начинается литерал)
        start_line = context.doc.get_line_number_for_byte(node.start_byte)
        lines = context.raw_text.split('\n')
        base_indent = ""
        if start_line < len(lines):
            line = lines[start_line]
            for char in line:
                if char in ' \t':
                    base_indent += char
                else:
                    break
        
        # Определяем отступ элементов внутри литерала
        element_indent = self._detect_element_indentation_from_full_text(full_literal_text, base_indent)
        
        return element_indent, base_indent

    def _detect_element_indentation_from_full_text(self, full_literal_text: str, base_indent: str) -> str:
        """
        Определяет отступ элементов внутри литерала из полного текста литерала.
        """
        lines = full_literal_text.split('\n')
        if len(lines) < 2:
            return "    "  # 4 пробела по умолчанию

        # Ищем первую строку с содержимым элемента (не пустую, не закрывающую скобку)
        for line in lines[1:]:
            stripped = line.strip()
            if stripped and not stripped.startswith(('}', ']', ')')):
                # Извлекаем leading whitespace
                element_indent = ""
                for char in line:
                    if char in ' \t':
                        element_indent += char
                    else:
                        break
                # Если нашли отступ, используем его
                if element_indent:
                    return element_indent

        # Fallback - добавляем стандартный отступ к базовому
        return base_indent + "    "

    def _add_comment(self, context: ProcessingContext, literal_info: LiteralInfo, saved_tokens: int, end_byte: int) -> None:
        """Добавляет комментарий в правильное место."""
        comment_style = self.adapter.get_comment_style()
        single_comment = comment_style[0]

        comment_text = f"literal {literal_info.type} (−{saved_tokens} tokens)"

        # Ищем лучшее место для размещения комментария
        placement = self._find_comment_placement(context, end_byte, comment_text, single_comment)

        context.editor.add_replacement(
            placement.position, placement.position, placement.text,
            edit_type="literal_comment"
        )

    def _find_comment_placement(self, context: ProcessingContext, end_byte: int, comment_text: str, single_comment: str) -> CommentPlacement:
        """Находит лучшее место для размещения комментария."""
        text_after = context.raw_text[end_byte:]
        line_after = text_after.split('\n')[0]

        # 1. Ищем закрывающие скобки/кавычки сразу после литерала
        bracket_pos = self._find_closing_brackets_after_literal(line_after)
        if bracket_pos is not None:
            insertion_pos = end_byte + bracket_pos + 1
            text_after_bracket = line_after[bracket_pos + 1:].strip()
            if text_after_bracket and not text_after_bracket.startswith((';', ',', ')')):
                # Есть код после - используем блочный комментарий
                block_open, block_close = self.adapter.get_comment_style()[1]
                comment = f" {block_open} {comment_text} {block_close}"
            else:
                # Нет кода - используем однострочный
                comment = f" {single_comment} {comment_text}"
            return CommentPlacement(insertion_pos, comment)

        # 2. Ищем точку с запятой
        semicolon_pos = line_after.find(';')
        if semicolon_pos != -1:
            insertion_pos = end_byte + semicolon_pos + 1
            text_after_semicolon = line_after[semicolon_pos + 1:].strip()
            if text_after_semicolon:
                # Есть код после - используем блочный комментарий
                block_open, block_close = self.adapter.get_comment_style()[1]
                comment = f" {block_open} {comment_text} {block_close}"
            else:
                # Нет кода - используем однострочный
                comment = f" {single_comment} {comment_text}"
            return CommentPlacement(insertion_pos, comment)

        # 3. Ищем запятую (для массивов, объектов)
        comma_pos = line_after.find(',')
        if comma_pos != -1:
            insertion_pos = end_byte + comma_pos + 1
            text_after_comma = line_after[comma_pos + 1:].strip()
            if text_after_comma and not text_after_comma.startswith((']', '}', ')')):
                # Есть код после - используем блочный комментарий
                block_open, block_close = self.adapter.get_comment_style()[1]
                comment = f" {block_open} {comment_text} {block_close}"
            else:
                # Нет кода - используем однострочный
                comment = f" {single_comment} {comment_text}"
            return CommentPlacement(insertion_pos, comment)

        # 4. Если ничего не найдено - размещаем сразу после литерала
        if line_after.strip():
            # Есть код после - используем блочный комментарий
            block_open, block_close = self.adapter.get_comment_style()[1]
            comment = f" {block_open} {comment_text} {block_close}"
        else:
            # Нет кода - используем однострочный
            comment = f" {single_comment} {comment_text}"

        return CommentPlacement(end_byte, comment)

    def _find_closing_brackets_after_literal(self, line_after: str) -> int | None:
        """Ищет закрывающие скобки сразу после литерала."""
        # Ищем закрывающие скобки в начале строки (после литерала)
        for i, char in enumerate(line_after):
            if char in '])}':
                return i
            elif char not in ' \t':  # Прерываем на первом не-пробельном символе
                break
        return None
