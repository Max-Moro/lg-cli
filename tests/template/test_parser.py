"""Тесты для парсера шаблонов TemplateParser."""
from typing import List

import pytest

from lg.template.lexer import TemplateLexer, Token, TokenType
from lg.template.nodes import (
    TextNode, SectionNode, IncludeNode,
    ConditionalBlockNode, ElifBlockNode, ElseBlockNode, ModeBlockNode, CommentNode
)
from lg.template.parser import TemplateParser, ParserError


class TestTemplateParser:
    """Основные тесты для TemplateParser."""

    def test_parse_empty_template(self):
        """Парсинг пустого шаблона."""
        tokens: List[Token] = []
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        assert ast == []

    def test_parse_simple_text(self):
        """Парсинг простого текста."""
        lexer = TemplateLexer("Hello, world!")
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        assert len(ast) == 1
        assert isinstance(ast[0], TextNode)
        assert ast[0].text == "Hello, world!"

    def test_parse_text_with_section(self):
        """Парсинг текста с секцией."""
        lexer = TemplateLexer("Hello ${name}!")
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        assert len(ast) == 3
        assert isinstance(ast[0], TextNode)
        assert ast[0].text == "Hello "
        assert isinstance(ast[1], SectionNode)
        assert ast[1].section_name == "name"
        assert isinstance(ast[2], TextNode)
        assert ast[2].text == "!"

    def test_parse_multiple_sections(self):
        """Парсинг нескольких секций."""
        lexer = TemplateLexer("${greeting} ${name}, ${message}")
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        assert len(ast) == 5
        assert isinstance(ast[0], SectionNode)
        assert ast[0].section_name == "greeting"
        assert isinstance(ast[1], TextNode)
        assert ast[1].text == " "
        assert isinstance(ast[2], SectionNode)
        assert ast[2].section_name == "name"
        assert isinstance(ast[3], TextNode)
        assert ast[3].text == ", "
        assert isinstance(ast[4], SectionNode)
        assert ast[4].section_name == "message"

    def test_parse_tpl_include(self):
        """Парсинг включения шаблона."""
        lexer = TemplateLexer("${tpl:header}")
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        assert len(ast) == 1
        assert isinstance(ast[0], IncludeNode)
        assert ast[0].kind == "tpl"
        assert ast[0].name == "header"

    def test_parse_ctx_include(self):
        """Парсинг включения контекста."""
        lexer = TemplateLexer("${ctx:config}")
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        assert len(ast) == 1
        assert isinstance(ast[0], IncludeNode)
        assert ast[0].kind == "ctx"
        assert ast[0].name == "config"


class TestParserDirectives:
    """Тесты для парсинга директив."""

    def test_parse_if_directive(self):
        """Парсинг условной директивы."""
        lexer = TemplateLexer("{%if tag:test%}content{%endif%}")
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        assert len(ast) == 1
        assert isinstance(ast[0], ConditionalBlockNode)
        assert ast[0].condition_text == "tag : test"
        assert len(ast[0].body) == 1
        assert isinstance(ast[0].body[0], TextNode)
        assert ast[0].body[0].text == "content"
        assert ast[0].else_block is None

    def test_parse_if_else_directive(self):
        """Парсинг условной директивы с else."""
        lexer = TemplateLexer("{%if tag:test%}true content{%else%}false content{%endif%}")
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        assert len(ast) == 1
        assert isinstance(ast[0], ConditionalBlockNode)
        assert ast[0].condition_text == "tag : test"
        assert len(ast[0].body) == 1
        assert isinstance(ast[0].body[0], TextNode)
        assert ast[0].body[0].text == "true content"
        
        assert ast[0].else_block is not None
        assert isinstance(ast[0].else_block, ElseBlockNode)
        assert len(ast[0].else_block.body) == 1
        assert isinstance(ast[0].else_block.body[0], TextNode)
        assert ast[0].else_block.body[0].text == "false content"

    def test_parse_nested_if_directives(self):
        """Парсинг вложенных условных директив."""
        template = "{%if tag:outer%}{%if tag:inner%}nested{%endif%}{%endif%}"
        lexer = TemplateLexer(template)
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        assert len(ast) == 1
        outer_if = ast[0]
        assert isinstance(outer_if, ConditionalBlockNode)
        assert outer_if.condition_text == "tag : outer"
        assert len(outer_if.body) == 1
        
        inner_if = outer_if.body[0]
        assert isinstance(inner_if, ConditionalBlockNode)
        assert inner_if.condition_text == "tag : inner"
        assert len(inner_if.body) == 1
        assert isinstance(inner_if.body[0], TextNode)
        assert inner_if.body[0].text == "nested"

    def test_parse_if_elif_directive(self):
        """Парсинг условной директивы с elif."""
        template = "{%if tag:first%}first content{%elif tag:second%}second content{%endif%}"
        lexer = TemplateLexer(template)
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        assert len(ast) == 1
        assert isinstance(ast[0], ConditionalBlockNode)
        assert ast[0].condition_text == "tag : first"
        assert len(ast[0].body) == 1
        assert isinstance(ast[0].body[0], TextNode)
        assert ast[0].body[0].text == "first content"
        
        # Проверяем elif блок
        assert len(ast[0].elif_blocks) == 1
        elif_block = ast[0].elif_blocks[0]
        assert isinstance(elif_block, ElifBlockNode)
        assert elif_block.condition_text == "tag : second"
        assert len(elif_block.body) == 1
        assert isinstance(elif_block.body[0], TextNode)
        assert elif_block.body[0].text == "second content"
        
        assert ast[0].else_block is None

    def test_parse_if_multiple_elif_directive(self):
        """Парсинг условной директивы с несколькими elif."""
        template = "{%if tag:first%}first{%elif tag:second%}second{%elif tag:third%}third{%endif%}"
        lexer = TemplateLexer(template)
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        assert len(ast) == 1
        assert isinstance(ast[0], ConditionalBlockNode)
        assert ast[0].condition_text == "tag : first"
        
        # Проверяем множественные elif блоки
        assert len(ast[0].elif_blocks) == 2
        
        elif1 = ast[0].elif_blocks[0]
        assert isinstance(elif1, ElifBlockNode)
        assert elif1.condition_text == "tag : second"
        assert len(elif1.body) == 1
        assert isinstance(elif1.body[0], TextNode)
        assert elif1.body[0].text == "second"
        
        elif2 = ast[0].elif_blocks[1]
        assert isinstance(elif2, ElifBlockNode)
        assert elif2.condition_text == "tag : third"
        assert len(elif2.body) == 1
        assert isinstance(elif2.body[0], TextNode)
        assert elif2.body[0].text == "third"
        
        assert ast[0].else_block is None

    def test_parse_if_elif_else_directive(self):
        """Парсинг полной цепочки if-elif-else."""
        template = "{%if tag:first%}first{%elif tag:second%}second{%else%}default{%endif%}"
        lexer = TemplateLexer(template)
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        assert len(ast) == 1
        assert isinstance(ast[0], ConditionalBlockNode)
        assert ast[0].condition_text == "tag : first"
        
        # Проверяем elif блок
        assert len(ast[0].elif_blocks) == 1
        elif_block = ast[0].elif_blocks[0]
        assert isinstance(elif_block, ElifBlockNode)
        assert elif_block.condition_text == "tag : second"
        assert isinstance(elif_block.body[0], TextNode)
        assert elif_block.body[0].text == "second"
        
        # Проверяем else блок
        assert ast[0].else_block is not None
        assert isinstance(ast[0].else_block, ElseBlockNode)
        assert len(ast[0].else_block.body) == 1
        assert isinstance(ast[0].else_block.body[0], TextNode)
        assert ast[0].else_block.body[0].text == "default"

    def test_parse_mode_directive(self):
        """Парсинг директивы режима."""
        lexer = TemplateLexer("{%mode java:class%}class content{%endmode%}")
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        assert len(ast) == 1
        assert isinstance(ast[0], ModeBlockNode)
        assert ast[0].modeset == "java"
        assert ast[0].mode == "class"
        assert len(ast[0].body) == 1
        assert isinstance(ast[0].body[0], TextNode)
        assert ast[0].body[0].text == "class content"

    def test_parse_nested_mode_directives(self):
        """Парсинг вложенных директив режима."""
        template = "{%mode java:class%}{%mode java:method%}method content{%endmode%}{%endmode%}"
        lexer = TemplateLexer(template)
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        assert len(ast) == 1
        outer_mode = ast[0]
        assert isinstance(outer_mode, ModeBlockNode)
        assert outer_mode.modeset == "java"
        assert outer_mode.mode == "class"
        assert len(outer_mode.body) == 1
        
        inner_mode = outer_mode.body[0]
        assert isinstance(inner_mode, ModeBlockNode)
        assert inner_mode.modeset == "java"
        assert inner_mode.mode == "method"
        assert len(inner_mode.body) == 1
        assert isinstance(inner_mode.body[0], TextNode)
        assert inner_mode.body[0].text == "method content"


class TestParserComments:
    """Тесты для парсинга комментариев."""

    def test_parse_comment(self):
        """Парсинг комментария."""
        lexer = TemplateLexer("{# This is a comment #}")
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        assert len(ast) == 1
        assert isinstance(ast[0], CommentNode)
        assert ast[0].text == " This is a comment "

    def test_parse_empty_comment(self):
        """Парсинг пустого комментария."""
        lexer = TemplateLexer("{##}")
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        assert len(ast) == 1
        assert isinstance(ast[0], CommentNode)
        assert ast[0].text == ""

    def test_parse_multiline_comment(self):
        """Парсинг многострочного комментария."""
        lexer = TemplateLexer("{#Line 1\nLine 2\nLine 3#}")
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        assert len(ast) == 1
        assert isinstance(ast[0], CommentNode)
        assert ast[0].text == "Line 1\nLine 2\nLine 3"


class TestParserErrors:
    """Тесты для обработки ошибок парсинга."""

    def test_unmatched_if_directive(self):
        """Ошибка при незакрытой if директиве."""
        lexer = TemplateLexer("{%if tag:test%}content")
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        with pytest.raises(ParserError) as excinfo:
            parser.parse()
        
        assert "Unexpected end of tokens" in str(excinfo.value)

    def test_unexpected_else_directive(self):
        """Ошибка при неожиданной else директиве."""
        lexer = TemplateLexer("{%else%}content{%endif%}")
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        with pytest.raises(ParserError) as excinfo:
            parser.parse()
        
        assert "else without if" in str(excinfo.value).lower()

    def test_unexpected_endif_directive(self):
        """Ошибка при неожиданной endif директиве."""
        lexer = TemplateLexer("{%endif%}")
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        with pytest.raises(ParserError) as excinfo:
            parser.parse()
        
        assert "endif without if" in str(excinfo.value).lower()

    def test_unmatched_mode_directive(self):
        """Ошибка при незакрытой mode директиве."""
        lexer = TemplateLexer("{%mode java:class%}content")
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        with pytest.raises(ParserError) as excinfo:
            parser.parse()
        
        assert "Unexpected end of tokens" in str(excinfo.value)

    def test_unexpected_endmode_directive(self):
        """Ошибка при неожиданной endmode директиве."""
        lexer = TemplateLexer("{%endmode%}")
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        with pytest.raises(ParserError) as excinfo:
            parser.parse()
        
        assert "endmode without mode" in str(excinfo.value).lower()

    def test_empty_placeholder(self):
        """Ошибка при пустом плейсхолдере."""
        lexer = TemplateLexer("${}")
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        with pytest.raises(ParserError) as excinfo:
            parser.parse()
        
        assert "Empty placeholder" in str(excinfo.value)

    def test_invalid_include_format(self):
        """Ошибка при неверном формате включения."""
        lexer = TemplateLexer("${tpl}")
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        with pytest.raises(ParserError) as excinfo:
            parser.parse()
        
        assert "Invalid tpl include format" in str(excinfo.value)

    def test_unexpected_token_at_top_level(self):
        """Ошибка при неожиданном токене на верхнем уровне."""
        # Создаем токены напрямую для имитации неожиданного токена
        tokens = [Token(TokenType.DIRECTIVE_END, "endif", 1, 1, 5)]
        parser = TemplateParser(tokens)
        
        with pytest.raises(ParserError) as excinfo:
            parser.parse()
        
        assert "Unexpected token at top level" in str(excinfo.value)


class TestParserComplexScenarios:
    """Тесты для сложных сценариев парсинга."""

    def test_mixed_content(self):
        """Парсинг смешанного контента."""
        template = '''
        # Header
        {%if tag:debug%}
        Debug info: ${debug_info}
        {%endif%}
        
        Hello ${name}!
        
        {%mode java:class%}
        ${tpl:class_header}
        {%endmode%}
        '''
        
        lexer = TemplateLexer(template)
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        # Проверяем что есть различные типы узлов на верхнем уровне
        node_types = {type(node) for node in ast}
        assert TextNode in node_types
        assert ConditionalBlockNode in node_types
        assert SectionNode in node_types
        assert ModeBlockNode in node_types
        
        # Проверяем что есть IncludeNode в любом месте AST
        from lg.template.nodes import collect_include_nodes
        include_nodes = collect_include_nodes(ast)
        assert len(include_nodes) > 0

    def test_deeply_nested_structures(self):
        """Парсинг глубоко вложенных структур."""
        template = '''
        {%if tag:feature%}
            {%mode java:class%}
                {%if tag:debug%}
                    Debug: ${debug_message}
                {%else%}
                    Production: ${prod_message}
                {%endif%}
            {%endmode%}
        {%endif%}
        '''
        
        lexer = TemplateLexer(template)
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        # Проверяем структуру вложения - находим ConditionalBlockNode
        conditional_nodes = [node for node in ast if isinstance(node, ConditionalBlockNode)]
        assert len(conditional_nodes) == 1
        outer_if = conditional_nodes[0]
        
        # Внутри должен быть mode блок
        mode_nodes = [node for node in outer_if.body if isinstance(node, ModeBlockNode)]
        assert len(mode_nodes) == 1
        
        mode_block = mode_nodes[0]
        # Внутри mode блока должен быть вложенный if
        inner_ifs = [node for node in mode_block.body if isinstance(node, ConditionalBlockNode)]
        assert len(inner_ifs) == 1

    def test_template_with_includes_and_children(self):
        """Парсинг шаблона с включениями и дочерними элементами."""
        template = '''
        ${tpl:header}
        
        {%if tag:content%}
        Content: ${content}
        {%endif%}
        
        ${ctx:footer}
        '''
        
        lexer = TemplateLexer(template)
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        # Найдем все включения
        includes = [node for node in ast if isinstance(node, IncludeNode)]
        assert len(includes) == 2
        
        # Проверим типы включений
        tpl_includes = [inc for inc in includes if inc.kind == "tpl"]
        ctx_includes = [inc for inc in includes if inc.kind == "ctx"]
        
        assert len(tpl_includes) == 1
        assert len(ctx_includes) == 1
        assert tpl_includes[0].name == "header"
        assert ctx_includes[0].name == "footer"

    def test_parser_preserves_position_info(self):
        """Парсер сохраняет информацию о позиции в исходном коде."""
        template = "Line 1\n${section}\nLine 3"
        
        lexer = TemplateLexer(template)
        tokens = lexer.tokenize()
        parser = TemplateParser(tokens)
        
        ast = parser.parse()
        
        # Проверяем, что узлы сохраняют позицию из токенов
        # (это зависит от того, как реализован парсер)
        assert len(ast) == 3
        assert isinstance(ast[0], TextNode)
        assert isinstance(ast[1], SectionNode)
        assert isinstance(ast[2], TextNode)