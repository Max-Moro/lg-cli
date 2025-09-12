"""
Literal optimization.
Processes and trims literal data (strings, arrays, objects).
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
    element_separator: str = ","  # разделитель элементов


@dataclass
class LiteralContext:
    """Контекст размещения литерала для правильного форматирования."""
    line_before: str  # текст до литерала на той же строке
    line_after: str   # текст после литерала на той же строке  
    has_semicolon: bool  # есть ли ; после литерала
    semicolon_pos: int = None  # позиция ; в тексте
    is_inline: bool = False  # есть ли значимый код после литерала
    base_indent: str = ""  # базовая табуляция для многострочных литералов
    immediate_after: str = ""  # текст сразу после литерала (до первого пробела)
    has_immediate_semicolon: bool = False  # есть ли ; сразу после литерала (без пробелов)


class LiteralOptimizer:
    """Handles literal data processing optimization."""
    
    def __init__(self, adapter):
        """
        Initialize with parent adapter for language-specific checks.
        
        Args:
            adapter: Parent CodeAdapter instance for language-specific methods
        """
        from ..code_base import CodeAdapter
        self.adapter = cast(CodeAdapter, adapter)
    
    def apply(self, context: ProcessingContext) -> None:
        """
        Apply literal processing based on configuration.
        
        Args:
            context: Processing context with document and editor
        """
        # Проверяем, настроена ли оптимизация литералов
        max_tokens = self.adapter.cfg.literals.max_tokens
        if max_tokens is None:
            return  # Оптимизация отключена
        
        # Находим все литералы в коде
        literals = context.doc.query("literals")
        
        for node, capture_name in literals:
            literal_text = context.doc.get_node_text(node)
            
            # Оцениваем размер литерала в токенах
            token_count = context.tokenizer.count_text(literal_text)
            
            if token_count > max_tokens:
                # Литерал превышает лимит - нужно урезать
                self._trim_literal(context, node, capture_name, literal_text, max_tokens)
    
    def _analyze_literal_context(self, context: ProcessingContext, node: Node) -> LiteralContext:
        """Анализирует контекст размещения литерала для правильного форматирования."""
        start_byte, end_byte = context.doc.get_node_range(node)
        
        # Определяем, находится ли литерал на отдельной строке или в середине строки
        text_before = context.raw_text[:start_byte]
        text_after = context.raw_text[end_byte:]
        
        # Ищем ближайший символ перевода строки до и после
        last_newline_before = text_before.rfind('\n')
        next_newline_after = text_after.find('\n')
        
        if next_newline_after == -1:
            next_newline_after = len(text_after)
        
        # Текст на той же строке до и после литерала
        line_before = text_before[last_newline_before + 1:] if last_newline_before != -1 else text_before
        line_after = text_after[:next_newline_after]
        
        # Проверяем, есть ли значимый код после литерала на той же строке
        significant_after = line_after.strip()
        
        # Анализируем что идет сразу после литерала
        immediate_after = ""
        for i, char in enumerate(line_after):
            if char in ' \t':
                continue  # пропускаем пробелы
            else:
                # Берем текст от первого непробельного символа до следующего пробела или конца
                remaining = line_after[i:]
                space_idx = None
                for j, c in enumerate(remaining):
                    if c in ' \t\n':
                        space_idx = j
                        break
                if space_idx is not None:
                    immediate_after = remaining[:space_idx]
                else:
                    immediate_after = remaining
                break
        
        # Проверяем есть ли ; сразу после литерала (без пробелов)
        has_immediate_semicolon = immediate_after.startswith(';')
        
        # Для языков с ; ищем его позицию (может быть не сразу после литерала)
        has_semicolon = ';' in significant_after
        semicolon_pos = None
        if has_semicolon:
            semicolon_idx = line_after.find(';')
            if semicolon_idx != -1:
                semicolon_pos = end_byte + semicolon_idx
        
        # Определяем базовую табуляцию из контекста размещения литерала
        base_indent = self._detect_base_indentation(line_before)
        
        return LiteralContext(
            line_before=line_before,
            line_after=line_after,
            has_semicolon=has_semicolon,
            semicolon_pos=semicolon_pos,
            is_inline=bool(significant_after),
            base_indent=base_indent,
            immediate_after=immediate_after,
            has_immediate_semicolon=has_immediate_semicolon
        )

    def _detect_base_indentation(self, line_before: str) -> str:
        """Определяет базовый отступ литерала из контекста его размещения."""
        # Извлекаем отступ из строки, где начинается литерал
        indent = ""
        for char in line_before:
            if char in ' \t':
                indent += char
            else:
                break
        return indent

    def _detect_element_indentation(self, literal_text: str, base_indent: str) -> str:
        """Определяет отступ элементов внутри многострочного литерала."""
        lines = literal_text.split('\n')
        if len(lines) < 2:
            return base_indent + "    "  # Базовый отступ + 4 пробела по умолчанию
        
        # Ищем первую непустую строку с содержимым элемента
        for line in lines[1:]:
            stripped = line.strip()
            if stripped and not stripped.startswith(('"', "'", "`", "}", "]", ")")):
                # Извлекаем leading whitespace
                element_indent = ""
                for char in line:
                    if char in ' \t':
                        element_indent += char
                    else:
                        break
                return element_indent if element_indent else base_indent + "    "
        
        # Если не нашли элемент, используем базовый отступ + 4 пробела
        return base_indent + "    "

    def _trim_literal(
        self, 
        context: ProcessingContext, 
        node: Node, 
        capture_name: str, 
        literal_text: str, 
        max_tokens: int
    ) -> None:
        """
        Умно урезает литерал с сохранением валидности AST.
        
        Args:
            context: Контекст обработки
            node: Узел литерала
            capture_name: Тип захвата (string, array, object)
            literal_text: Исходный текст литерала
            max_tokens: Максимальный размер в токенах
        """
        # Определяем язык по расширению адаптера
        language = self.adapter.name
        
        # Анализируем контекст размещения
        literal_context = self._analyze_literal_context(context, node)
        
        # Анализируем структуру литерала
        literal_info = self._analyze_literal_structure(literal_text, capture_name, language)
        
        # Определяем отступ элементов внутри литерала
        element_indent = self._detect_element_indentation(literal_text, literal_context.base_indent)
        
        # Обновляем информацию о табуляции в literal_info
        literal_info.element_separator = ", " if not literal_info.is_multiline else f",\n{element_indent}"
        
        # Умно урезаем содержимое с учетом структуры
        trimmed_content = self._smart_trim_content(context, literal_info, max_tokens, literal_context, element_indent)
        
        # Формируем корректную замену
        replacement = self._build_replacement(literal_info, trimmed_content)
        
        # Вычисляем экономию токенов
        original_tokens = context.tokenizer.count_text(literal_text)
        saved_tokens = original_tokens - context.tokenizer.count_text(replacement)
        
        # Применяем замену литерала
        start_byte, end_byte = context.doc.get_node_range(node)
        context.editor.add_replacement(
            start_byte, end_byte, replacement,
            edit_type="literal_trimmed"
        )
        
        # Добавляем комментарий в правильное место
        self._add_smart_comment(context, literal_context, literal_info, saved_tokens, end_byte)
        
        # Обновляем метрики
        context.metrics.mark_element_removed("literal")
        context.metrics.add_bytes_saved(len(literal_text.encode('utf-8')) - len(replacement.encode('utf-8')))

    def _add_smart_comment(
        self, 
        context: ProcessingContext, 
        literal_context: LiteralContext, 
        literal_info: LiteralInfo, 
        saved_tokens: int, 
        original_end_byte: int
    ) -> None:
        """Добавляет комментарий в правильное место с учетом контекста."""
        comment_style = self.adapter.get_comment_style()
        single_comment = comment_style[0]
        block_open, block_close = comment_style[1]
        
        comment_text = f"literal {literal_info.type} (−{saved_tokens} tokens)"
        
        # Логика выбора места и типа комментария
        if literal_context.has_immediate_semicolon and literal_context.semicolon_pos:
            # `;` сразу после литерала - проверяем есть ли ещё код после `;`
            semicolon_end = literal_context.semicolon_pos + 1
            text_after_semicolon = context.raw_text[semicolon_end:].split('\n')[0].strip()
            
            if not text_after_semicolon:
                # Нет кода после `;` на той же строке - можем использовать однострочный комментарий
                insertion_pos = literal_context.semicolon_pos + 1
                final_comment = f" {single_comment} {comment_text}"
            else:
                # Есть код после `;` - используем блочный комментарий сразу после литерала
                insertion_pos = original_end_byte
                final_comment = f" {block_open} {comment_text} {block_close}"
        elif literal_context.is_inline:
            # Есть значимый код после литерала на той же строке - используем блочный комментарий
            # чтобы не "закомментировать" остальной код
            insertion_pos = original_end_byte
            final_comment = f" {block_open} {comment_text} {block_close}"
        else:
            # Литерал заканчивается в конце строки - можем использовать однострочный комментарий
            insertion_pos = original_end_byte
            final_comment = f" {single_comment} {comment_text}"
        
        context.editor.add_replacement(
            insertion_pos, insertion_pos, final_comment,
            edit_type="literal_comment"
        )
    
    def _analyze_literal_structure(self, literal_text: str, capture_name: str, language: str) -> LiteralInfo:
        """
        Анализирует структуру литерала для умного тримминга.
        
        Args:
            literal_text: Текст литерала
            capture_name: Тип захвата из Tree-sitter
            language: Язык программирования
            
        Returns:
            LiteralInfo с полной информацией о структуре
        """
        stripped = literal_text.strip()
        is_multiline = '\n' in literal_text
        
        if capture_name == "string":
            # Строки: обрабатываем различные виды кавычек
            if stripped.startswith('"""') or stripped.startswith("'''"):
                # Python triple quotes
                quote = stripped[:3]
                content = self._extract_content(literal_text, quote, quote)
                return LiteralInfo("string", quote, quote, content, is_multiline, language)
            elif stripped.startswith('`'):
                # Template strings (TypeScript)
                content = self._extract_content(literal_text, "`", "`")
                return LiteralInfo("string", "`", "`", content, is_multiline, language)
            elif stripped.startswith('"'):
                content = self._extract_content(literal_text, '"', '"')
                return LiteralInfo("string", '"', '"', content, is_multiline, language)
            elif stripped.startswith("'"):
                content = self._extract_content(literal_text, "'", "'")
                return LiteralInfo("string", "'", "'", content, is_multiline, language)
            else:
                # Fallback
                content = stripped
                return LiteralInfo("string", '"', '"', content, is_multiline, language)
        
        elif capture_name == "set":
            # Python set literals  
            content = self._extract_content(literal_text, "{", "}")
            return LiteralInfo("set", "{", "}", content, is_multiline, language)
        
        elif capture_name in ("array", "list"):
            # Массивы/списки - проверяем реальные символы
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
        
        elif capture_name in ("object", "dictionary"):
            # Объекты/словари
            content = self._extract_content(literal_text, "{", "}")
            return LiteralInfo("object", "{", "}", content, is_multiline, language)
        
        else:
            # Универсальный анализ по символам с улучшенной логикой
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
                content = stripped
                return LiteralInfo("literal", "", "", content, is_multiline, language)

    def _extract_content(self, literal_text: str, opening: str, closing: str) -> str:
        """
        Извлекает содержимое литерала без открывающих/закрывающих символов.
        
        Args:
            literal_text: Полный текст литерала
            opening: Открывающий символ(ы)
            closing: Закрывающий символ(ы)
            
        Returns:
            Содержимое без границ
        """
        stripped = literal_text.strip()
        
        if opening and closing:
            # Убираем открывающие и закрывающие символы
            if stripped.startswith(opening) and stripped.endswith(closing):
                content = stripped[len(opening):-len(closing)]
                return content
        
        return stripped
    
    def _smart_trim_content(self, context: ProcessingContext, literal_info: LiteralInfo, max_tokens: int, literal_context: LiteralContext, element_indent: str) -> str:
        """
        Умно урезает содержимое с учетом структуры литерала.
        
        Args:
            context: Контекст обработки
            literal_info: Информация о структуре литерала
            max_tokens: Максимальный размер в токенах
            literal_context: Контекст размещения литерала
            element_indent: Отступ для элементов внутри литерала
            
        Returns:
            Урезанное содержимое для корректной замены
        """
        if literal_info.type == "string":
            return self._trim_string_content(context, literal_info, max_tokens)
        elif literal_info.type in ("array", "tuple", "set"):
            return self._trim_array_content(context, literal_info, max_tokens, literal_context, element_indent)
        elif literal_info.type == "object":
            return self._trim_object_content(context, literal_info, max_tokens, literal_context, element_indent)
        else:
            # Fallback к простому урезанию
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
    
    def _trim_array_content(self, context: ProcessingContext, literal_info: LiteralInfo, max_tokens: int, literal_context: LiteralContext, element_indent: str) -> str:
        """Урезает массивы/списки с добавлением корректного элемента-заглушки."""
        content = literal_info.content.strip()
        
        # Резервируем место для границ, заглушки и отступов
        placeholder_element = '"…"'
        if literal_info.language == "python" and literal_info.type == "tuple":
            # Для tuple нужна запятая даже для одного элемента
            overhead = f"{literal_info.opening}{placeholder_element},{literal_info.closing}"
        else:
            overhead = f"{literal_info.opening}{placeholder_element},{literal_info.closing}"
        
        overhead_tokens = context.tokenizer.count_text(overhead)
        content_budget = max(10, max_tokens - overhead_tokens)  # минимум места для хотя бы одного элемента
        
        # Находим последний полный элемент, который помещается в бюджет
        elements = self._parse_array_elements(content)
        
        included_elements = []
        current_tokens = 0
        
        for element in elements:
            element_tokens = context.tokenizer.count_text(element + ",")
            if current_tokens + element_tokens <= content_budget:
                included_elements.append(element)
                current_tokens += element_tokens
            else:
                break
        
        if not included_elements:
            # Если не помещается ни один элемент, берем первый частично
            first_element = elements[0] if elements else '""'
            trimmed_element = self._trim_simple_content(context, first_element, content_budget - 10)
            if literal_info.is_multiline:
                return f"\n{element_indent}{trimmed_element}, \"…\",\n{literal_context.base_indent}"
            else:
                return f"{trimmed_element}, \"…\""
        
        # Формируем результат с корректным форматированием
        if literal_info.is_multiline:
            joined = f",\n{element_indent}".join(included_elements)
            return f"\n{element_indent}{joined}, \"…\",\n{literal_context.base_indent}"
        else:
            joined = ", ".join(included_elements)
            return f"{joined}, \"…\""
    
    def _trim_object_content(self, context: ProcessingContext, literal_info: LiteralInfo, max_tokens: int, literal_context: LiteralContext, element_indent: str) -> str:
        """Урезает объекты/словари с добавлением корректной заглушки."""
        content = literal_info.content.strip()
        
        # Резервируем место для границ и заглушки
        if literal_info.language == "python":
            placeholder_pair = '"…": "…"'
        else:
            placeholder_pair = '"…": "…"'
        
        overhead = f"{literal_info.opening}{placeholder_pair},{literal_info.closing}"
        overhead_tokens = context.tokenizer.count_text(overhead)
        content_budget = max(10, max_tokens - overhead_tokens)
        
        # Находим последнюю полную пару ключ-значение
        pairs = self._parse_object_pairs(content)
        
        included_pairs = []
        current_tokens = 0
        
        for pair in pairs:
            pair_tokens = context.tokenizer.count_text(pair + ",")
            if current_tokens + pair_tokens <= content_budget:
                included_pairs.append(pair)
                current_tokens += pair_tokens
            else:
                break
        
        if not included_pairs:
            # Если не помещается ни одна пара, используем только заглушку
            if literal_info.is_multiline:
                return f"\n{element_indent}\"…\": \"…\",\n{literal_context.base_indent}"
            else:
                return '"…": "…"'
        
        # Формируем результат
        if literal_info.is_multiline:
            joined = f",\n{element_indent}".join(included_pairs)
            return f"\n{element_indent}{joined},\n{element_indent}\"…\": \"…\",\n{literal_context.base_indent}"
        else:
            joined = ", ".join(included_pairs)
            return f"{joined}, \"…\": \"…\""
    
    def _trim_simple_content(self, context: ProcessingContext, content: str, token_budget: int) -> str:
        """Простое урезание содержимого по токенам."""
        if not content:
            return ""
        
        current_tokens = context.tokenizer.count_text(content)
        if current_tokens <= token_budget:
            return content
        
        # Бинарный поиск точки обрезания
        left, right = 0, len(content)
        best_end = 0
        
        while left <= right:
            mid = (left + right) // 2
            substring = content[:mid]
            tokens = context.tokenizer.count_text(substring)
            
            if tokens <= token_budget:
                best_end = mid
                left = mid + 1
            else:
                right = mid - 1
        
        return content[:best_end].rstrip()
    
    def _parse_array_elements(self, content: str) -> List[str]:
        """
        Парсит элементы массива/списка с учетом вложенности.
        Упрощенный парсер, который работает для большинства случаев.
        """
        if not content.strip():
            return []
        
        elements = []
        current_element = ""
        depth = 0
        in_string = False
        string_char = None
        i = 0
        
        while i < len(content):
            char = content[i]
            
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
            
            i += 1
        
        # Добавляем последний элемент
        if current_element.strip():
            elements.append(current_element.strip())
        
        return elements
    
    def _parse_object_pairs(self, content: str) -> List[str]:
        """
        Парсит пары ключ-значение в объекте с учетом вложенности.
        Возвращает список строк вида "key: value".
        """
        if not content.strip():
            return []
        
        pairs = []
        current_pair = ""
        depth = 0
        in_string = False
        string_char = None
        i = 0
        
        while i < len(content):
            char = content[i]
            
            # Обработка строк
            if char in ('"', "'", "`") and not in_string:
                in_string = True
                string_char = char
                current_pair += char
            elif char == string_char and in_string:
                if i > 0 and content[i-1] != '\\':
                    in_string = False
                    string_char = None
                current_pair += char
            elif in_string:
                current_pair += char
            # Обработка вложенности вне строк
            elif char in ('(', '[', '{'):
                depth += 1
                current_pair += char
            elif char in (')', ']', '}'):
                depth -= 1
                current_pair += char
            elif char == ',' and depth == 0:
                # Найден разделитель на верхнем уровне
                if current_pair.strip():
                    pairs.append(current_pair.strip())
                current_pair = ""
            else:
                current_pair += char
            
            i += 1
        
        # Добавляем последнюю пару
        if current_pair.strip():
            pairs.append(current_pair.strip())
        
        return pairs
    
    def _build_replacement(self, literal_info: LiteralInfo, trimmed_content: str) -> str:
        """Формирует финальную замену с корректными границами."""
        return f"{literal_info.opening}{trimmed_content}{literal_info.closing}"
    

