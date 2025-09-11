"""
Literal optimization.
Processes and trims literal data (strings, arrays, objects).
"""

from __future__ import annotations

import re
from typing import Tuple, Optional, cast

from ..context import ProcessingContext
from ..tree_sitter_support import Node


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
    
    def _trim_literal(
        self, 
        context: ProcessingContext, 
        node: Node, 
        capture_name: str, 
        literal_text: str, 
        max_tokens: int
    ) -> None:
        """
        Урезает литерал с корректным закрытием и добавляет комментарий.
        
        Args:
            context: Контекст обработки
            node: Узел литерала
            capture_name: Тип захвата (string, array, object)
            literal_text: Исходный текст литерала
            max_tokens: Максимальный размер в токенах
        """
        # Определяем тип литерала и корректные границы
        literal_type, opening, closing = self._analyze_literal_type(literal_text, capture_name)
        
        # Вычисляем сколько места оставить для содержимого
        # Резервируем место для открывающих/закрывающих символов и многоточия
        overhead_text = f"{opening}...{closing}"
        overhead_tokens = context.tokenizer.count_text(overhead_text)
        content_token_budget = max(1, max_tokens - overhead_tokens)
        
        # Извлекаем содержимое без границ
        content = self._extract_content(literal_text, opening, closing)
        
        # Урезаем содержимое до бюджета токенов
        trimmed_content = self._trim_content_to_tokens(context, content, content_token_budget)
        
        # Формируем урезанный литерал
        trimmed_literal = f"{opening}{trimmed_content}...{closing}"
        
        # Создаем комментарий о урезании
        comment_style = self.adapter.get_comment_style()
        single_comment = comment_style[0]
        original_tokens = context.tokenizer.count_text(literal_text)
        saved_tokens = original_tokens - context.tokenizer.count_text(trimmed_literal)
        
        # Формируем комментарий
        comment = f" {single_comment} … literal {literal_type} (−{saved_tokens} tokens)"
        
        # Применяем замену
        start_byte, end_byte = context.doc.get_node_range(node)
        replacement = f"{trimmed_literal}{comment}"
        
        context.editor.add_replacement(
            start_byte, end_byte, replacement,
            edit_type="literal_trimmed"
        )
        
        # Обновляем метрики
        context.metrics.mark_element_removed("literal")
        context.metrics.add_bytes_saved(len(literal_text.encode('utf-8')) - len(replacement.encode('utf-8')))
    
    def _analyze_literal_type(self, literal_text: str, capture_name: str) -> Tuple[str, str, str]:
        """
        Анализирует тип литерала и определяет открывающие/закрывающие символы.
        
        Args:
            literal_text: Текст литерала
            capture_name: Тип захвата из Tree-sitter
            
        Returns:
            Tuple (тип_литерала, открывающий_символ, закрывающий_символ)
        """
        stripped = literal_text.strip()
        
        if capture_name == "string":
            # Строки: обрабатываем различные виды кавычек
            if stripped.startswith('"""') or stripped.startswith("'''"):
                # Python triple quotes
                quote = stripped[:3]
                return "string", quote, quote
            elif stripped.startswith('`'):
                # Template strings (TypeScript)
                return "string", "`", "`"
            elif stripped.startswith('"'):
                return "string", '"', '"'
            elif stripped.startswith("'"):
                return "string", "'", "'"
            else:
                # Fallback
                return "string", '"', '"'
        
        elif capture_name in ("array", "list"):
            # Массивы/списки
            if stripped.startswith('['):
                return "array", "[", "]"
            elif stripped.startswith('(') and stripped.endswith(')'):
                # Tuple в Python
                return "tuple", "(", ")"
            else:
                return "array", "[", "]"
        
        elif capture_name in ("object", "dictionary"):
            # Объекты/словари
            return "object", "{", "}"
        
        else:
            # Универсальный fallback
            if stripped.startswith('['):
                return "array", "[", "]"
            elif stripped.startswith('{'):
                return "object", "{", "}"
            elif stripped.startswith('('):
                return "tuple", "(", ")"
            else:
                return "literal", "", ""
    
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
    
    def _trim_content_to_tokens(self, context: ProcessingContext, content: str, token_budget: int) -> str:
        """
        Урезает содержимое до указанного количества токенов.
        
        Args:
            context: Контекст обработки
            content: Содержимое для урезания
            token_budget: Бюджет токенов
            
        Returns:
            Урезанное содержимое
        """
        if not content:
            return ""
        
        # Если содержимое уже помещается в бюджет
        current_tokens = context.tokenizer.count_text(content)
        if current_tokens <= token_budget:
            return content
        
        # Ищем подходящую точку обрезания
        # Используем бинарный поиск для эффективности
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
        
        trimmed = content[:best_end]
        
        # Стараемся обрезать по границам слов/элементов для лучшей читаемости
        return self._smart_trim_at_boundary(trimmed)
    
    def _smart_trim_at_boundary(self, text: str) -> str:
        """
        Умное обрезание по границам слов/элементов.
        
        Args:
            text: Текст для обрезания
            
        Returns:
            Обрезанный текст по разумной границе
        """
        if not text:
            return text
        
        # Убираем trailing whitespace
        text = text.rstrip()
        
        # Для структурированных данных ищем границы элементов
        boundaries = [',', ';', '\n', ' ', '\t']
        
        # Ищем последнюю границу в последних 20% текста для лучшего результата
        search_start = max(0, len(text) - len(text) // 5)
        
        for i in range(len(text) - 1, search_start - 1, -1):
            if text[i] in boundaries:
                candidate = text[:i].rstrip()
                if candidate:  # Убеждаемся что не получили пустую строку
                    return candidate
        
        # Если границу не нашли, возвращаем как есть
        return text

