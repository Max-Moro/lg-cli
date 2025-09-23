"""
Контекстный анализатор заголовков для определения оптимальных параметров
включения Markdown-документов в шаблоны.

Анализирует окружение плейсхолдера в AST для автоматического определения
подходящих значений max_heading_level и strip_h1.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .nodes import TemplateAST, TemplateNode, TextNode, MarkdownFileNode


@dataclass(frozen=True)
class HeadingContext:
    """
    Контекст заголовков для плейсхолдера Markdown-документа.
    
    Содержит информацию об окружающих заголовках и рекомендуемых
    параметрах для включения документа.
    """
    # Информация о контексте
    parent_heading_level: Optional[int] = None  # Уровень родительского заголовка
    is_inline_after_heading: bool = False      # Плейсхолдер сразу после заголовка
    suggested_max_heading_level: Optional[int] = None  # Рекомендуемый max_heading_level
    suggested_strip_h1: Optional[bool] = None   # Рекомендуемый strip_h1
    
    # Дополнительная информация для диагностики
    parent_heading_text: Optional[str] = None   # Текст родительского заголовка
    analysis_reason: str = ""                   # Причина выбора параметров


class HeadingContextDetector:
    """
    Детектор контекста заголовков для плейсхолдеров Markdown-документов.
    
    Анализирует AST шаблона для определения оптимальных параметров
    включения Markdown-документов на основе окружающих заголовков.
    """
    
    # Регулярные выражения для распознавания заголовков в тексте
    ATX_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+?)(?:\s+#*)?$', re.MULTILINE)
    SETEXT_H1_RE = re.compile(r'^(.+?)\n=+\s*$', re.MULTILINE)
    SETEXT_H2_RE = re.compile(r'^(.+?)\n-+\s*$', re.MULTILINE)
    
    def __init__(self):
        """Инициализирует детектор контекста заголовков."""
        pass
    
    def detect_context(self, target_node: MarkdownFileNode, ast: TemplateAST, node_index: int) -> HeadingContext:
        """
        Анализирует контекст плейсхолдера и определяет оптимальные параметры.
        
        Args:
            target_node: Узел MarkdownFileNode для анализа
            ast: Полный AST шаблона
            node_index: Индекс целевого узла в AST
            
        Returns:
            HeadingContext с рекомендациями по параметрам
        """
        # Анализируем текстовые узлы вокруг плейсхолдера
        preceding_text = self._get_preceding_text(ast, node_index)
        following_text = self._get_following_text(ast, node_index)
        
        # Определяем ближайший родительский заголовок
        parent_info = self._find_parent_heading(preceding_text)
        
        # Проверяем, находится ли плейсхолдер сразу после заголовка
        is_inline = self._is_inline_after_heading(preceding_text, following_text)
        
        # Вычисляем рекомендуемые параметры
        suggestions = self._calculate_suggestions(parent_info, is_inline)
        
        return HeadingContext(
            parent_heading_level=parent_info[0] if parent_info else None,
            is_inline_after_heading=is_inline,
            suggested_max_heading_level=suggestions[0],
            suggested_strip_h1=suggestions[1],
            parent_heading_text=parent_info[1] if parent_info else None,
            analysis_reason=suggestions[2]
        )
    
    def _get_preceding_text(self, ast: TemplateAST, node_index: int) -> str:
        """
        Получает предшествующий текст до указанного узла.
        
        Собирает текст из всех TextNode, предшествующих целевому узлу.
        """
        text_parts = []
        
        for i in range(node_index - 1, -1, -1):
            node = ast[i]
            if isinstance(node, TextNode):
                # Добавляем в начало, так как идем в обратном порядке
                text_parts.insert(0, node.text)
            else:
                # Прерываем на первом не-текстовом узле
                break
        
        return ''.join(text_parts)
    
    def _get_following_text(self, ast: TemplateAST, node_index: int) -> str:
        """
        Получает следующий текст после указанного узла.
        
        Собирает текст из ближайшего TextNode после целевого узла.
        """
        if node_index + 1 < len(ast):
            next_node = ast[node_index + 1]
            if isinstance(next_node, TextNode):
                return next_node.text
        
        return ""
    
    def _find_parent_heading(self, preceding_text: str) -> Optional[Tuple[int, str]]:
        """
        Находит ближайший родительский заголовок в предшествующем тексте.
        
        Args:
            preceding_text: Текст, предшествующий плейсхолдеру
            
        Returns:
            Кортеж (уровень_заголовка, текст_заголовка) или None
        """
        # Разбиваем текст на строки для анализа с конца
        lines = preceding_text.split('\n')
        
        # Ищем заголовки ATX (### Заголовок)
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            match = self.ATX_HEADING_RE.match(line)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                return level, title
        
        # Ищем заголовки Setext (с подчеркиванием)
        text_chunk = '\n'.join(lines)
        
        # Ищем H1 (=====)
        h1_matches = list(self.SETEXT_H1_RE.finditer(text_chunk))
        if h1_matches:
            last_h1 = h1_matches[-1]
            title = last_h1.group(1).strip()
            return 1, title
        
        # Ищем H2 (-----)
        h2_matches = list(self.SETEXT_H2_RE.finditer(text_chunk))
        if h2_matches:
            last_h2 = h2_matches[-1]
            title = last_h2.group(1).strip()
            return 2, title
        
        return None
    
    def _is_inline_after_heading(self, preceding_text: str, following_text: str) -> bool:
        """
        Определяет, находится ли плейсхолдер непосредственно после заголовка.
        
        Плейсхолдер считается inline, если:
        - Он находится на той же строке что и заголовок, или
        - Между заголовком и плейсхолдером только пробельные символы
        
        Args:
            preceding_text: Текст перед плейсхолдером
            following_text: Текст после плейсхолдера (для проверки переноса строки)
            
        Returns:
            True если плейсхолдер inline после заголовка
        """
        if not preceding_text:
            return False
        
        # Проверяем последние строки предшествующего текста
        lines = preceding_text.split('\n')
        
        # Если текст заканчивается переносом строки, плейсхолдер не inline
        if preceding_text.endswith('\n'):
            return False
        
        # Проверяем последнюю строку на наличие заголовка ATX
        if lines:
            last_line = lines[-1]
            if self.ATX_HEADING_RE.match(last_line.strip()):
                # Плейсхолдер на той же строке что и заголовок ATX
                return True
        
        # Проверяем наличие заголовка Setext в конце
        if len(lines) >= 2:
            # Проверяем паттерн: заголовок + подчеркивание + плейсхолдер
            potential_title = lines[-2]
            underline = lines[-1]
            
            if (re.match(r'^=+\s*$', underline.strip()) or 
                re.match(r'^-+\s*$', underline.strip())):
                return True
        
        return False
    
    def _calculate_suggestions(self, parent_info: Optional[Tuple[int, str]], is_inline: bool) -> Tuple[Optional[int], Optional[bool], str]:
        """
        Вычисляет рекомендуемые параметры на основе анализа контекста.
        
        Args:
            parent_info: Информация о родительском заголовке (уровень, текст)
            is_inline: Является ли плейсхолдер inline после заголовка
            
        Returns:
            Кортеж (suggested_max_heading_level, suggested_strip_h1, reason)
        """
        if parent_info is None:
            # Нет родительского заголовка
            if is_inline:
                # Плейсхолдер inline, но без заголовка - необычная ситуация
                return 2, False, "inline_no_parent"
            else:
                # Плейсхолдер в корне документа
                return None, False, "root_level"
        
        parent_level, parent_text = parent_info
        
        if is_inline:
            # Плейсхолдер inline после заголовка
            # Содержимое документа заменяет заголовок
            next_level = parent_level + 1
            return next_level, True, f"inline_after_h{parent_level}"
        else:
            # Плейсхолдер в теле после заголовка
            # Содержимое документа должно быть на следующем уровне
            next_level = parent_level + 1
            return next_level, False, f"body_under_h{parent_level}"
    
    def format_analysis(self, context: HeadingContext) -> str:
        """
        Форматирует результат анализа для отладки и диагностики.
        
        Args:
            context: Результат анализа контекста
            
        Returns:
            Строка с детальной информацией об анализе
        """
        parts = []
        
        if context.parent_heading_level:
            parts.append(f"Parent heading: H{context.parent_heading_level}")
            if context.parent_heading_text:
                parts.append(f"'{context.parent_heading_text}'")
        else:
            parts.append("No parent heading")
        
        parts.append(f"Inline: {context.is_inline_after_heading}")
        
        if context.suggested_max_heading_level:
            parts.append(f"Suggested max_level: {context.suggested_max_heading_level}")
        
        if context.suggested_strip_h1 is not None:
            parts.append(f"Suggested strip_h1: {context.suggested_strip_h1}")
        
        parts.append(f"Reason: {context.analysis_reason}")
        
        return " | ".join(parts)


def detect_heading_context_for_node(node: MarkdownFileNode, ast: TemplateAST, node_index: int) -> HeadingContext:
    """
    Удобная функция для анализа контекста заголовков для одного узла.
    
    Args:
        node: Узел MarkdownFileNode для анализа
        ast: Полный AST шаблона
        node_index: Индекс узла в AST
        
    Returns:
        HeadingContext с рекомендациями
    """
    detector = HeadingContextDetector()
    return detector.detect_context(node, ast, node_index)