"""
Тесты для лексического анализатора движка шаблонизации.

Проверяет корректную токенизацию всех элементов шаблонов:
- обычный текст
- плейсхолдеры ${...}
- директивы {% ... %}
- комментарии {# ... #}
- специальные символы и операторы
"""

import pytest
from lg.template.lexer import (
    TemplateLexer, 
    TokenType, 
    Token, 
    LexerError,
    tokenize_template
)


class TestTemplateLexer:
    """Тесты для базовой функциональности лексера."""
    
    def test_empty_template(self):
        """Пустой шаблон должен возвращать только EOF токен."""
        lexer = TemplateLexer("")
        tokens = lexer.tokenize()
        
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF
        assert tokens[0].value == ""
        assert tokens[0].position == 0
        assert tokens[0].line == 1
        assert tokens[0].column == 1

    def test_plain_text(self):
        """Обычный текст должен токенизироваться как TEXT."""
        text = "Hello, world!"
        lexer = TemplateLexer(text)
        tokens = lexer.tokenize()
        
        assert len(tokens) == 2  # TEXT + EOF
        assert tokens[0].type == TokenType.TEXT
        assert tokens[0].value == text
        assert tokens[0].position == 0
        assert tokens[0].line == 1
        assert tokens[0].column == 1
        assert tokens[1].type == TokenType.EOF

    def test_multiline_text(self):
        """Многострочный текст должен корректно обрабатывать позиции."""
        text = "Line 1\nLine 2\nLine 3"
        lexer = TemplateLexer(text)
        tokens = lexer.tokenize()
        
        assert len(tokens) == 2  # TEXT + EOF
        assert tokens[0].type == TokenType.TEXT
        assert tokens[0].value == text
        # EOF должен быть в правильной позиции
        assert tokens[1].line == 3
        assert tokens[1].column == 7  # После "Line 3"

    def test_simple_placeholder(self):
        """Простой плейсхолдер ${section}."""
        text = "${section}"
        lexer = TemplateLexer(text)
        tokens = lexer.tokenize()
        
        expected_types = [
            TokenType.PLACEHOLDER_START,
            TokenType.IDENTIFIER,  # "section" внутри плейсхолдера теперь токенизируется как IDENTIFIER
            TokenType.PLACEHOLDER_END,
            TokenType.EOF
        ]
        
        assert len(tokens) == len(expected_types)
        for token, expected_type in zip(tokens, expected_types):
            assert token.type == expected_type
        
        # Проверяем, что значение идентификатора корректно
        assert tokens[1].value == "section"

    def test_directive_tokens(self):
        """Директивы {% ... %} должны правильно токенизироваться."""
        text = "{% if condition %}"
        lexer = TemplateLexer(text)
        tokens = lexer.tokenize()
        
        expected_types = [
            TokenType.DIRECTIVE_START,
            TokenType.TEXT,  # " if condition "
            TokenType.DIRECTIVE_END,
            TokenType.EOF
        ]
        
        assert len(tokens) == len(expected_types)
        for token, expected_type in zip(tokens, expected_types):
            assert token.type == expected_type

    def test_comment_tokens(self):
        """Комментарии {# ... #} должны правильно токенизироваться."""
        text = "{# This is a comment #}"
        lexer = TemplateLexer(text)
        tokens = lexer.tokenize()
        
        expected_types = [
            TokenType.COMMENT_START,
            TokenType.TEXT,  # " This is a comment "
            TokenType.COMMENT_END,
            TokenType.EOF
        ]
        
        assert len(tokens) == len(expected_types)
        for token, expected_type in zip(tokens, expected_types):
            assert token.type == expected_type

    def test_mixed_content(self):
        """Смешанный контент с текстом, плейсхолдерами и директивами."""
        text = "Hello ${name}!\n{% if greeting %}\nWelcome!\n{% endif %}"
        lexer = TemplateLexer(text)
        tokens = lexer.tokenize()
        
        # Проверяем, что получили корректную последовательность токенов
        types = [token.type for token in tokens]
        
        # Ожидаем: TEXT, PLACEHOLDER_START, TEXT, PLACEHOLDER_END, TEXT, 
        #          DIRECTIVE_START, TEXT, DIRECTIVE_END, TEXT,
        #          DIRECTIVE_START, TEXT, DIRECTIVE_END, EOF
        assert TokenType.TEXT in types
        assert TokenType.PLACEHOLDER_START in types
        assert TokenType.PLACEHOLDER_END in types
        assert TokenType.DIRECTIVE_START in types
        assert TokenType.DIRECTIVE_END in types
        assert types[-1] == TokenType.EOF

    def test_nested_braces(self):
        """Вложенные скобки внутри плейсхолдеров или директив."""
        text = "${func(arg)}"
        lexer = TemplateLexer(text)
        tokens = lexer.tokenize()
        
        expected_types = [
            TokenType.PLACEHOLDER_START,
            TokenType.IDENTIFIER,  # "func"
            TokenType.LPAREN,      # "("  
            TokenType.IDENTIFIER,  # "arg"
            TokenType.RPAREN,      # ")"
            TokenType.PLACEHOLDER_END,
            TokenType.EOF
        ]
        
        assert len(tokens) == len(expected_types)
        for token, expected_type in zip(tokens, expected_types):
            assert token.type == expected_type
            
        # Проверяем значения ключевых токенов
        assert tokens[1].value == "func"
        assert tokens[3].value == "arg"

    def test_escaped_sequences(self):
        """Проверка обработки последовательностей, похожих на специальные."""
        text = "This $ is not a placeholder and % neither"
        lexer = TemplateLexer(text)
        tokens = lexer.tokenize()
        
        assert len(tokens) == 2  # TEXT + EOF
        assert tokens[0].type == TokenType.TEXT
        assert tokens[0].value == text

    def test_position_tracking(self):
        """Проверка корректного отслеживания позиций в тексте."""
        text = "Line 1\n${var}\nLine 3"
        lexer = TemplateLexer(text)
        tokens = lexer.tokenize()
        
        # Проверяем позиции ключевых токенов
        placeholder_start = None
        placeholder_end = None
        
        for token in tokens:
            if token.type == TokenType.PLACEHOLDER_START:
                placeholder_start = token
            elif token.type == TokenType.PLACEHOLDER_END:
                placeholder_end = token
        
        assert placeholder_start is not None
        assert placeholder_start.line == 2
        assert placeholder_start.column == 1
        
        assert placeholder_end is not None
        assert placeholder_end.line == 2
        assert placeholder_end.column == 6  # После "${var"


class TestPlaceholderContentTokenization:
    """Тесты для токенизации содержимого плейсхолдеров."""
    
    def test_simple_identifier(self):
        """Простой идентификатор в плейсхолдере."""
        lexer = TemplateLexer("")
        tokens = lexer.tokenize_placeholder_content("section")
        
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].value == "section"

    def test_colon_separated(self):
        """Идентификаторы с разделителями двоеточия."""
        lexer = TemplateLexer("")
        tokens = lexer.tokenize_placeholder_content("tpl:name")
        
        expected_types = [TokenType.IDENTIFIER, TokenType.COLON, TokenType.IDENTIFIER]
        assert len(tokens) == len(expected_types)
        for token, expected_type in zip(tokens, expected_types):
            assert token.type == expected_type
        
        assert tokens[0].value == "tpl"
        assert tokens[1].value == ":"
        assert tokens[2].value == "name"

    def test_at_addressing(self):
        """Адресация через @ символ."""
        lexer = TemplateLexer("")
        tokens = lexer.tokenize_placeholder_content("tpl@origin:name")
        
        expected_types = [
            TokenType.IDENTIFIER, TokenType.AT, TokenType.IDENTIFIER, 
            TokenType.COLON, TokenType.IDENTIFIER
        ]
        assert len(tokens) == len(expected_types)
        for token, expected_type in zip(tokens, expected_types):
            assert token.type == expected_type

    def test_bracket_addressing(self):
        """Адресация через квадратные скобки."""
        lexer = TemplateLexer("")
        tokens = lexer.tokenize_placeholder_content("tpl@[origin]:name")
        
        expected_types = [
            TokenType.IDENTIFIER, TokenType.AT, TokenType.LBRACKET,
            TokenType.IDENTIFIER, TokenType.RBRACKET, TokenType.COLON,
            TokenType.IDENTIFIER
        ]
        assert len(tokens) == len(expected_types)

    def test_complex_path(self):
        """Сложный путь с слешами и дефисами."""
        lexer = TemplateLexer("")
        tokens = lexer.tokenize_placeholder_content("sub-folder/some-name")
        
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].value == "sub-folder/some-name"

    def test_whitespace_handling(self):
        """Обработка пробелов в содержимом плейсхолдера."""
        lexer = TemplateLexer("")
        tokens = lexer.tokenize_placeholder_content(" section ")
        
        # Пробелы должны пропускаться, остается только идентификатор
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].value == "section"


class TestDirectiveContentTokenization:
    """Тесты для токенизации содержимого директив."""
    
    def test_if_keyword(self):
        """Ключевое слово if в директиве."""
        lexer = TemplateLexer("")
        tokens = lexer.tokenize_directive_content("if condition")
        
        assert len(tokens) == 2
        assert tokens[0].type == TokenType.IF
        assert tokens[0].value == "if"
        assert tokens[1].type == TokenType.IDENTIFIER
        assert tokens[1].value == "condition"

    def test_mode_directive(self):
        """Директива режима с модусом."""
        lexer = TemplateLexer("")
        tokens = lexer.tokenize_directive_content("mode set:value")
        
        expected_types = [
            TokenType.MODE, TokenType.IDENTIFIER, 
            TokenType.COLON, TokenType.IDENTIFIER
        ]
        assert len(tokens) == len(expected_types)
        for token, expected_type in zip(tokens, expected_types):
            assert token.type == expected_type

    def test_logical_operators(self):
        """Логические операторы в условиях."""
        lexer = TemplateLexer("")
        tokens = lexer.tokenize_directive_content("if tag1 AND tag2 OR NOT tag3")
        
        types = [token.type for token in tokens]
        values = [token.value for token in tokens]
        
        assert TokenType.IF in types
        assert TokenType.AND in types
        assert TokenType.OR in types
        assert TokenType.NOT in types
        assert "tag1" in values
        assert "tag2" in values
        assert "tag3" in values

    def test_parentheses_grouping(self):
        """Группировка с помощью скобок."""
        lexer = TemplateLexer("")
        tokens = lexer.tokenize_directive_content("if (tag1 OR tag2) AND tag3")
        
        types = [token.type for token in tokens]
        
        assert TokenType.LPAREN in types
        assert TokenType.RPAREN in types
        assert TokenType.OR in types
        assert TokenType.AND in types

    def test_complex_condition(self):
        """Сложное условие с различными элементами."""
        lexer = TemplateLexer("")
        tokens = lexer.tokenize_directive_content("if NOT (tag:python OR TAGSET:lang:typescript)")
        
        # Проверяем наличие всех ожидаемых типов токенов
        types = [token.type for token in tokens]
        values = [token.value for token in tokens]
        
        assert TokenType.IF in types
        assert TokenType.NOT in types
        assert TokenType.LPAREN in types
        assert TokenType.RPAREN in types
        assert TokenType.OR in types
        assert TokenType.COLON in types
        assert "tag" in values
        assert "python" in values
        assert "TAGSET" in values


class TestErrorHandling:
    """Тесты для обработки ошибок лексера."""
    
    def test_unexpected_character(self):
        """Неожиданный символ должен вызывать LexerError."""
        # Символ @ является валидным в плейсхолдерах для адресации
        # Создаем ситуацию с действительно неожиданным символом
        lexer = TemplateLexer("&")  # & не поддерживается в плейсхолдерах
        lexer.position = 0
        
        # Попытаемся обработать неподдерживаемый символ & в плейсхолдере
        with pytest.raises(LexerError):
            lexer._tokenize_inside_placeholder()

    def test_lexer_error_details(self):
        """Проверка деталей ошибки лексера."""
        try:
            lexer = TemplateLexer("test")
            lexer.position = 0
            lexer._tokenize_inside_placeholder()
        except LexerError as e:
            assert e.line == 1
            assert e.column == 1
            assert e.position == 0
            assert "Unexpected character" in str(e)


class TestConvenienceFunctions:
    """Тесты для вспомогательных функций."""
    
    def test_tokenize_template_function(self):
        """Функция tokenize_template должна работать корректно."""
        text = "Hello ${name}!"
        tokens = tokenize_template(text)
        
        assert len(tokens) > 0
        assert tokens[-1].type == TokenType.EOF
        
        types = [token.type for token in tokens]
        assert TokenType.TEXT in types
        assert TokenType.PLACEHOLDER_START in types
        assert TokenType.PLACEHOLDER_END in types

    def test_token_representation(self):
        """Проверка строкового представления токена."""
        token = Token(TokenType.IDENTIFIER, "test", 0, 1, 1)
        repr_str = repr(token)
        
        assert "IDENTIFIER" in repr_str
        assert "test" in repr_str
        assert "1:1" in repr_str


class TestAdvancedScenarios:
    """Тесты для сложных сценариев токенизации."""
    
    def test_adjacent_special_sequences(self):
        """Соседние специальные последовательности."""
        text = "${section}{% if condition %}{# comment #}"
        lexer = TemplateLexer(text)
        tokens = lexer.tokenize()
        
        # Проверяем, что все специальные последовательности правильно разделены
        types = [token.type for token in tokens if token.type != TokenType.EOF]
        expected_pattern = [
            TokenType.PLACEHOLDER_START, TokenType.IDENTIFIER, TokenType.PLACEHOLDER_END,  # ${section}
            TokenType.DIRECTIVE_START, TokenType.TEXT, TokenType.DIRECTIVE_END,             # {% if condition %}
            TokenType.COMMENT_START, TokenType.TEXT, TokenType.COMMENT_END                  # {# comment #}
        ]
        
        assert types == expected_pattern
        
        # Дополнительная проверка содержимого токенов
        assert tokens[1].value == "section"         # IDENTIFIER в плейсхолдере
        assert " if condition " in tokens[4].value  # TEXT в директиве  
        assert " comment " in tokens[7].value       # TEXT в комментарии

    def test_nested_structures(self):
        """Вложенные структуры с различными типами блоков."""
        text = """
        Start text
        ${section1}
        {% if tag:python %}
            Python-specific content
            ${python-section}
        {% endif %}
        {# This is a comment with ${placeholder} inside #}
        End text
        """
        
        lexer = TemplateLexer(text)
        tokens = lexer.tokenize()
        
        # Проверяем наличие всех основных типов токенов
        types = [token.type for token in tokens]
        
        assert TokenType.TEXT in types
        assert TokenType.PLACEHOLDER_START in types
        assert TokenType.PLACEHOLDER_END in types
        assert TokenType.DIRECTIVE_START in types
        assert TokenType.DIRECTIVE_END in types
        assert TokenType.COMMENT_START in types
        assert TokenType.COMMENT_END in types
        assert TokenType.EOF in types

    def test_empty_placeholders_and_directives(self):
        """Пустые плейсхолдеры и директивы."""
        text = "${}{% %}{#  #}"
        lexer = TemplateLexer(text)
        tokens = lexer.tokenize()
        
        types = [token.type for token in tokens if token.type != TokenType.EOF]
        expected_pattern = [
            TokenType.PLACEHOLDER_START, TokenType.PLACEHOLDER_END,
            TokenType.DIRECTIVE_START, TokenType.TEXT, TokenType.DIRECTIVE_END,
            TokenType.COMMENT_START, TokenType.TEXT, TokenType.COMMENT_END
        ]
        
        assert types == expected_pattern

    def test_line_and_column_tracking_complex(self):
        """Сложный тест отслеживания позиций в многострочном тексте."""
        text = """Line 1
${var1}
Line 3 with ${var2} in middle
{% if condition %}
Content
{% endif %}"""
        
        lexer = TemplateLexer(text)
        tokens = lexer.tokenize()
        
        # Найдем второй плейсхолдер и проверим его позицию
        placeholder_count = 0
        for token in tokens:
            if token.type == TokenType.PLACEHOLDER_START:
                placeholder_count += 1
                if placeholder_count == 2:
                    # Второй плейсхолдер должен быть на строке 3
                    assert token.line == 3
                    assert token.column == 13  # После "Line 3 with " (исправленная позиция)
                    break
    
    def test_special_characters_in_identifiers(self):
        """Специальные символы в идентификаторах."""
        lexer = TemplateLexer("")
        
        # Тестируем различные валидные идентификаторы
        valid_identifiers = [
            "simple",
            "with-dashes",
            "with_underscores",
            "with123numbers",
            "path/to/file",
            "complex-path_with/multiple.parts"
        ]
        
        for identifier in valid_identifiers:
            tokens = lexer.tokenize_placeholder_content(identifier)
            assert len(tokens) == 1
            assert tokens[0].type == TokenType.IDENTIFIER
            assert tokens[0].value == identifier


class TestMarkdownPlaceholders:
    """Тесты для токенизации md плейсхолдеров."""
    
    def test_simple_md_placeholder(self):
        """Простой md плейсхолдер ${md:docs/api}."""
        text = "${md:docs/api}"
        lexer = TemplateLexer(text)
        tokens = lexer.tokenize()
        
        expected_types = [
            TokenType.PLACEHOLDER_START,
            TokenType.IDENTIFIER,      # "md"
            TokenType.COLON,           # ":"
            TokenType.IDENTIFIER,      # "docs/api"
            TokenType.PLACEHOLDER_END,
            TokenType.EOF
        ]
        
        assert len(tokens) == len(expected_types)
        for token, expected_type in zip(tokens, expected_types):
            assert token.type == expected_type
        
        assert tokens[1].value == "md"
        assert tokens[3].value == "docs/api"

    def test_md_placeholder_with_anchor(self):
        """MD плейсхолдер с якорем ${md:docs/api#Authentication}."""
        text = "${md:docs/api#Authentication}"
        lexer = TemplateLexer(text)
        tokens = lexer.tokenize()
        
        expected_types = [
            TokenType.PLACEHOLDER_START,
            TokenType.IDENTIFIER,      # "md"
            TokenType.COLON,           # ":"
            TokenType.IDENTIFIER,      # "docs/api" 
            TokenType.HASH,            # "#"
            TokenType.TEXT,            # "Authentication" (после # обрабатывается как TEXT)
            TokenType.PLACEHOLDER_END,
            TokenType.EOF
        ]
        
        assert len(tokens) == len(expected_types)
        for token, expected_type in zip(tokens, expected_types):
            assert token.type == expected_type
        
        assert tokens[1].value == "md"
        assert tokens[3].value == "docs/api"
        assert tokens[5].value == "Authentication"

    def test_md_placeholder_with_parameters(self):
        """MD плейсхолдер с параметрами ${md:docs/api, level:3, strip_h1:true}."""
        text = "${md:docs/api, level:3, strip_h1:true}"
        lexer = TemplateLexer(text)
        tokens = lexer.tokenize()
        
        expected_types = [
            TokenType.PLACEHOLDER_START,
            TokenType.IDENTIFIER,      # "md"
            TokenType.COLON,           # ":"
            TokenType.IDENTIFIER,      # "docs/api"
            TokenType.COMMA,           # ","
            TokenType.IDENTIFIER,      # "level"
            TokenType.COLON,           # ":"
            TokenType.IDENTIFIER,      # "3"
            TokenType.COMMA,           # ","
            TokenType.IDENTIFIER,      # "strip_h1" 
            TokenType.COLON,           # ":"
            TokenType.IDENTIFIER,      # "true"
            TokenType.PLACEHOLDER_END,
            TokenType.EOF
        ]
        
        assert len(tokens) == len(expected_types)
        for token, expected_type in zip(tokens, expected_types):
            assert token.type == expected_type
        
        # Проверяем ключевые значения
        assert tokens[1].value == "md"
        assert tokens[3].value == "docs/api"
        assert tokens[5].value == "level"
        assert tokens[7].value == "3"
        assert tokens[9].value == "strip_h1"
        assert tokens[11].value == "true"

    def test_md_placeholder_with_addressing(self):
        """MD плейсхолдер с адресацией ${md@apps/web:intro}."""
        text = "${md@apps/web:intro}"
        lexer = TemplateLexer(text)
        tokens = lexer.tokenize()
        
        expected_types = [
            TokenType.PLACEHOLDER_START,
            TokenType.IDENTIFIER,      # "md"
            TokenType.AT,              # "@"
            TokenType.IDENTIFIER,      # "apps/web"
            TokenType.COLON,           # ":"
            TokenType.IDENTIFIER,      # "intro"
            TokenType.PLACEHOLDER_END,
            TokenType.EOF
        ]
        
        assert len(tokens) == len(expected_types)
        for token, expected_type in zip(tokens, expected_types):
            assert token.type == expected_type
        
        assert tokens[1].value == "md"
        assert tokens[3].value == "apps/web"
        assert tokens[5].value == "intro"

    def test_md_placeholder_complex(self):
        """Сложный MD плейсхолдер с адресацией, якорем и параметрами."""
        text = "${md@apps/web:docs/api#Authentication, level:2}"
        lexer = TemplateLexer(text)
        tokens = lexer.tokenize()
        
        # Проверяем основную структуру токенов
        types = [token.type for token in tokens if token.type != TokenType.EOF]
        
        assert TokenType.PLACEHOLDER_START in types
        assert TokenType.IDENTIFIER in types
        assert TokenType.AT in types
        assert TokenType.HASH in types
        assert TokenType.COMMA in types
        assert TokenType.PLACEHOLDER_END in types
        
        # Находим ключевые токены
        md_token = next(token for token in tokens if token.value == "md")
        auth_token = next(token for token in tokens if token.type == TokenType.TEXT and "Authentication" in token.value)
        level_token = next(token for token in tokens if token.value == "level")
        
        assert md_token.type == TokenType.IDENTIFIER
        assert auth_token.type == TokenType.TEXT
        assert level_token.type == TokenType.IDENTIFIER

    def test_md_placeholder_glob_pattern(self):
        """MD плейсхолдер с glob паттерном ${md:docs/*.md}."""
        text = "${md:docs/*.md}"
        lexer = TemplateLexer(text)
        tokens = lexer.tokenize()
        
        expected_types = [
            TokenType.PLACEHOLDER_START,
            TokenType.IDENTIFIER,      # "md"
            TokenType.COLON,           # ":"
            TokenType.IDENTIFIER,      # "docs/*.md" (содержит специальные символы glob)
            TokenType.PLACEHOLDER_END,
            TokenType.EOF
        ]
        
        assert len(tokens) == len(expected_types)
        for token, expected_type in zip(tokens, expected_types):
            assert token.type == expected_type
        
        assert tokens[1].value == "md"
        assert tokens[3].value == "docs/*.md"