"""
Процессор для обработки Markdown с условными конструкциями.

Объединяет лексер, парсер и оценщик условий для полной обработки
Markdown-документов с LG-инструкциями в HTML-комментариях.
"""

from __future__ import annotations

from typing import Tuple, Optional

from .nodes import (
    MarkdownAST, MarkdownNode, TextNode, ConditionalBlockNode,
    CommentBlockNode, RawBlockNode
)
from .parser import parse_markdown_template, MarkdownTemplateParserError


class MarkdownTemplateProcessorError(Exception):
    """Ошибка обработки Markdown с условными конструкциями."""
    
    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message)
        self.cause = cause


class MarkdownTemplateProcessor:
    """
    Процессор для Markdown с условными конструкциями.
    
    Выполняет полный цикл обработки: лексический анализ, парсинг,
    оценка условий и генерация итогового текста.
    """
    
    def __init__(self, template_ctx=None):
        """
        Инициализирует процессор.
        
        Args:
            template_ctx: Контекст шаблона для оценки условий (опционально)
        """
        self.template_ctx = template_ctx
    
    def process(self, text: str) -> Tuple[str, dict]:
        """
        Обрабатывает Markdown-текст с условными конструкциями.
        
        Args:
            text: Исходный Markdown-текст
            
        Returns:
            Кортеж (обработанный_текст, метаданные)
            
        Raises:
            MarkdownTemplateProcessorError: При ошибке обработки
        """
        try:
            # 1. Парсим текст в AST
            ast = parse_markdown_template(text)
            
            # 2. Оцениваем условия и генерируем результат
            processed_text = self._evaluate_ast(ast)
            
            # 3. Собираем метаданные
            meta = self._collect_metadata(ast)
            
            return processed_text, meta
            
        except MarkdownTemplateParserError as e:
            raise MarkdownTemplateProcessorError(f"Ошибка парсинга: {e}", e)
        except Exception as e:
            raise MarkdownTemplateProcessorError(f"Неожиданная ошибка обработки: {e}", e)
    
    def _evaluate_ast(self, ast: MarkdownAST) -> str:
        """
        Оценивает AST и генерирует итоговый текст.
        
        Args:
            ast: AST для оценки
            
        Returns:
            Итоговый обработанный текст
        """
        result_parts = []
        
        for node in ast:
            result_parts.append(self._evaluate_node(node))
        
        return "".join(result_parts)
    
    def _evaluate_node(self, node: MarkdownNode) -> str:
        """
        Оценивает один узел AST.
        
        Args:
            node: Узел для оценки
            
        Returns:
            Текстовое представление узла
        """
        if isinstance(node, TextNode):
            return node.text
        
        elif isinstance(node, ConditionalBlockNode):
            return self._evaluate_conditional_block(node)
        
        elif isinstance(node, CommentBlockNode):
            # Комментарии удаляются при обработке
            return ""
        
        elif isinstance(node, RawBlockNode):
            # Raw-блоки выводятся как есть без обработки
            return node.text
        
        else:
            # Неизвестный тип узла - возвращаем как есть
            return f"<!-- Unknown node type: {type(node).__name__} -->"
    
    def _evaluate_conditional_block(self, node: ConditionalBlockNode) -> str:
        """
        Оценивает условный блок.
        
        Args:
            node: Узел условного блока
            
        Returns:
            Текст соответствующей ветки условия или пустая строка
        """
        # Оцениваем основное условие
        if self._evaluate_condition(node.condition_text):
            return self._evaluate_ast(node.body)
        
        # Проверяем elif блоки по порядку
        if node.elif_blocks:
            for elif_block in node.elif_blocks:
                if self._evaluate_condition(elif_block.condition_text):
                    return self._evaluate_ast(elif_block.body)
        
        # Если ни одно условие не выполнилось, проверяем else блок
        if node.else_block:
            return self._evaluate_ast(node.else_block.body)
        
        return ""
    
    def _evaluate_condition(self, condition_text: str) -> bool:
        """
        Оценивает текстовое условие.
        
        Args:
            condition_text: Текст условия для оценки
            
        Returns:
            Результат оценки условия
        """
        if not condition_text:
            return False
        
        if self.template_ctx is None:
            # Если контекст шаблона не задан, возвращаем False для всех условий
            return False
        
        try:
            # Используем оценщик условий из контекста шаблона
            return self.template_ctx.evaluate_condition_text(condition_text)
        except Exception:
            # При ошибке оценки условия возвращаем False
            return False
    
    def _collect_metadata(self, ast: MarkdownAST) -> dict:
        """
        Собирает метаданные обработки.
        
        Args:
            ast: AST для анализа
            
        Returns:
            Словарь метаданных
        """
        meta = {
            "md.templating.processed": True,
            "md.templating.conditional_blocks": 0,
            "md.templating.comment_blocks": 0,
            "md.templating.conditions_evaluated": 0,
            "md.templating.conditions_true": 0
        }
        
        def analyze_node(node: MarkdownNode) -> None:
            if isinstance(node, ConditionalBlockNode):
                meta["md.templating.conditional_blocks"] += 1
                
                # Анализируем основное условие
                if node.condition_text:
                    meta["md.templating.conditions_evaluated"] += 1
                    if self._evaluate_condition(node.condition_text):
                        meta["md.templating.conditions_true"] += 1
                
                # Анализируем elif условия
                if node.elif_blocks:
                    for elif_block in node.elif_blocks:
                        if elif_block.condition_text:
                            meta["md.templating.conditions_evaluated"] += 1
                            if self._evaluate_condition(elif_block.condition_text):
                                meta["md.templating.conditions_true"] += 1
                
                # Рекурсивно анализируем содержимое
                for child in node.body:
                    analyze_node(child)
                if node.elif_blocks:
                    for elif_block in node.elif_blocks:
                        for child in elif_block.body:
                            analyze_node(child)
                if node.else_block:
                    for child in node.else_block.body:
                        analyze_node(child)
            
            elif isinstance(node, CommentBlockNode):
                meta["md.templating.comment_blocks"] += 1
            
            elif isinstance(node, RawBlockNode):
                # Raw-блоки не считаем отдельно, но можем добавить метрику если нужно
                pass
        
        for node in ast:
            analyze_node(node)
        
        return meta


def process_markdown_template(text: str, template_ctx=None) -> Tuple[str, dict]:
    """
    Удобная функция для обработки Markdown с условными конструкциями.
    
    Args:
        text: Исходный Markdown-текст
        template_ctx: Контекст шаблона для оценки условий (опционально)
        
    Returns:
        Кортеж (обработанный_текст, метаданные)
        
    Raises:
        MarkdownTemplateProcessorError: При ошибке обработки
    """
    processor = MarkdownTemplateProcessor(template_ctx)
    return processor.process(text)


__all__ = [
    "MarkdownTemplateProcessor",
    "MarkdownTemplateProcessorError", 
    "process_markdown_template"
]