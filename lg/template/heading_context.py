"""
Контекстный анализатор заголовков для определения оптимальных параметров
включения Markdown-документов в шаблоны.

Анализирует окружение плейсхолдера в AST для автоматического определения
подходящих значений max_heading_level и strip_single_h1.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .nodes import TemplateAST, MarkdownFileNode, TextNode


@dataclass(frozen=True)
class HeadingContext:
    """
    Контекст заголовков для плейсхолдера Markdown-документа.
    
    Содержит информацию об окружающих заголовках и рекомендуемых
    параметрах для включения документа.
    """
    # Информация о контексте
    placeholders_continuous_chain: bool      # Плейсхолдеры образуют непрерывную цепочку
    placeholder_inside_heading: bool         # Плейсхолдер внутри заголовка

    # Контекстуально определенные параметры для MarkdownCfg
    heading_level: int    # Рекомендуемый max_heading_level
    strip_h1: bool        # Рекомендуемый strip_single_h1


@dataclass(frozen=True)
class HeadingInfo:
    """Информация о заголовке в шаблоне."""
    line_number: int
    level: int
    title: str
    heading_type: str  # 'atx', 'setext', 'placeholder'


@dataclass(frozen=True)
class PlaceholderPosition:
    """Информация о позиции плейсхолдера в шаблоне."""
    line_number: int
    node_index: int
    inside_heading: bool


class MarkdownPatterns:
    """Централизованные паттерны для парсинга Markdown."""
    
    # ATX заголовки: # Заголовок
    ATX_HEADING = re.compile(r'^(#{1,6})\s+(.*)$')
    
    # ATX заголовки только с символами (для плейсхолдеров): ###
    ATX_HEADING_ONLY = re.compile(r'^(#{1,6})\s*$')
    
    # Setext заголовки (подчеркивания)
    SETEXT_H1 = re.compile(r'^=+\s*$')
    SETEXT_H2 = re.compile(r'^-+\s*$')
    
    # Fenced блоки кода
    FENCED_BLOCK = re.compile(r'^```|^~~~')
    
    # Заголовочные символы в строке (для определения inside_heading)
    HEADING_MARKERS_WITH_TEXT = re.compile(r'^#{1,6}\s+.*?$')
    HEADING_MARKERS_ONLY = re.compile(r'^#{1,6}\s*$')


class TextLineProcessor:
    """Процессор для анализа текстовых строк в шаблоне."""
    
    def __init__(self, patterns: MarkdownPatterns):
        self.patterns = patterns
    
    def parse_headings_from_text(self, text: str, start_line: int) -> List[HeadingInfo]:
        """
        Извлекает заголовки из текстового блока.
        
        Args:
            text: Текст для анализа
            start_line: Номер начальной строки
            
        Returns:
            Список найденных заголовков
        """
        headings = []
        lines = text.split('\n')
        current_line = start_line
        in_fenced_block = False
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Отслеживаем fenced блоки
            if self.patterns.FENCED_BLOCK.match(line_stripped):
                in_fenced_block = not in_fenced_block
                current_line += 1
                continue
            
            if in_fenced_block:
                current_line += 1
                continue
            
            # Проверяем ATX заголовки
            heading = self._parse_atx_heading(line_stripped, current_line)
            if heading:
                headings.append(heading)
                current_line += 1
                continue
            
            # Проверяем Setext заголовки
            if i + 1 < len(lines):
                heading = self._parse_setext_heading(line_stripped, lines[i + 1], current_line)
                if heading:
                    headings.append(heading)
            
            current_line += 1
        
        return headings
    
    def _parse_atx_heading(self, line: str, line_number: int) -> Optional[HeadingInfo]:
        """Парсит ATX заголовок (# Заголовок)."""
        match = self.patterns.ATX_HEADING.match(line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            return HeadingInfo(line_number, level, title, 'atx')
        return None
    
    def _parse_setext_heading(self, line: str, next_line: str, line_number: int) -> Optional[HeadingInfo]:
        """Парсит Setext заголовок (подчеркивание)."""
        if not line:
            return None
        
        next_line_stripped = next_line.strip()
        
        if self.patterns.SETEXT_H1.match(next_line_stripped):
            return HeadingInfo(line_number, 1, line, 'setext')
        elif self.patterns.SETEXT_H2.match(next_line_stripped):
            return HeadingInfo(line_number, 2, line, 'setext')
        
        return None
    
    def is_heading_line(self, line: str) -> bool:
        """Проверяет, является ли строка заголовочной."""
        line_stripped = line.strip()
        return (bool(self.patterns.HEADING_MARKERS_WITH_TEXT.match(line_stripped)) or 
                bool(self.patterns.HEADING_MARKERS_ONLY.match(line_stripped)))


class PlaceholderAnalyzer:
    """Анализатор позиций и контекста плейсхолдеров."""
    
    def __init__(self, patterns: MarkdownPatterns):
        self.patterns = patterns
    
    def find_placeholder_position(self, ast: TemplateAST, node_index: int) -> PlaceholderPosition:
        """
        Определяет точную позицию плейсхолдера в шаблоне.
        
        Args:
            ast: AST шаблона
            node_index: Индекс целевого узла
            
        Returns:
            Информация о позиции плейсхолдера
        """
        line_number = self._calculate_line_number(ast, node_index)
        inside_heading = self._is_inside_heading(ast, node_index)
        
        return PlaceholderPosition(line_number, node_index, inside_heading)
    
    def _calculate_line_number(self, ast: TemplateAST, node_index: int) -> int:
        """Вычисляет номер строки для узла."""
        line_number = 0
        for i, node in enumerate(ast):
            if i == node_index:
                break
            if isinstance(node, TextNode):
                line_number += len(node.text.split('\n'))
            else:
                line_number += 1
        return line_number
    
    def _is_inside_heading(self, ast: TemplateAST, node_index: int) -> bool:
        """
        Определяет, находится ли плейсхолдер внутри заголовка.
        
        Проверяет паттерны типа: "### ${md:docs/api}" или "## API: ${md:docs/api}"
        """
        return (self._check_heading_before(ast, node_index) or 
                self._check_heading_continuation(ast, node_index))
    
    def _check_heading_before(self, ast: TemplateAST, node_index: int) -> bool:
        """Проверяет наличие заголовочных символов в предыдущем узле."""
        if node_index <= 0:
            return False
        
        prev_node = ast[node_index - 1]
        if not isinstance(prev_node, TextNode):
            return False
        
        # Проверяем последнюю строку предыдущего узла
        lines = prev_node.text.split('\n')
        if not lines:
            return False
        
        last_line = lines[-1]
        
        # Плейсхолдер на той же строке, если предыдущий узел не заканчивается переводом строки
        if not prev_node.text.endswith('\n'):
            return (bool(self.patterns.HEADING_MARKERS_WITH_TEXT.match(last_line)) or 
                    bool(self.patterns.HEADING_MARKERS_ONLY.match(last_line)))
        
        return False
    
    def _check_heading_continuation(self, ast: TemplateAST, node_index: int) -> bool:
        """Проверяет продолжение заголовка в следующем узле."""
        if node_index + 1 >= len(ast):
            return False
        
        next_node = ast[node_index + 1]
        if not isinstance(next_node, TextNode):
            return False
        
        # Если следующий узел не начинается с перевода строки - плейсхолдер и текст на одной строке
        if not next_node.text.startswith('\n'):
            # Проверяем, есть ли заголовочные символы в предыдущем узле
            return self._check_heading_before(ast, node_index)
        
        return False


class ChainAnalyzer:
    """Анализатор цепочек плейсхолдеров."""
    
    def is_continuous_chain(self, ast: TemplateAST, target_index: int, headings: List[HeadingInfo]) -> bool:
        """
        Определяет, образуют ли плейсхолдеры непрерывную цепочку.
        
        Логика:
        - Если между md-плейсхолдерами есть заголовки, то они НЕ образуют цепочку
        - Если между ними только текст или другие плейсхолдеры - цепочка
        """
        md_indices = self._find_markdown_placeholder_indices(ast)
        
        if len(md_indices) <= 1:
            return self._analyze_single_placeholder(ast, target_index, headings)
        
        # Проверяем заголовки между всеми соседними плейсхолдерами
        for i in range(len(md_indices) - 1):
            if self._has_headings_between(ast, md_indices[i], md_indices[i + 1], headings):
                return False
        
        return True
    
    def _find_markdown_placeholder_indices(self, ast: TemplateAST) -> List[int]:
        """Находит все индексы Markdown плейсхолдеров."""
        return [i for i, node in enumerate(ast) if isinstance(node, MarkdownFileNode)]
    
    def _has_headings_between(self, ast: TemplateAST, start_idx: int, end_idx: int, headings: List[HeadingInfo]) -> bool:
        """Проверяет наличие заголовков между двумя узлами."""
        start_line = self._calculate_node_line(ast, start_idx)
        end_line = self._calculate_node_line(ast, end_idx)
        
        return any(start_line < heading.line_number < end_line for heading in headings)
    
    def _calculate_node_line(self, ast: TemplateAST, node_index: int) -> int:
        """Вычисляет номер строки для узла."""
        line = 0
        for i, node in enumerate(ast):
            if i == node_index:
                break
            if isinstance(node, TextNode):
                line += len(node.text.split('\n'))
            else:
                line += 1
        return line
    
    def _analyze_single_placeholder(self, ast: TemplateAST, node_index: int, headings: List[HeadingInfo]) -> bool:
        """
        Анализирует единственный плейсхолдер на предмет "цепочности".
        
        Если плейсхолдер окружен заголовками одного уровня - он разделен.
        """
        placeholder_line = self._calculate_node_line(ast, node_index)
        
        headings_before = [h for h in headings if h.line_number < placeholder_line]
        headings_after = [h for h in headings if h.line_number > placeholder_line]
        
        if headings_before and headings_after:
            last_before = headings_before[-1]
            first_after = headings_after[0]
            
            # Если заголовки одного уровня - плейсхолдер разделен
            if first_after.level <= last_before.level:
                return False
        
        return True


class HeadingContextDetectorV2:
    """
    Детектор контекста заголовков.
    """
    
    def __init__(self):
        self.patterns = MarkdownPatterns()
        self.text_processor = TextLineProcessor(self.patterns)
        self.placeholder_analyzer = PlaceholderAnalyzer(self.patterns)
        self.chain_analyzer = ChainAnalyzer()
    
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
        # 1. Парсим все заголовки в шаблоне
        template_headings = self._parse_all_headings(ast)
        
        # 2. Определяем позицию плейсхолдера
        placeholder_pos = self.placeholder_analyzer.find_placeholder_position(ast, node_index)
        
        # 3. Находим родительский заголовок
        parent_level = self._find_parent_heading_level(placeholder_pos.line_number, template_headings)
        
        # 4. Анализируем цепочки плейсхолдеров
        is_chain = self.chain_analyzer.is_continuous_chain(ast, node_index, template_headings)
        
        # 5. Вычисляем итоговые параметры
        heading_level, strip_h1 = self._calculate_parameters(
            placeholder_pos.inside_heading, parent_level, is_chain
        )
        
        return HeadingContext(
            placeholders_continuous_chain=is_chain,
            placeholder_inside_heading=placeholder_pos.inside_heading,
            heading_level=heading_level,
            strip_h1=strip_h1
        )
    
    def _parse_all_headings(self, ast: TemplateAST) -> List[HeadingInfo]:
        """
        Парсит все заголовки из AST шаблона.
        
        Включает обычные заголовки и заголовки с плейсхолдерами.
        """
        headings = []
        current_line = 0
        
        for node_idx, node in enumerate(ast):
            if isinstance(node, TextNode):
                # Парсим заголовки из текста
                text_headings = self.text_processor.parse_headings_from_text(node.text, current_line)
                headings.extend(text_headings)
                
                # Проверяем заголовки с плейсхолдерами
                placeholder_heading = self._check_placeholder_heading(ast, node_idx, current_line)
                if placeholder_heading:
                    headings.append(placeholder_heading)
                
                current_line += len(node.text.split('\n'))
            else:
                current_line += 1
        
        return headings
    
    def _check_placeholder_heading(self, ast: TemplateAST, node_idx: int, current_line: int) -> Optional[HeadingInfo]:
        """
        Проверяет, является ли текущий узел частью заголовка с плейсхолдером.
        
        Ищет паттерн: TextNode("### ") + MarkdownFileNode
        """
        if not isinstance(ast[node_idx], TextNode):
            return None
        
        # Проверяем следующий узел
        if node_idx + 1 >= len(ast) or not isinstance(ast[node_idx + 1], MarkdownFileNode):
            return None
        
        text_node = ast[node_idx]
        if isinstance(text_node, TextNode):
            lines = text_node.text.split('\n')
        else:
            return None
        
        if not lines:
            return None
        
        last_line = lines[-1]
        
        # Проверяем, что последняя строка содержит только заголовочные символы
        match = self.patterns.ATX_HEADING_ONLY.match(last_line)
        if match:
            level = len(match.group(1))
            # Вычисляем номер строки для заголовка
            heading_line = current_line + len(lines) - 1
            
            return HeadingInfo(
                line_number=heading_line,
                level=level,
                title="[placeholder]",
                heading_type='placeholder'
            )
        
        return None
    
    def _find_parent_heading_level(self, placeholder_line: int, headings: List[HeadingInfo]) -> int:
        """Находит уровень ближайшего родительского заголовка."""
        parent_level = 1
        
        for heading in headings:
            if heading.line_number < placeholder_line:
                parent_level = heading.level
            else:
                break
        
        return parent_level
    
    def _calculate_parameters(self, inside_heading: bool, parent_level: int, is_chain: bool) -> Tuple[int, bool]:
        """
        Вычисляет итоговые параметры heading_level и strip_h1.
        
        Args:
            inside_heading: Плейсхолдер внутри заголовка
            parent_level: Уровень родительского заголовка
            is_chain: Плейсхолдеры образуют цепочку
            
        Returns:
            Кортеж (heading_level, strip_h1)
        """
        if inside_heading:
            # Для плейсхолдеров внутри заголовков используем уровень родительского заголовка
            heading_level = parent_level
        else:
            # Для обычных плейсхолдеров - родительский уровень + 1, ограничиваем до H6
            heading_level = min(parent_level + 1, 6)
        
        # strip_h1=true когда плейсхолдеры разделены заголовками (НЕ цепочка)
        # и плейсхолдер не внутри заголовка
        strip_h1 = not is_chain and not inside_heading
        
        return heading_level, strip_h1


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
    detector = HeadingContextDetectorV2()
    return detector.detect_context(node, ast, node_index)