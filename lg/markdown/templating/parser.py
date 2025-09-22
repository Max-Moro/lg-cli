"""
Парсер для условных конструкций в Markdown.

Преобразует токены HTML-комментариев в AST с поддержкой 
условных блоков и комментариев-инструкций.
"""

from __future__ import annotations

from typing import List, Optional

from .lexer import CommentToken, MarkdownTemplateLexer
from .nodes import (
    MarkdownAST, MarkdownNode, TextNode, ConditionalBlockNode,
    ElifBlockNode, ElseBlockNode, CommentBlockNode
)


class MarkdownTemplateParserError(Exception):
    """Ошибка синтаксического анализа Markdown с условными конструкциями."""
    
    def __init__(self, message: str, token: Optional[CommentToken] = None):
        if token:
            super().__init__(f"{message} в токене '{token.type}' на позиции {token.start_pos}")
        else:
            super().__init__(message)
        self.token = token


class MarkdownTemplateParser:
    """
    Парсер для Markdown с условными конструкциями в HTML-комментариях.
    
    Преобразует последовательность токенов комментариев и текстовых сегментов
    в AST, корректно обрабатывая вложенные условные конструкции.
    """
    
    def __init__(self, text: str):
        """
        Инициализирует парсер с исходным текстом.
        
        Args:
            text: Исходный Markdown-текст для парсинга
        """
        self.text = text
        self.lexer = MarkdownTemplateLexer(text)
        
    def parse(self) -> MarkdownAST:
        """
        Парсит текст в AST.
        
        Returns:
            AST с условными конструкциями
            
        Raises:
            MarkdownTemplateParserError: При ошибке синтаксического анализа
        """
        # Получаем токены комментариев
        tokens = self.lexer.tokenize()
        
        # Валидируем структуру токенов
        validation_errors = self.lexer.validate_tokens(tokens)
        if validation_errors:
            raise MarkdownTemplateParserError(
                f"Ошибки валидации структуры: {'; '.join(validation_errors)}"
            )
        
        # Если токенов нет, возвращаем простой текстовый узел
        if not tokens:
            return [TextNode(text=self.text)]
        
        # Парсим с учетом токенов
        return self._parse_with_tokens(tokens)
    
    def _parse_with_tokens(self, tokens: List[CommentToken]) -> MarkdownAST:
        """
        Парсит текст с учетом найденных токенов комментариев.
        
        Args:
            tokens: Список токенов комментариев
            
        Returns:
            Список узлов AST
        """
        ast = []
        current_pos = 0
        token_index = 0
        
        while token_index < len(tokens):
            token = tokens[token_index]
            
            # Добавляем текст перед токеном
            if current_pos < token.start_pos:
                text_content = self.text[current_pos:token.start_pos]
                if text_content:
                    ast.append(TextNode(text=text_content))
            
            # Обрабатываем токен
            if token.type == 'if':
                # Парсим условный блок
                if_block, consumed_tokens = self._parse_conditional_block(tokens, token_index)
                ast.append(if_block)
                token_index += consumed_tokens
                # Обновляем позицию на конец последнего обработанного токена
                if token_index < len(tokens):
                    current_pos = tokens[token_index - 1].end_pos
                else:
                    current_pos = tokens[-1].end_pos
            
            elif token.type == 'comment:start':
                # Парсим блок комментария
                comment_block, consumed_tokens = self._parse_comment_block(tokens, token_index)
                ast.append(comment_block)
                token_index += consumed_tokens
                # Обновляем позицию на конец последнего обработанного токена
                if token_index < len(tokens):
                    current_pos = tokens[token_index - 1].end_pos
                else:
                    current_pos = tokens[-1].end_pos
            
            else:
                # Неожиданный токен на верхнем уровне
                raise MarkdownTemplateParserError(
                    f"Неожиданный токен '{token.type}' на верхнем уровне", token
                )
        
        # Добавляем оставшийся текст
        if current_pos < len(self.text):
            remaining_text = self.text[current_pos:]
            if remaining_text:
                ast.append(TextNode(text=remaining_text))
        
        return ast
    
    def _parse_conditional_block(self, tokens: List[CommentToken], start_index: int) -> tuple[ConditionalBlockNode, int]:
        """
        Парсит условный блок if...elif...else...endif.
        
        Args:
            tokens: Список всех токенов
            start_index: Индекс токена 'if'
            
        Returns:
            Кортеж (узел условного блока, количество обработанных токенов)
        """
        if_token = tokens[start_index]
        if if_token.type != 'if':
            raise MarkdownTemplateParserError("Ожидался токен 'if'", if_token)
        
        # Ищем соответствующий endif
        endif_index = self._find_matching_endif(tokens, start_index)
        if endif_index == -1:
            raise MarkdownTemplateParserError("Не найден соответствующий 'endif'", if_token)
        
        # Парсим содержимое условного блока
        condition_text = if_token.content
        
        # Ищем elif и else токены внутри блока
        elif_indices = []
        else_index = -1
        
        for i in range(start_index + 1, endif_index):
            token = tokens[i]
            if token.type == 'elif' and self._is_at_same_level(tokens, start_index, i):
                elif_indices.append(i)
            elif token.type == 'else' and self._is_at_same_level(tokens, start_index, i):
                if else_index != -1:
                    raise MarkdownTemplateParserError("Множественные 'else' в одном блоке", token)
                else_index = i
        
        # Проверяем порядок elif и else
        if else_index != -1 and elif_indices:
            if any(ei > else_index for ei in elif_indices):
                else_token = tokens[else_index]
                raise MarkdownTemplateParserError("'elif' после 'else'", else_token)
        
        # Парсим тело if блока
        body_start = if_token.end_pos
        body_end = tokens[elif_indices[0]].start_pos if elif_indices else (
            tokens[else_index].start_pos if else_index != -1 else tokens[endif_index].start_pos
        )
        
        if_body = self._parse_body_between_positions(tokens, start_index + 1, body_start, body_end)
        
        # Парсим elif блоки
        elif_blocks = []
        for i, elif_idx in enumerate(elif_indices):
            elif_token = tokens[elif_idx]
            elif_body_start = elif_token.end_pos
            
            # Определяем конец тела elif блока
            next_idx = elif_indices[i + 1] if i + 1 < len(elif_indices) else (
                else_index if else_index != -1 else endif_index
            )
            elif_body_end = tokens[next_idx].start_pos
            
            elif_body = self._parse_body_between_positions(tokens, elif_idx + 1, elif_body_start, elif_body_end)
            
            elif_blocks.append(ElifBlockNode(
                condition_text=elif_token.content,
                body=elif_body
            ))
        
        # Парсим else блок
        else_block = None
        if else_index != -1:
            else_token = tokens[else_index]
            else_body_start = else_token.end_pos
            else_body_end = tokens[endif_index].start_pos
            
            else_body = self._parse_body_between_positions(tokens, else_index + 1, else_body_start, else_body_end)
            else_block = ElseBlockNode(body=else_body)
        
        conditional_block = ConditionalBlockNode(
            condition_text=condition_text,
            body=if_body,
            elif_blocks=elif_blocks,
            else_block=else_block
        )
        
        # Возвращаем узел и количество обработанных токенов
        consumed_tokens = endif_index - start_index + 1
        return conditional_block, consumed_tokens
    
    def _parse_comment_block(self, tokens: List[CommentToken], start_index: int) -> tuple[CommentBlockNode, int]:
        """
        Парсит блок комментария comment:start...comment:end.
        
        Args:
            tokens: Список всех токенов  
            start_index: Индекс токена 'comment:start'
            
        Returns:
            Кортеж (узел комментария, количество обработанных токенов)
        """
        start_token = tokens[start_index]
        if start_token.type != 'comment:start':
            raise MarkdownTemplateParserError("Ожидался токен 'comment:start'", start_token)
        
        # Ищем соответствующий comment:end
        end_index = -1
        for i in range(start_index + 1, len(tokens)):
            if tokens[i].type == 'comment:end':
                end_index = i
                break
        
        if end_index == -1:
            raise MarkdownTemplateParserError("Не найден соответствующий 'comment:end'", start_token)
        
        # Извлекаем текст комментария
        comment_start = start_token.end_pos
        comment_end = tokens[end_index].start_pos
        comment_text = self.text[comment_start:comment_end]
        
        comment_block = CommentBlockNode(text=comment_text)
        
        consumed_tokens = end_index - start_index + 1
        return comment_block, consumed_tokens
    
    def _parse_body_between_positions(self, all_tokens: List[CommentToken], 
                                    start_token_index: int, start_pos: int, end_pos: int) -> List[MarkdownNode]:
        """
        Парсит тело между указанными позициями в тексте.
        
        Args:
            all_tokens: Все токены документа
            start_token_index: Индекс начального токена (для определения уровня вложенности)
            start_pos: Начальная позиция в тексте
            end_pos: Конечная позиция в тексте
            
        Returns:
            Список узлов для тела
        """
        # Фильтруем токены, которые попадают в диапазон
        relevant_tokens = [
            token for token in all_tokens 
            if start_pos <= token.start_pos < end_pos
        ]
        
        if not relevant_tokens:
            # Если токенов в диапазоне нет, возвращаем просто текст
            body_text = self.text[start_pos:end_pos]
            return [TextNode(text=body_text)] if body_text else []
        
        # Создаем временный парсер для этого фрагмента
        body_text = self.text[start_pos:end_pos]
        
        # Корректируем позиции токенов относительно начала фрагмента
        adjusted_tokens = []
        for token in relevant_tokens:
            adjusted_token = CommentToken(
                type=token.type,
                content=token.content,
                start_pos=token.start_pos - start_pos,
                end_pos=token.end_pos - start_pos,
                full_match=token.full_match
            )
            adjusted_tokens.append(adjusted_token)
        
        # Создаем временный парсер
        temp_parser = MarkdownTemplateParser(body_text)
        return temp_parser._parse_with_tokens(adjusted_tokens)
    
    def _find_matching_endif(self, tokens: List[CommentToken], if_index: int) -> int:
        """
        Находит соответствующий endif для if токена.
        
        Args:
            tokens: Список токенов
            if_index: Индекс if токена
            
        Returns:
            Индекс соответствующего endif или -1 если не найден
        """
        if_count = 1  # Начинаем с 1 для текущего if
        
        for i in range(if_index + 1, len(tokens)):
            token = tokens[i]
            if token.type == 'if':
                if_count += 1
            elif token.type == 'endif':
                if_count -= 1
                if if_count == 0:
                    return i
        
        return -1
    
    def _is_at_same_level(self, tokens: List[CommentToken], if_index: int, target_index: int) -> bool:
        """
        Проверяет, находится ли токен на том же уровне вложенности что и if.
        
        Args:
            tokens: Список токенов
            if_index: Индекс if токена
            target_index: Индекс проверяемого токена
            
        Returns:
            True если токены на одном уровне
        """
        if_count = 1  # Начинаем с 1 для исходного if
        
        for i in range(if_index + 1, target_index):
            token = tokens[i]
            if token.type == 'if':
                if_count += 1
            elif token.type == 'endif':
                if_count -= 1
        
        return if_count == 1


def parse_markdown_template(text: str) -> MarkdownAST:
    """
    Удобная функция для парсинга Markdown с условными конструкциями.
    
    Args:
        text: Исходный Markdown-текст
        
    Returns:
        AST с условными конструкциями
        
    Raises:
        MarkdownTemplateParserError: При ошибке синтаксического анализа
    """
    parser = MarkdownTemplateParser(text)
    return parser.parse()


__all__ = [
    "MarkdownTemplateParser",
    "MarkdownTemplateParserError",
    "parse_markdown_template"
]