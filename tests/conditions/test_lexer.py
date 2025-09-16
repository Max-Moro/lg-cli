"""
Тесты для лексера условий.
"""

import pytest

from lg.conditions.lexer import ConditionLexer, Token


class TestConditionLexer:
    
    def setup_method(self):
        self.lexer = ConditionLexer()
    
    def test_empty_string(self):
        """Тест токенизации пустой строки"""
        tokens = self.lexer.tokenize("")
        assert len(tokens) == 1
        assert tokens[0].type == 'EOF'
    
    def test_whitespace_ignored(self):
        """Тест игнорирования пробелов"""
        tokens = self.lexer.tokenize("   \t  ")
        assert len(tokens) == 1
        assert tokens[0].type == 'EOF'
    
    def test_keywords(self):
        """Тест распознавания ключевых слов"""
        test_cases = [
            "tag", "TAGSET", "scope", "AND", "OR", "NOT"
        ]
        
        for keyword in test_cases:
            tokens = self.lexer.tokenize(keyword)
            assert len(tokens) == 2  # keyword + EOF
            assert tokens[0].type == 'KEYWORD'
            assert tokens[0].value == keyword
            assert tokens[1].type == 'EOF'
    
    def test_symbols(self):
        """Тест распознавания символов"""
        test_cases = ["(", ")", ":"]
        
        for symbol in test_cases:
            tokens = self.lexer.tokenize(symbol)
            assert len(tokens) == 2  # symbol + EOF
            assert tokens[0].type == 'SYMBOL'
            assert tokens[0].value == symbol
            assert tokens[1].type == 'EOF'
    
    def test_identifiers(self):
        """Тест распознавания идентификаторов"""
        test_cases = [
            "python", "test_tag", "my-tag", "Tag123", "_private", "x"
        ]
        
        for identifier in test_cases:
            tokens = self.lexer.tokenize(identifier)
            assert len(tokens) == 2  # identifier + EOF
            assert tokens[0].type == 'IDENTIFIER'
            assert tokens[0].value == identifier
            assert tokens[1].type == 'EOF'
    
    def test_simple_tag_condition(self):
        """Тест простого условия тега"""
        tokens = self.lexer.tokenize("tag:python")
        
        expected = [
            Token('KEYWORD', 'tag', 0),
            Token('SYMBOL', ':', 3),
            Token('IDENTIFIER', 'python', 4),
            Token('EOF', '', 10)
        ]
        
        assert len(tokens) == len(expected)
        for actual, expected_token in zip(tokens, expected):
            assert actual.type == expected_token.type
            assert actual.value == expected_token.value
    
    def test_tagset_condition(self):
        """Тест условия набора тегов"""
        tokens = self.lexer.tokenize("TAGSET:language:python")
        
        expected_types = ['KEYWORD', 'SYMBOL', 'IDENTIFIER', 'SYMBOL', 'IDENTIFIER', 'EOF']
        expected_values = ['TAGSET', ':', 'language', ':', 'python', '']
        
        assert len(tokens) == len(expected_types)
        for i, token in enumerate(tokens):
            assert token.type == expected_types[i]
            assert token.value == expected_values[i]
    
    def test_complex_expression(self):
        """Тест сложного выражения с несколькими операторами"""
        tokens = self.lexer.tokenize("tag:python AND (NOT tag:deprecated OR scope:local)")
        
        expected_types = [
            'KEYWORD', 'SYMBOL', 'IDENTIFIER',  # tag:python
            'KEYWORD',                           # AND
            'SYMBOL',                            # (
            'KEYWORD',                           # NOT
            'KEYWORD', 'SYMBOL', 'IDENTIFIER',  # tag:deprecated
            'KEYWORD',                           # OR
            'KEYWORD', 'SYMBOL', 'IDENTIFIER',  # scope:local
            'SYMBOL',                            # )
            'EOF'
        ]
        
        assert len(tokens) == len(expected_types)
        for i, token in enumerate(tokens):
            assert token.type == expected_types[i]
    
    def test_positions(self):
        """Тест правильности позиций токенов"""
        tokens = self.lexer.tokenize("tag:test")
        
        assert tokens[0].position == 0  # tag
        assert tokens[1].position == 3  # :
        assert tokens[2].position == 4  # test
        assert tokens[3].position == 8  # EOF
    
    def test_positions_with_whitespace(self):
        """Тест позиций с учетом пробелов"""
        tokens = self.lexer.tokenize("  tag  :  test  ")
        
        # Пробелы игнорируются, но позиции должны быть правильными
        assert tokens[0].type == 'KEYWORD'
        assert tokens[0].value == 'tag'
        assert tokens[0].position == 2
        
        assert tokens[1].type == 'SYMBOL'
        assert tokens[1].value == ':'
        assert tokens[1].position == 7
        
        assert tokens[2].type == 'IDENTIFIER'
        assert tokens[2].value == 'test'
        assert tokens[2].position == 10
    
    def test_unknown_character_error(self):
        """Тест обработки неизвестных символов"""
        with pytest.raises(ValueError, match="Unexpected character"):
            self.lexer.tokenize("tag@invalid")
    
    def test_case_sensitivity(self):
        """Тест чувствительности к регистру"""
        # Ключевые слова должны быть точными
        tokens = self.lexer.tokenize("Tag")
        assert tokens[0].type == 'IDENTIFIER'  # не KEYWORD
        
        tokens = self.lexer.tokenize("and")
        assert tokens[0].type == 'IDENTIFIER'  # не KEYWORD (должно быть AND)
    
    def test_token_stream(self):
        """Тест генератора токенов"""
        token_stream = list(self.lexer.tokenize_stream("tag:python"))
        tokens_list = self.lexer.tokenize("tag:python")
        
        assert len(token_stream) == len(tokens_list)
        for stream_token, list_token in zip(token_stream, tokens_list):
            assert stream_token.type == list_token.type
            assert stream_token.value == list_token.value
            assert stream_token.position == list_token.position