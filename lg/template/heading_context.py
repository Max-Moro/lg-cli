"""
Контекстный анализатор заголовков для определения оптимальных параметров
включения Markdown-документов в шаблоны.

Анализирует окружение плейсхолдера в AST для автоматического определения
подходящих значений max_heading_level и strip_single_h1.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from .nodes import TemplateAST, MarkdownFileNode, TextNode


@dataclass(frozen=True)
class HeadingContext:
    """
    Контекст заголовков для плейсхолдера Markdown-документа.
    
    Содержит информацию об окружающих заголовках и рекомендуемых
    параметрах для включения документа.
    """
    # Информация о контексте (можно расширять, есть потребуется)
    placeholders_continuous_chain: bool      # Плейсхолдеры образуют непрерывную цепочку / иначе разделены заголовками родительского шаблона
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
    heading_type: str  # 'atx' или 'setext'


@dataclass(frozen=True)
class PlaceholderInfo:
    """Информация о позиции плейсхолдера."""
    line_number: int
    inside_heading: bool


class HeadingContextDetector:
    """
    Детектор контекста заголовков для плейсхолдеров Markdown-документов.
    
    Анализирует AST шаблона для определения оптимальных параметров
    включения Markdown-документов на основе окружающих заголовков.
    """
    
    def __init__(self):
        """Инициализирует детектор контекста заголовков."""
        # Регулярные выражения для парсинга заголовков
        self.atx_heading_re = re.compile(r'^(#{1,6})\s+(.*)$')
        self.setext_h1_re = re.compile(r'^=+\s*$')
        self.setext_h2_re = re.compile(r'^-+\s*$')
        # Регулярное выражение для fenced блоков
        self.fenced_start_re = re.compile(r'^```|^~~~')
    
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
        template_headings = self._parse_template_headings(ast)
        
        # 2. Определяем позицию целевого плейсхолдера в тексте
        placeholder_info = self._analyze_placeholder_position(target_node, ast, node_index)
        
        # 3. Находим ближайший родительский заголовок
        parent_heading_level = self._find_parent_heading_level(placeholder_info, template_headings)
        
        # 4. Анализируем, образуют ли плейсхолдеры непрерывную цепочку
        is_continuous_chain = self._analyze_placeholder_chain(target_node, ast, node_index, template_headings)
        
        # 5. Определяем итоговые параметры
        if placeholder_info.inside_heading:
            # Для плейсхолдеров внутри заголовков используем уровень родительского заголовка
            heading_level = parent_heading_level
        else:
            # Для обычных плейсхолдеров - родительский уровень + 1
            heading_level = min(parent_heading_level + 1, 6)  # Ограничиваем до H6
        
        # strip_h1=true когда плейсхолдеры разделены заголовками (НЕ цепочка)
        # и плейсхолдер не внутри заголовка (там особая логика)
        strip_h1 = not is_continuous_chain and not placeholder_info.inside_heading
        
        return HeadingContext(
            placeholders_continuous_chain=is_continuous_chain,
            placeholder_inside_heading=placeholder_info.inside_heading,
            heading_level=heading_level,
            strip_h1=strip_h1
        )
    
    def _parse_template_headings(self, ast: TemplateAST) -> List[HeadingInfo]:
        """
        Парсит все заголовки из текстовых узлов шаблона.
        Также обнаруживает заголовки с плейсхолдерами (например, "### ${md:docs/api}").
        
        Args:
            ast: AST шаблона для парсинга
            
        Returns:
            Список найденных заголовков с позициями
        """
        headings = []
        current_line = 0
        in_fenced_block = False
        
        for node_idx, node in enumerate(ast):
            if isinstance(node, TextNode):
                lines = node.text.split('\n')
                
                for i, line in enumerate(lines):
                    line_stripped = line.strip()
                    
                    # Отслеживаем fenced блоки
                    if self.fenced_start_re.match(line_stripped):
                        in_fenced_block = not in_fenced_block
                        current_line += 1
                        continue
                    
                    if in_fenced_block:
                        current_line += 1
                        continue
                    
                    # Проверяем ATX заголовки (# заголовок)
                    atx_match = self.atx_heading_re.match(line_stripped)
                    if atx_match:
                        level = len(atx_match.group(1))
                        title = atx_match.group(2).strip()
                        headings.append(HeadingInfo(
                            line_number=current_line,
                            level=level,
                            title=title,
                            heading_type='atx'
                        ))
                        current_line += 1
                        continue
                    
                    # Проверяем потенциальные заголовки с плейсхолдерами
                    # Паттерн: "### " в конце строки + следующий узел может быть MarkdownFileNode
                    if (re.match(r'^#{1,6}\s*$', line_stripped) and 
                        node_idx + 1 < len(ast) and 
                        isinstance(ast[node_idx + 1], MarkdownFileNode) and
                        i == len(lines) - 1):  # это последняя строка текстового узла
                        
                        level = len(line_stripped.rstrip())
                        # Для заголовков с плейсхолдерами используем "placeholder" как заголовок
                        # (поскольку реальный заголовок будет извлечен из файла)
                        headings.append(HeadingInfo(
                            line_number=current_line,
                            level=level,
                            title="[placeholder]",
                            heading_type='atx'
                        ))
                        current_line += 1
                        continue
                    
                    # Проверяем Setext заголовки (подчеркивания)
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if line_stripped and self.setext_h1_re.match(next_line):
                            headings.append(HeadingInfo(
                                line_number=current_line,
                                level=1,
                                title=line_stripped,
                                heading_type='setext'
                            ))
                        elif line_stripped and self.setext_h2_re.match(next_line):
                            headings.append(HeadingInfo(
                                line_number=current_line,
                                level=2,
                                title=line_stripped,
                                heading_type='setext'
                            ))
                    
                    current_line += 1
            else:
                # Для других типов узлов считаем как одну строку (упрощение)
                current_line += 1
        
        return headings
    
    def _analyze_placeholder_position(self, target_node: MarkdownFileNode, ast: TemplateAST, node_index: int) -> PlaceholderInfo:
        """
        Анализирует позицию плейсхолдера в тексте шаблона.
        
        Args:
            target_node: Целевой узел плейсхолдера
            ast: AST шаблона
            node_index: Индекс узла в AST
            
        Returns:
            Информация о позиции плейсхолдера
        """
        # Определяем приблизительную строку плейсхолдера
        placeholder_line = 0
        for i, node in enumerate(ast):
            if i == node_index:
                break
            if isinstance(node, TextNode):
                placeholder_line += len(node.text.split('\n'))
            else:
                placeholder_line += 1
        
        # Проверяем, находится ли плейсхолдер внутри заголовка
        inside_heading = self._is_placeholder_inside_heading(target_node, ast, node_index)
        
        return PlaceholderInfo(
            line_number=placeholder_line,
            inside_heading=inside_heading
        )
    
    def _is_placeholder_inside_heading(self, target_node: MarkdownFileNode, ast: TemplateAST, node_index: int) -> bool:
        """
        Проверяет, находится ли плейсхолдер внутри заголовка.
        
        Ищет паттерны типа: "### ${md:docs/api}" где плейсхолдер находится 
        в той же строке что и символы заголовка.
        
        Args:
            target_node: Целевой узел плейсхолдера
            ast: AST шаблона
            node_index: Индекс узла в AST
            
        Returns:
            True если плейсхолдер находится внутри заголовка
        """
        # Проверяем предыдущий узел на наличие символов заголовка без перевода строки
        if node_index > 0:
            prev_node = ast[node_index - 1]
            if isinstance(prev_node, TextNode):
                # Получаем последнюю строку предыдущего текста
                lines = prev_node.text.split('\n')
                if lines:
                    last_line = lines[-1]  # не strip() - важны пробелы
                    # Проверяем, содержит ли последняя строка заголовочные символы
                    # Может быть как "### " так и "## API: "
                    if re.search(r'^#{1,6}\s+.*?$', last_line) or re.match(r'^#{1,6}\s*$', last_line):
                        # Дополнительно проверяем, что предыдущий текст не заканчивается переводом строки
                        if not prev_node.text.endswith('\n'):
                            return True
        
        # Проверяем следующий узел - если там есть продолжение в той же строке
        if node_index + 1 < len(ast):
            next_node = ast[node_index + 1]
            if isinstance(next_node, TextNode):
                lines = next_node.text.split('\n')
                if lines:
                    first_line = lines[0]
                    # Если первая строка не начинается с перевода строки,
                    # значит плейсхолдер и следующий текст на одной строке
                    if first_line and not next_node.text.startswith('\n'):
                        # Дополнительная проверка - есть ли заголовочные символы в предыдущем узле
                        if node_index > 0:
                            prev_node = ast[node_index - 1]
                            if isinstance(prev_node, TextNode):
                                prev_lines = prev_node.text.split('\n')
                                if prev_lines and re.search(r'#{1,6}\s*$', prev_lines[-1]):
                                    return True
        
        return False
    
    def _find_parent_heading_level(self, placeholder_info: PlaceholderInfo, headings: List[HeadingInfo]) -> int:
        """
        Находит уровень ближайшего родительского заголовка.
        
        Args:
            placeholder_info: Информация о плейсхолдере
            headings: Список заголовков шаблона
            
        Returns:
            Уровень родительского заголовка (по умолчанию 1)
        """
        # Ищем последний заголовок перед плейсхолдером
        parent_level = 1  # По умолчанию считаем, что мы под H1
        
        for heading in headings:
            if heading.line_number < placeholder_info.line_number:
                parent_level = heading.level
            else:
                break
        
        return parent_level
    
    def _analyze_placeholder_chain(self, target_node: MarkdownFileNode, ast: TemplateAST, node_index: int, headings: List[HeadingInfo]) -> bool:
        """
        Анализирует, образуют ли плейсхолдеры непрерывную цепочку.
        
        Логика:
        - Если между соседними md-плейсхолдерами есть заголовки родительского шаблона,
          то они НЕ образуют цепочку
        - Если между ними только текст (без заголовков) или другие плейсхолдеры,
          то они образуют цепочку
        
        Args:
            target_node: Целевой узел плейсхолдера
            ast: AST шаблона
            node_index: Индекс узла в AST
            headings: Список заголовков шаблона
            
        Returns:
            True если плейсхолдеры образуют непрерывную цепочку
        """
        # Ищем другие md-плейсхолдеры поблизости
        md_placeholder_indices = []
        for i, node in enumerate(ast):
            if isinstance(node, MarkdownFileNode):
                md_placeholder_indices.append(i)
        
        if len(md_placeholder_indices) <= 1:
            # Для единственного плейсхолдера анализируем его окружение
            # Если плейсхолдер "окружен" заголовками (до и после), считаем его разделенным
            return self._is_single_placeholder_in_chain(target_node, ast, node_index, headings)
        
        current_index_in_chain = md_placeholder_indices.index(node_index)
        
        # Проверяем заголовки между соседними плейсхолдерами
        for i in range(len(md_placeholder_indices) - 1):
            start_idx = md_placeholder_indices[i]
            end_idx = md_placeholder_indices[i + 1]
            
            # Проверяем, есть ли заголовки между этими плейсхолдерами
            if self._has_headings_between_nodes(ast, start_idx, end_idx, headings):
                # Есть разделяющие заголовки - не цепочка
                return False
        
        return True
    
    def _has_headings_between_nodes(self, ast: TemplateAST, start_idx: int, end_idx: int, headings: List[HeadingInfo]) -> bool:
        """
        Проверяет наличие заголовков между двумя узлами AST.
        
        Args:
            ast: AST шаблона
            start_idx: Индекс начального узла
            end_idx: Индекс конечного узла
            headings: Список заголовков шаблона
            
        Returns:
            True если между узлами есть заголовки
        """
        # Вычисляем приблизительные позиции строк
        start_line = 0
        end_line = 0
        current_line = 0
        
        for i, node in enumerate(ast):
            if i == start_idx:
                start_line = current_line
            elif i == end_idx:
                end_line = current_line
                break
                
            if isinstance(node, TextNode):
                current_line += len(node.text.split('\n'))
            else:
                current_line += 1
        
        # Проверяем, есть ли заголовки в диапазоне
        for heading in headings:
            if start_line < heading.line_number < end_line:
                return True
        
        return False


    def _is_single_placeholder_in_chain(self, target_node: MarkdownFileNode, ast: TemplateAST, node_index: int, headings: List[HeadingInfo]) -> bool:
        """
        Анализирует, образует ли единственный плейсхолдер "цепочку" или разделен заголовками.
        
        Логика:
        - Если перед и после плейсхолдера есть заголовки того же или более высокого уровня,
          то плейсхолдер считается "разделенным" (не цепочка)
        - Иначе - цепочка
        
        Args:
            target_node: Целевой узел плейсхолдера
            ast: AST шаблона
            node_index: Индекс узла в AST
            headings: Список заголовков шаблона
            
        Returns:
            True если единственный плейсхолдер считается цепочкой
        """
        # Определяем позицию плейсхолдера
        placeholder_line = 0
        for i, node in enumerate(ast):
            if i == node_index:
                break
            if isinstance(node, TextNode):
                placeholder_line += len(node.text.split('\n'))
            else:
                placeholder_line += 1
        
        # Ищем заголовки до и после плейсхолдера
        headings_before = [h for h in headings if h.line_number < placeholder_line]
        headings_after = [h for h in headings if h.line_number > placeholder_line]
        
        # Если есть заголовки и до и после плейсхолдера
        if headings_before and headings_after:
            # Получаем последний заголовок перед и первый после
            last_before = headings_before[-1]
            first_after = headings_after[0]
            
            # Если заголовки одного уровня или выше родительского - плейсхолдер разделен
            parent_level = last_before.level
            if first_after.level <= parent_level:
                return False  # Разделен, не цепочка
        
        return True  # По умолчанию считаем цепочкой


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