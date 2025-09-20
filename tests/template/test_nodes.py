"""
Тесты для AST узлов движка шаблонизации LG V2.

Проверяет создание и поведение всех типов узлов шаблонного AST:
- TextNode
- SectionNode 
- IncludeNode
- ConditionalBlockNode
- ModeBlockNode
- CommentNode
- ElseBlockNode
- Вспомогательные функции для работы с AST
"""

import pytest
from typing import List, cast
from lg.template.nodes import (
    TemplateNode,
    TextNode,
    SectionNode, 
    IncludeNode,
    ConditionalBlockNode,
    ModeBlockNode,
    CommentNode,
    ElseBlockNode,
    TemplateAST,
    collect_section_nodes,
    collect_include_nodes,
    has_conditional_content,
    format_ast_tree
)
from lg.conditions.model import TagCondition
from lg.config.adaptive_model import ModeOptions


class TestTextNode:
    """Тесты для узла обычного текста."""
    
    def test_create_text_node(self):
        """Создание текстового узла."""
        text = "Hello, world!"
        node = TextNode(text=text)
        
        assert node.text == text
        assert isinstance(node, TextNode)

    def test_text_node_immutable(self):
        """Текстовый узел должен быть неизменяемым."""
        node = TextNode(text="test")
        
        # Попытка изменения должна вызвать ошибку
        with pytest.raises((AttributeError, TypeError)):
            node.text = "modified"  # type: ignore

    def test_text_node_visitor_pattern(self):
        """Проверка реализации паттерна Visitor."""
        node = TextNode(text="test")
        
        class MockVisitor:
            def visit_text_node(self, node):
                return f"visited: {node.text}"
        
        visitor = MockVisitor()
        result = node.accept(visitor)
        assert result == "visited: test"

    def test_text_node_equality(self):
        """Проверка равенства текстовых узлов."""
        node1 = TextNode(text="test")
        node2 = TextNode(text="test")
        node3 = TextNode(text="different")
        
        assert node1 == node2
        assert node1 != node3

    def test_empty_text_node(self):
        """Текстовый узел с пустым содержимым."""
        node = TextNode(text="")
        assert node.text == ""

    def test_multiline_text_node(self):
        """Текстовый узел с многострочным содержимым."""
        text = "Line 1\nLine 2\nLine 3"
        node = TextNode(text=text)
        assert node.text == text
        assert "\n" in node.text


class TestSectionNode:
    """Тесты для узла секции."""
    
    def test_create_section_node(self):
        """Создание узла секции."""
        section_name = "my-section"
        node = SectionNode(section_name=section_name)
        
        assert node.section_name == section_name
        assert node.resolved_ref is None

    def test_section_node_with_resolved_ref(self):
        """Узел секции с разрешенной ссылкой."""
        from lg.types import SectionRef
        from pathlib import Path
        
        section_ref = SectionRef(
            name="test-section",
            scope_rel="",
            scope_dir=Path("/test/lg-cfg")
        )
        
        node = SectionNode(
            section_name="test-section",
            resolved_ref=section_ref
        )
        
        assert node.section_name == "test-section"
        assert node.resolved_ref == section_ref

    def test_section_node_visitor_pattern(self):
        """Проверка реализации паттерна Visitor."""
        node = SectionNode(section_name="test")
        
        class MockVisitor:
            def visit_section_node(self, node):
                return f"section: {node.section_name}"
        
        visitor = MockVisitor()
        result = node.accept(visitor)
        assert result == "section: test"

    def test_section_node_immutable(self):
        """Узел секции должен быть неизменяемым."""
        node = SectionNode(section_name="test")
        
        with pytest.raises((AttributeError, TypeError)):
            node.section_name = "modified"  # type: ignore


class TestIncludeNode:
    """Тесты для узла включения."""
    
    def test_create_include_node(self):
        """Создание узла включения."""
        node = IncludeNode(
            kind="tpl",
            name="my-template",
            origin="self"
        )
        
        assert node.kind == "tpl"
        assert node.name == "my-template"
        assert node.origin == "self"
        assert node.children is None

    def test_include_node_with_children(self):
        """Узел включения с вложенными узлами."""
        child1 = TextNode(text="Child 1")
        child2 = TextNode(text="Child 2")
        
        node = IncludeNode(
            kind="ctx",
            name="context-template", 
            origin="apps/web",
            children=[child1, child2]
        )
        
        assert node.kind == "ctx"
        assert node.name == "context-template"
        assert node.origin == "apps/web"
        assert node.children is not None
        assert len(node.children) == 2
        assert node.children[0] == child1
        assert node.children[1] == child2

    def test_include_node_visitor_pattern(self):
        """Проверка реализации паттерна Visitor."""
        node = IncludeNode(kind="tpl", name="test", origin="self")
        
        class MockVisitor:
            def visit_include_node(self, node):
                return f"{node.kind}:{node.name}@{node.origin}"
        
        visitor = MockVisitor()
        result = node.accept(visitor)
        assert result == "tpl:test@self"

    def test_include_kinds(self):
        """Проверка различных типов включений."""
        tpl_node = IncludeNode(kind="tpl", name="template", origin="self")
        ctx_node = IncludeNode(kind="ctx", name="context", origin="self")
        
        assert tpl_node.kind == "tpl"
        assert ctx_node.kind == "ctx"


class TestConditionalBlockNode:
    """Тесты для узла условного блока."""
    
    def test_create_conditional_block(self):
        """Создание условного блока."""
        condition_text = "tag:python"
        text_node = TextNode(text="Python content")
        body: List[TemplateNode] = [text_node]
        
        node = ConditionalBlockNode(
            condition_text=condition_text,
            body=body
        )
        
        assert node.condition_text == condition_text
        assert len(node.body) == 1
        assert isinstance(node.body[0], TextNode)
        assert node.body[0].text == "Python content"  # type: ignore
        assert node.else_block is None
        assert node.condition_ast is None
        assert node.evaluated is None

    def test_conditional_block_with_else(self):
        """Условный блок с else веткой."""
        condition_text = "tag:python"
        body: List[TemplateNode] = [TextNode(text="Python content")]
        else_body: List[TemplateNode] = [TextNode(text="Other content")]
        else_block = ElseBlockNode(body=else_body)
        
        node = ConditionalBlockNode(
            condition_text=condition_text,
            body=body,
            else_block=else_block
        )
        
        assert node.condition_text == condition_text
        assert len(node.body) == 1
        assert node.else_block is not None
        assert len(node.else_block.body) == 1
        assert isinstance(node.else_block.body[0], TextNode)
        assert node.else_block.body[0].text == "Other content"  # type: ignore

    def test_conditional_block_with_parsed_condition(self):
        """Условный блок с разобранным условием."""
        condition_text = "tag:python"
        condition_ast = TagCondition(name="python")
        body: List[TemplateNode] = [TextNode(text="Content")]
        
        node = ConditionalBlockNode(
            condition_text=condition_text,
            body=body,
            condition_ast=condition_ast,
            evaluated=True
        )
        
        assert node.condition_ast == condition_ast
        assert node.evaluated == True

    def test_conditional_block_visitor_pattern(self):
        """Проверка реализации паттерна Visitor."""
        node = ConditionalBlockNode(
            condition_text="tag:test",
            body=[TextNode(text="content")]
        )
        
        class MockVisitor:
            def visit_conditional_block_node(self, node):
                return f"if {node.condition_text}"
        
        visitor = MockVisitor()
        result = node.accept(visitor)
        assert result == "if tag:test"

    def test_nested_conditional_blocks(self):
        """Вложенные условные блоки."""
        inner_condition = ConditionalBlockNode(
            condition_text="tag:inner",
            body=[TextNode(text="Inner content")]
        )
        
        outer_condition = ConditionalBlockNode(
            condition_text="tag:outer",
            body=[TextNode(text="Before inner"), inner_condition, TextNode(text="After inner")]
        )
        
        assert len(outer_condition.body) == 3
        assert isinstance(outer_condition.body[1], ConditionalBlockNode)
        assert outer_condition.body[1].condition_text == "tag:inner"


class TestElseBlockNode:
    """Тесты для узла else блока."""
    
    def test_create_else_block(self):
        """Создание else блока."""
        body: List[TemplateNode] = [TextNode(text="Else content")]
        node = ElseBlockNode(body=body)
        
        assert len(node.body) == 1
        assert isinstance(node.body[0], TextNode)
        assert node.body[0].text == "Else content"  # type: ignore

    def test_empty_else_block(self):
        """Пустой else блок."""
        node = ElseBlockNode(body=[])
        assert len(node.body) == 0

    def test_else_block_visitor_pattern(self):
        """Проверка реализации паттерна Visitor."""
        node = ElseBlockNode(body=[TextNode(text="content")])
        
        class MockVisitor:
            def visit_else_block_node(self, node):
                return f"else with {len(node.body)} items"
        
        visitor = MockVisitor()
        result = node.accept(visitor)
        assert result == "else with 1 items"


class TestModeBlockNode:
    """Тесты для узла режимного блока."""
    
    def test_create_mode_block(self):
        """Создание режимного блока."""
        modeset = "ai-interaction"
        mode = "agent"
        body: List[TemplateNode] = [TextNode(text="Agent-specific content")]
        
        node = ModeBlockNode(
            modeset=modeset,
            mode=mode,
            body=body
        )
        
        assert node.modeset == modeset
        assert node.mode == mode
        assert len(node.body) == 1
        assert isinstance(node.body[0], TextNode)
        assert node.body[0].text == "Agent-specific content"  # type: ignore
        assert node.original_mode_options is None
        assert node.original_active_tags is None
        assert node.original_active_modes is None

    def test_mode_block_with_saved_state(self):
        """Режимный блок с сохраненным состоянием."""
        original_options = ModeOptions()
        original_tags = {"tag1", "tag2"}
        original_modes = {"ai": "basic"}
        
        node = ModeBlockNode(
            modeset="ai-interaction",
            mode="agent",
            body=[TextNode(text="Content")],
            original_mode_options=original_options,
            original_active_tags=original_tags,
            original_active_modes=original_modes
        )
        
        assert node.original_mode_options == original_options
        assert node.original_active_tags == original_tags
        assert node.original_active_modes == original_modes

    def test_mode_block_visitor_pattern(self):
        """Проверка реализации паттерна Visitor."""
        node = ModeBlockNode(
            modeset="test-set",
            mode="test-mode",
            body=[TextNode(text="content")]
        )
        
        class MockVisitor:
            def visit_mode_block_node(self, node):
                return f"mode {node.modeset}:{node.mode}"
        
        visitor = MockVisitor()
        result = node.accept(visitor)
        assert result == "mode test-set:test-mode"

    def test_nested_mode_blocks(self):
        """Вложенные режимные блоки."""
        inner_mode = ModeBlockNode(
            modeset="inner-set",
            mode="inner-mode",
            body=[TextNode(text="Inner content")]
        )
        
        outer_mode = ModeBlockNode(
            modeset="outer-set", 
            mode="outer-mode",
            body=[TextNode(text="Before"), inner_mode, TextNode(text="After")]
        )
        
        assert len(outer_mode.body) == 3
        assert isinstance(outer_mode.body[1], ModeBlockNode)
        assert outer_mode.body[1].modeset == "inner-set"


class TestCommentNode:
    """Тесты для узла комментария."""
    
    def test_create_comment_node(self):
        """Создание узла комментария."""
        comment_text = "This is a comment"
        node = CommentNode(text=comment_text)
        
        assert node.text == comment_text

    def test_empty_comment_node(self):
        """Пустой комментарий."""
        node = CommentNode(text="")
        assert node.text == ""

    def test_multiline_comment_node(self):
        """Многострочный комментарий."""
        comment_text = "Line 1\nLine 2\nLine 3"
        node = CommentNode(text=comment_text)
        assert node.text == comment_text

    def test_comment_node_visitor_pattern(self):
        """Проверка реализации паттерна Visitor."""
        node = CommentNode(text="test comment")
        
        class MockVisitor:
            def visit_comment_node(self, node):
                return f"comment: {node.text}"
        
        visitor = MockVisitor()
        result = node.accept(visitor)
        assert result == "comment: test comment"


class TestASTHelpers:
    """Тесты для вспомогательных функций работы с AST."""
    
    def test_collect_section_nodes(self):
        """Сбор всех узлов секций из AST."""
        ast: TemplateAST = [
            TextNode(text="Start"),
            SectionNode(section_name="section1"),
            ConditionalBlockNode(
                condition_text="tag:test",
                body=[
                    SectionNode(section_name="section2"),
                    TextNode(text="Content")
                ]
            ),
            SectionNode(section_name="section3")
        ]
        
        sections = collect_section_nodes(ast)
        
        assert len(sections) == 3
        section_names = [s.section_name for s in sections]
        assert "section1" in section_names
        assert "section2" in section_names 
        assert "section3" in section_names

    def test_collect_section_nodes_nested(self):
        """Сбор секций из глубоко вложенных структур."""
        else_block = ElseBlockNode(body=[
            SectionNode(section_name="else_section")
        ])
        
        conditional = ConditionalBlockNode(
            condition_text="tag:test",
            body=[SectionNode(section_name="if_section")],
            else_block=else_block
        )
        
        mode_block = ModeBlockNode(
            modeset="test",
            mode="mode",
            body=[conditional]
        )
        
        include_with_children = IncludeNode(
            kind="tpl",
            name="test",
            origin="self",
            children=[SectionNode(section_name="include_section")]
        )
        
        ast: TemplateAST = [mode_block, include_with_children]
        
        sections = collect_section_nodes(ast)
        
        assert len(sections) == 3
        section_names = [s.section_name for s in sections]
        assert "if_section" in section_names
        assert "else_section" in section_names
        assert "include_section" in section_names

    def test_collect_include_nodes(self):
        """Сбор всех узлов включений из AST."""
        ast: TemplateAST = [
            IncludeNode(kind="tpl", name="template1", origin="self"),
            ConditionalBlockNode(
                condition_text="tag:test",
                body=[IncludeNode(kind="ctx", name="context1", origin="self")]
            ),
            IncludeNode(kind="tpl", name="template2", origin="apps/web")
        ]
        
        includes = collect_include_nodes(ast)
        
        assert len(includes) == 3
        include_names = [i.name for i in includes]
        assert "template1" in include_names
        assert "context1" in include_names
        assert "template2" in include_names

    def test_collect_include_nodes_with_children(self):
        """Сбор включений с вложенными детьми."""
        child_include = IncludeNode(kind="tpl", name="child", origin="self")
        
        parent_include = IncludeNode(
            kind="ctx",
            name="parent", 
            origin="self",
            children=[child_include]
        )
        
        ast: TemplateAST = [parent_include]
        
        includes = collect_include_nodes(ast)
        
        assert len(includes) == 2
        include_names = [i.name for i in includes]
        assert "parent" in include_names
        assert "child" in include_names

    def test_has_conditional_content_true(self):
        """Проверка наличия условного содержимого - положительный случай."""
        ast: TemplateAST = [
            TextNode(text="Start"),
            ConditionalBlockNode(
                condition_text="tag:test",
                body=[TextNode(text="Conditional content")]
            )
        ]
        
        assert has_conditional_content(ast) == True

    def test_has_conditional_content_mode_blocks(self):
        """Проверка наличия режимных блоков."""
        ast: TemplateAST = [
            ModeBlockNode(
                modeset="test",
                mode="mode",
                body=[TextNode(text="Mode content")]
            )
        ]
        
        assert has_conditional_content(ast) == True

    def test_has_conditional_content_false(self):
        """Проверка отсутствия условного содержимого."""
        ast: TemplateAST = [
            TextNode(text="Static text"),
            SectionNode(section_name="section"),
            IncludeNode(kind="tpl", name="template", origin="self"),
            CommentNode(text="Comment")
        ]
        
        assert has_conditional_content(ast) == False

    def test_has_conditional_content_nested(self):
        """Проверка условного содержимого во вложенных структурах."""
        include_with_conditional = IncludeNode(
            kind="tpl",
            name="test",
            origin="self",
            children=[
                ConditionalBlockNode(
                    condition_text="tag:nested",
                    body=[TextNode(text="Nested conditional")]
                )
            ]
        )
        
        ast: TemplateAST = [
            TextNode(text="Text"),
            include_with_conditional
        ]
        
        assert has_conditional_content(ast) == True


class TestFormatASTTree:
    """Тесты для функции форматирования AST в виде дерева."""
    
    def test_format_simple_ast(self):
        """Форматирование простого AST."""
        ast: TemplateAST = [
            TextNode(text="Hello"),
            SectionNode(section_name="section1"),
            CommentNode(text="comment")
        ]
        
        tree_str = format_ast_tree(ast)
        
        assert "TextNode" in tree_str
        assert "SectionNode" in tree_str
        assert "CommentNode" in tree_str
        assert "Hello" in tree_str
        assert "section1" in tree_str
        assert "comment" in tree_str

    def test_format_nested_ast(self):
        """Форматирование вложенного AST."""
        conditional = ConditionalBlockNode(
            condition_text="tag:test",
            body=[
                TextNode(text="Inner content"),
                SectionNode(section_name="inner_section")
            ]
        )
        
        ast: TemplateAST = [
            TextNode(text="Start"),
            conditional,
            TextNode(text="End")
        ]
        
        tree_str = format_ast_tree(ast)
        
        # Проверяем структуру вложенности через отступы
        lines = tree_str.split('\n')
        conditional_line = None
        inner_content_line = None
        
        for i, line in enumerate(lines):
            if "ConditionalBlockNode" in line:
                conditional_line = i
            elif "Inner content" in line and conditional_line is not None:
                inner_content_line = i
                break
        
        assert conditional_line is not None
        assert inner_content_line is not None
        
        # Проверяем, что вложенное содержимое имеет больше отступов
        conditional_indent = len(lines[conditional_line]) - len(lines[conditional_line].lstrip())
        inner_indent = len(lines[inner_content_line]) - len(lines[inner_content_line].lstrip())
        assert inner_indent > conditional_indent

    def test_format_with_else_blocks(self):
        """Форматирование с else блоками."""
        else_block = ElseBlockNode(body=[TextNode(text="Else content")])
        conditional = ConditionalBlockNode(
            condition_text="tag:test",
            body=[TextNode(text="If content")],
            else_block=else_block
        )
        
        ast: TemplateAST = [conditional]
        
        tree_str = format_ast_tree(ast)
        
        assert "ConditionalBlockNode" in tree_str
        assert "body:" in tree_str
        assert "else:" in tree_str
        assert "If content" in tree_str
        assert "Else content" in tree_str

    def test_format_empty_ast(self):
        """Форматирование пустого AST."""
        tree_str = format_ast_tree([])
        assert tree_str == ""

    def test_format_mode_blocks(self):
        """Форматирование режимных блоков."""
        mode_block = ModeBlockNode(
            modeset="ai-interaction",
            mode="agent",
            body=[TextNode(text="Mode content")]
        )
        
        ast: TemplateAST = [mode_block]
        
        tree_str = format_ast_tree(ast)
        
        assert "ModeBlockNode" in tree_str
        assert "ai-interaction" in tree_str
        assert "agent" in tree_str
        assert "Mode content" in tree_str