"""
Контекстный анализатор заголовков для определения оптимальных параметров
включения Markdown-документов в шаблоны.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .nodes import MarkdownFileNode
from ..nodes import TemplateAST, TextNode
from ..types import ProcessingContext


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
    strip_h1: bool        # Рекомендуемый strip_h1


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
    
    # Горизонтальные черты (разделители контекста)
    HORIZONTAL_RULE = re.compile(r'^\s{0,3}[-*_]{3,}\s*$')
    
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
    
    def parse_horizontal_rules_from_text(self, text: str, start_line: int) -> List[int]:
        """
        Извлекает позиции горизонтальных черт из текстового блока.
        
        Args:
            text: Текст для анализа
            start_line: Номер начальной строки
            
        Returns:
            Список номеров строк с горизонтальными чертами
        """
        horizontal_rules = []
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
            
            # Проверяем горизонтальные черты (только вне fenced блоков)
            if self.patterns.HORIZONTAL_RULE.match(line):
                # Проверяем, что это НЕ подчеркивание Setext заголовка
                if not self._is_setext_underline(lines, i):
                    horizontal_rules.append(current_line)
            
            current_line += 1
        
        return horizontal_rules
    
    def _is_setext_underline(self, lines: List[str], line_index: int) -> bool:
        """
        Проверяет, является ли строка подчеркиванием Setext заголовка.
        
        Args:
            lines: Список всех строк текста
            line_index: Индекс проверяемой строки
            
        Returns:
            True, если строка является подчеркиванием Setext заголовка
        """
        if line_index == 0:
            return False
            
        # Проверяем предыдущую строку
        prev_line = lines[line_index - 1].strip()
        
        # Предыдущая строка должна содержать текст (не быть пустой)
        if not prev_line:
            return False
            
        # Предыдущая строка не должна быть заголовком ATX или другой разметкой
        if (self.patterns.ATX_HEADING.match(prev_line) or
            self.patterns.FENCED_BLOCK.match(prev_line) or
            self.patterns.HORIZONTAL_RULE.match(prev_line)):
            return False
            
        return True


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
    
    def __init__(self, placeholder_analyzer: PlaceholderAnalyzer):
        """
        Инициализирует анализатор цепочек.
        
        Args:
            placeholder_analyzer: Анализатор позиций плейсхолдеров
        """
        self.placeholder_analyzer = placeholder_analyzer
    
    def is_continuous_chain(self, ast: TemplateAST, target_index: int, headings: List[HeadingInfo], horizontal_rules: Optional[List[int]] = None) -> bool:
        """
        Определяет, образуют ли плейсхолдеры непрерывную цепочку.
        
        Логика:
        - Плейсхолдеры с глобами всегда считаются непрерывной цепочкой (вставляют несколько документов)
        - Если между md-плейсхолдерами есть заголовки или горизонтальные черты, то они НЕ образуют цепочку
        - Если между ними только текст или другие плейсхолдеры - цепочка
        - Плейсхолдеры внутри заголовков НЕ участвуют в анализе цепочек
        """
        if horizontal_rules is None:
            horizontal_rules = []
            
        # Специальный случай: плейсхолдер с глобами всегда образует цепочку
        target_node = ast[target_index]
        if isinstance(target_node, MarkdownFileNode) and target_node.is_glob:
            return True
        
        # Находим только "обычные" плейсхолдеры (не внутри заголовков)
        regular_md_indices = self._find_regular_markdown_placeholder_indices(ast)
        
        if len(regular_md_indices) <= 1:
            return self._analyze_single_placeholder(ast, target_index, headings, horizontal_rules)
        
        # Разделяем плейсхолдеры на сегменты горизонтальными чертами
        segments = self._split_placeholders_by_horizontal_rules(ast, regular_md_indices, horizontal_rules)
        
        # Находим сегмент, содержащий целевой плейсхолдер
        target_segment = None
        for segment in segments:
            if target_index in segment:
                target_segment = segment
                break
        
        if not target_segment:
            return self._analyze_single_placeholder(ast, target_index, headings, horizontal_rules)
        
        # Если в сегменте только один плейсхолдер - он изолирован
        if len(target_segment) <= 1:
            return False
        
        # Проверяем заголовки между плейсхолдерами в пределах сегмента
        for i in range(len(target_segment) - 1):
            has_headings = self._has_headings_between(ast, target_segment[i], target_segment[i + 1], headings)
            if has_headings:
                return False
        
        return True

    def _find_regular_markdown_placeholder_indices(self, ast: TemplateAST) -> List[int]:
        """
        Находит индексы только "обычных" Markdown плейсхолдеров (не внутри заголовков).
        
        Плейсхолдеры внутри заголовков не участвуют в анализе цепочек,
        так как они имеют другую семантику - заменяют текст заголовка.
        """        
        regular_indices = []
        for i, node in enumerate(ast):
            if isinstance(node, MarkdownFileNode):
                # Проверяем, находится ли плейсхолдер внутри заголовка
                placeholder_pos = self.placeholder_analyzer.find_placeholder_position(ast, i)
                if not placeholder_pos.inside_heading:
                    regular_indices.append(i)
        
        return regular_indices
    
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
    
    def _analyze_single_placeholder(self, ast: TemplateAST, node_index: int, headings: List[HeadingInfo], horizontal_rules: Optional[List[int]] = None) -> bool:
        """
        Анализирует единственный плейсхолдер на предмет "цепочности".
        
        Плейсхолдеры с глобами всегда считаются цепочкой.
        Если плейсхолдер окружен заголовками одного уровня или горизонтальными чертами - он разделен.
        """
        if horizontal_rules is None:
            horizontal_rules = []
            
        # Специальный случай: плейсхолдер с глобами всегда образует цепочку
        target_node = ast[node_index]
        if isinstance(target_node, MarkdownFileNode) and target_node.is_glob:
            return True
        
        placeholder_line = self._calculate_node_line(ast, node_index)
        
        # Проверяем наличие горизонтальных черт рядом с плейсхолдером
        rules_before = [r for r in horizontal_rules if r < placeholder_line]
        rules_after = [r for r in horizontal_rules if r > placeholder_line]
        
        # Если есть горизонтальные черты до и после плейсхолдера - он изолирован
        if rules_before and rules_after:
            return False
        
        headings_before = [h for h in headings if h.line_number < placeholder_line]
        headings_after = [h for h in headings if h.line_number > placeholder_line]
        
        if headings_before and headings_after:
            last_before = headings_before[-1]
            first_after = headings_after[0]
            
            # Если заголовки одного уровня - плейсхолдер разделен
            if first_after.level <= last_before.level:
                return False
        
        return True
    
    def _has_horizontal_rules_between(self, ast: TemplateAST, start_idx: int, end_idx: int, horizontal_rules: List[int]) -> bool:
        """Проверяет наличие горизонтальных черт между двумя узлами."""
        start_line = self._calculate_node_line(ast, start_idx)
        end_line = self._calculate_node_line(ast, end_idx)
        
        return any(start_line < rule_line < end_line for rule_line in horizontal_rules)
    
    def _split_placeholders_by_horizontal_rules(self, ast: TemplateAST, placeholder_indices: List[int], horizontal_rules: List[int]) -> List[List[int]]:
        """
        Разделяет плейсхолдеры на сегменты горизонтальными чертами.
        
        Args:
            ast: AST шаблона
            placeholder_indices: Список индексов плейсхолдеров
            horizontal_rules: Список номеров строк с горизонтальными чертами
            
        Returns:
            Список сегментов, каждый сегмент - список индексов плейсхолдеров
        """
        if not horizontal_rules:
            return [placeholder_indices]
        
        segments = []
        current_segment = []
        
        for placeholder_idx in placeholder_indices:
            placeholder_node = ast[placeholder_idx]
            if not isinstance(placeholder_node, MarkdownFileNode):
                continue
            
            # Получаем номер строки плейсхолдера
            placeholder_line = self._get_node_line_number(ast, placeholder_idx)
            
            # Проверяем, есть ли горизонтальная черта перед этим плейсхолдером
            # (если текущий сегмент не пустой)
            if current_segment:
                prev_placeholder_idx = current_segment[-1]
                prev_placeholder_line = self._get_node_line_number(ast, prev_placeholder_idx)
                
                # Есть ли горизонтальная черта между предыдущим и текущим плейсхолдером?
                has_rule_between = any(prev_placeholder_line < rule_line < placeholder_line 
                                     for rule_line in horizontal_rules)
                
                if has_rule_between:
                    # Начинаем новый сегмент
                    if current_segment:
                        segments.append(current_segment)
                    current_segment = [placeholder_idx]
                else:
                    # Продолжаем текущий сегмент
                    current_segment.append(placeholder_idx)
            else:
                # Первый плейсхолдер - начинаем сегмент
                current_segment.append(placeholder_idx)
        
        # Добавляем последний сегмент
        if current_segment:
            segments.append(current_segment)
        
        return segments
    
    def _get_node_line_number(self, ast: TemplateAST, node_index: int) -> int:
        """Получает номер строки узла в AST."""
        line_number = 1
        for i in range(node_index):
            node = ast[i]
            if isinstance(node, TextNode):
                line_number += node.text.count('\n')
            else:
                line_number += 1
        return line_number


class HeadingContextDetector:
    """
    Детектор контекста заголовков.
    """
    
    def __init__(self):
        self.patterns = MarkdownPatterns()
        self.text_processor = TextLineProcessor(self.patterns)
        self.placeholder_analyzer = PlaceholderAnalyzer(self.patterns)
        self.chain_analyzer = ChainAnalyzer(self.placeholder_analyzer)
    
    def detect_context(self, processing_context: ProcessingContext) -> HeadingContext:
        """
        Анализирует контекст плейсхолдера и определяет оптимальные параметры.
        
        Args:
            processing_context:Контекст обработки узла AST

        Returns:
            HeadingContext с рекомендациями по параметрам
        """
        # 1. Парсим все заголовки в шаблоне
        template_headings = self._parse_all_headings(processing_context.ast)
        
        # 2. Парсим все горизонтальные черты в шаблоне
        horizontal_rules = self._parse_all_horizontal_rules(processing_context.ast)
        
        # 3. Определяем позицию плейсхолдера
        placeholder_pos = self.placeholder_analyzer.find_placeholder_position(processing_context.ast, processing_context.node_index)
        
        # 4. Находим родительский заголовок с учетом горизонтальных черт
        parent_level = self._find_parent_heading_level(placeholder_pos.line_number, template_headings, horizontal_rules)
        
        # 5. Анализируем цепочки плейсхолдеров с учетом горизонтальных черт
        is_chain = self.chain_analyzer.is_continuous_chain(processing_context.ast, processing_context.node_index, template_headings, horizontal_rules)
        

        
        # 6. Проверяем, изолирован ли плейсхолдер горизонтальной чертой
        isolated_by_hr = self._is_placeholder_isolated_by_horizontal_rule(
            placeholder_pos.line_number, horizontal_rules, template_headings
        )
        
        # 7. Вычисляем итоговые параметры
        heading_level, strip_h1 = self._calculate_parameters(
            placeholder_pos.inside_heading, parent_level, is_chain, isolated_by_hr
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
    
    def _parse_all_horizontal_rules(self, ast: TemplateAST) -> List[int]:
        """
        Парсит все горизонтальные черты из AST шаблона.
        
        Returns:
            Список номеров строк с горизонтальными чертами
        """
        horizontal_rules = []
        current_line = 0
        
        for node in ast:
            if isinstance(node, TextNode):
                # Парсим горизонтальные черты из текста
                rules = self.text_processor.parse_horizontal_rules_from_text(node.text, current_line)
                horizontal_rules.extend(rules)
                current_line += len(node.text.split('\n'))
            else:
                current_line += 1
        
        return horizontal_rules
    
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
    
    def _find_parent_heading_level(self, placeholder_line: int, headings: List[HeadingInfo], horizontal_rules: List[int]) -> Optional[int]:
        """
        Находит уровень ближайшего родительского заголовка с учетом горизонтальных черт.

        Горизонтальная черта сбрасывает контекст заголовков до уровня 1.

        Returns:
            Уровень родительского заголовка или None если родительских заголовков не найдено
        """
        parent_level = None

        # Находим ближайшую горизонтальную черту перед плейсхолдером
        closest_rule = None
        for rule_line in horizontal_rules:
            if rule_line < placeholder_line:
                closest_rule = rule_line
            else:
                break

        # Если есть горизонтальная черта, анализируем только заголовки после неё
        start_line = closest_rule if closest_rule is not None else 0

        for heading in headings:
            if start_line <= heading.line_number < placeholder_line:
                parent_level = heading.level
            elif heading.line_number >= placeholder_line:
                break

        return parent_level
    
    def _is_placeholder_isolated_by_horizontal_rule(self, placeholder_line: int, horizontal_rules: List[int], headings: List[HeadingInfo]) -> bool:
        """
        Проверяет, изолирован ли плейсхолдер горизонтальной чертой.
        
        Плейсхолдер считается изолированным горизонтальной чертой, если:
        1. Есть горизонтальная черта перед ним
        2. Между горизонтальной чертой и плейсхолдером нет заголовков
        """
        if not horizontal_rules:
            return False
            
        # Находим ближайшую горизонтальную черту перед плейсхолдером
        closest_rule = None
        for rule_line in horizontal_rules:
            if rule_line < placeholder_line:
                closest_rule = rule_line
            else:
                break
                
        if closest_rule is None:
            return False
            
        # Проверяем, есть ли заголовки между горизонтальной чертой и плейсхолдером
        for heading in headings:
            if closest_rule < heading.line_number < placeholder_line:
                # Есть заголовок между чертой и плейсхолдером - не изолирован чертой
                return False
                
        return True
    
    def _calculate_parameters(self, inside_heading: bool, parent_level: Optional[int], is_chain: bool, isolated_by_hr: bool = False) -> Tuple[int, bool]:
        """
        Вычисляет итоговые параметры heading_level и strip_h1.

        Args:
            inside_heading: Плейсхолдер внутри заголовка
            parent_level: Уровень родительского заголовка или None если родительских заголовков не найдено
            is_chain: Плейсхолдеры образуют цепочку
            isolated_by_hr: Плейсхолдер изолирован горизонтальной чертой

        Returns:
            Кортеж (heading_level, strip_h1)
        """
        # Случай 1: Плейсхолдер внутри заголовка
        # Пример: ### ${md:docs/api}
        # H1 из файла заменяет содержимое заголовка H3
        if inside_heading:
            # parent_level не может быть None для inside_heading (всегда есть уровень заголовка)
            return parent_level if parent_level is not None else 1, False

        # Случай 2: Нет родительских заголовков
        # Пример: ${md:README} (без заголовков вообще)
        # Пример: ${md:README}\n---\n# License (заголовок есть, но после плейсхолдера)
        # Документ вставляется как корневой (верхнего уровня)
        if parent_level is None:
            return 1, False

        # Случай 3: Плейсхолдер изолирован горизонтальной чертой
        # Пример: ## Section\n---\n${md:docs/api}
        # Горизонтальная черта сбрасывает контекст → новый корневой раздел
        if isolated_by_hr:
            return 1, False

        # Случай 4: Обычные плейсхолдеры под родительским заголовком
        # Пример: ## Section\n${md:docs/api}\n${md:docs/guide}
        # Вложенность: parent_level + 1 (ограничиваем до H6)
        heading_level = min(parent_level + 1, 6)

        # strip_h1 зависит от того, образуют ли плейсхолдеры цепочку:
        # - Цепочка (нет разделяющих заголовков): strip_h1 = false (H1 сохраняется)
        # - Разделены заголовками: strip_h1 = true (H1 удаляется)
        strip_h1 = not is_chain

        return heading_level, strip_h1


def detect_heading_context_for_node(processing_context: ProcessingContext) -> HeadingContext:
    """
    Удобная функция для анализа контекста заголовков для одного узла.
    
    Args:
        processing_context:Контекст обработки узла AST
        
    Returns:
        HeadingContext с рекомендациями
    """
    detector = HeadingContextDetector()
    return detector.detect_context(processing_context)