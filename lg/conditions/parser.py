"""
Парсер условных выражений с рекурсивным спуском.

Строит абстрактное синтаксическое дерево (AST) из последовательности токенов.
Поддерживает приоритеты операторов и группировку в скобках.

Грамматика:
expression     → or_expression
or_expression  → and_expression ("OR" and_expression)*
and_expression → not_expression ("AND" not_expression)*
not_expression → "NOT" not_expression | primary
primary        → tag_condition | tagset_condition | scope_condition | "(" expression ")"

tag_condition    → "tag" ":" IDENTIFIER
tagset_condition → "TAGSET" ":" IDENTIFIER ":" IDENTIFIER  
scope_condition  → "scope" ":" IDENTIFIER
"""

from __future__ import annotations

from typing import List

from .lexer import ConditionLexer, Token
from .model import (
    Condition,
    ConditionType,
    TagCondition,
    TagSetCondition,
    ScopeCondition,
    GroupCondition,
    NotCondition,
    BinaryCondition,
)


class ParseError(Exception):
    """Ошибка парсинга условного выражения."""
    
    def __init__(self, message: str, position: int):
        self.message = message
        self.position = position
        super().__init__(f"Parse error at position {position}: {message}")


class ConditionParser:
    """
    Парсер условных выражений с рекурсивным спуском.
    
    Преобразует список токенов в абстрактное синтаксическое дерево,
    соблюдая приоритеты операторов и правила группировки.
    """
    
    def __init__(self):
        self.lexer = ConditionLexer()
        self._tokens: List[Token] = []
        self._position = 0
    
    def parse(self, condition_str: str) -> Condition:
        """
        Парсит строку условия в AST.
        
        Args:
            condition_str: Строка условного выражения
            
        Returns:
            Корневой узел AST
            
        Raises:
            ParseError: При синтаксической ошибке
            ValueError: При ошибке токенизации
        """
        self._tokens = self.lexer.tokenize(condition_str)
        self._position = 0
        
        if not self._tokens or (len(self._tokens) == 1 and self._tokens[0].type == 'EOF'):
            raise ParseError("Empty condition", 0)
        
        result = self._parse_expression()
        
        # Проверяем, что мы достигли конца входных данных
        if not self._is_at_end():
            current = self._current_token()
            raise ParseError(f"Unexpected token '{current.value}'", current.position)
        
        return result
    
    def _parse_expression(self) -> Condition:
        """Парсит полное выражение (начальный символ грамматики)."""
        return self._parse_or_expression()
    
    def _parse_or_expression(self) -> Condition:
        """Парсит выражение с оператором OR (низший приоритет)."""
        left = self._parse_and_expression()
        
        while self._match_keyword("OR"):
            right = self._parse_and_expression()
            left = BinaryCondition(left=left, right=right, operator=ConditionType.OR)
        
        return left
    
    def _parse_and_expression(self) -> Condition:
        """Парсит выражение с оператором AND (средний приоритет)."""
        left = self._parse_not_expression()
        
        while self._match_keyword("AND"):
            right = self._parse_not_expression()
            left = BinaryCondition(left=left, right=right, operator=ConditionType.AND)
        
        return left
    
    def _parse_not_expression(self) -> Condition:
        """Парсит выражение с оператором NOT (высокий приоритет)."""
        if self._match_keyword("NOT"):
            condition = self._parse_not_expression()  # Правая ассоциативность для NOT
            return NotCondition(condition=condition)
        
        return self._parse_primary()
    
    def _parse_primary(self) -> Condition:
        """Парсит первичное выражение (атомарные условия и группы в скобках)."""
        # Группировка в скобках
        if self._match_symbol("("):
            expr = self._parse_expression()
            if not self._match_symbol(")"):
                raise ParseError("Expected ')' after grouped expression", self._current_position())
            return GroupCondition(condition=expr)
        
        # tag:name
        if self._match_keyword("tag"):
            return self._parse_tag_condition()
        
        # TAGSET:set:tag
        if self._match_keyword("TAGSET"):
            return self._parse_tagset_condition()
        
        # scope:type
        if self._match_keyword("scope"):
            return self._parse_scope_condition()
        
        # Если ничего не подошло, это ошибка
        current = self._current_token()
        if current.type == 'EOF':
            raise ParseError("Unexpected end of expression", current.position)
        else:
            raise ParseError(f"Unexpected token '{current.value}'", current.position)
    
    def _parse_tag_condition(self) -> TagCondition:
        """Парсит условие тега: tag:name"""
        if not self._match_symbol(":"):
            raise ParseError("Expected ':' after 'tag'", self._current_position())
        
        name_token = self._consume_identifier("Expected tag name after 'tag:'")
        return TagCondition(name=name_token.value)
    
    def _parse_tagset_condition(self) -> TagSetCondition:
        """Парсит условие набора тегов: TAGSET:set:tag"""
        if not self._match_symbol(":"):
            raise ParseError("Expected ':' after 'TAGSET'", self._current_position())
        
        set_name_token = self._consume_identifier("Expected set name after 'TAGSET:'")
        
        if not self._match_symbol(":"):
            raise ParseError("Expected ':' after set name", self._current_position())
        
        tag_name_token = self._consume_identifier("Expected tag name after set name")
        
        return TagSetCondition(set_name=set_name_token.value, tag_name=tag_name_token.value)
    
    def _parse_scope_condition(self) -> ScopeCondition:
        """Парсит условие скоупа: scope:type"""
        if not self._match_symbol(":"):
            raise ParseError("Expected ':' after 'scope'", self._current_position())
        
        type_token = self._consume_identifier("Expected scope type after 'scope:'")
        
        # Валидируем тип скоупа
        if type_token.value not in ("local", "parent"):
            raise ParseError(
                f"Invalid scope type '{type_token.value}'. Expected 'local' or 'parent'",
                type_token.position
            )
        
        return ScopeCondition(scope_type=type_token.value)
    
    # Вспомогательные методы для работы с токенами
    
    def _current_token(self) -> Token:
        """Возвращает текущий токен без продвижения позиции."""
        if self._position >= len(self._tokens):
            # Возвращаем EOF если вышли за границы
            return Token(type='EOF', value='', position=len(self._tokens))
        return self._tokens[self._position]
    
    def _current_position(self) -> int:
        """Возвращает текущую позицию в исходной строке."""
        return self._current_token().position
    
    def _is_at_end(self) -> bool:
        """Проверяет, достигли ли мы конца токенов."""
        return self._current_token().type == 'EOF'
    
    def _advance(self) -> Token:
        """Продвигает позицию и возвращает предыдущий токен."""
        if not self._is_at_end():
            self._position += 1
        return self._tokens[self._position - 1] if self._position > 0 else self._current_token()
    
    def _match_keyword(self, keyword: str) -> bool:
        """Проверяет и потребляет ключевое слово."""
        current = self._current_token()
        if current.type == 'KEYWORD' and current.value == keyword:
            self._advance()
            return True
        return False
    
    def _match_symbol(self, symbol: str) -> bool:
        """Проверяет и потребляет символ."""
        current = self._current_token()
        if current.type == 'SYMBOL' and current.value == symbol:
            self._advance()
            return True
        return False
    
    def _consume_identifier(self, error_message: str) -> Token:
        """Потребляет идентификатор или выбрасывает ошибку."""
        current = self._current_token()
        if current.type == 'IDENTIFIER':
            return self._advance()
        
        raise ParseError(error_message, current.position)