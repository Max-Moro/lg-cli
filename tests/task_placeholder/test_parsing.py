"""
Tests for parsing task placeholders.

Checks correct parsing of different placeholder forms:
- ${task}
- ${task:prompt:"default text"}
- With whitespace
- With escape sequences
"""

import pytest

from lg.template.context import TemplateContext
from lg.template.lexer import ContextualLexer
from lg.template.nodes import TextNode
from lg.template.parser import ModularParser
from lg.template.registry import TemplateRegistry
from lg.template.task_placeholder.nodes import TaskNode
from tests.infrastructure import make_run_context


class TestTaskPlaceholderParsing:
    """Tests for parsing task placeholders."""

    @pytest.fixture
    def registry_with_plugin(self, task_project):
        """Registry with registered task plugin."""
        registry = TemplateRegistry()
        run_ctx = make_run_context(task_project)
        template_ctx = TemplateContext(run_ctx)

        # Register all necessary plugins in the correct order
        from lg.template.common_placeholders import CommonPlaceholdersPlugin
        from lg.template.task_placeholder import TaskPlaceholderPlugin

        # First register basic placeholders
        common_plugin = CommonPlaceholdersPlugin(template_ctx)
        registry.register_plugin(common_plugin)

        # Then task plugin
        task_plugin = TaskPlaceholderPlugin(template_ctx)
        registry.register_plugin(task_plugin)

        # Create dummy handler for plugin initialization
        class DummyHandlers:
            def process_ast_node(self, context): return ""
            def process_section_ref(self, section_ref): return ""
            def parse_next_node(self, context): return None
            def resolve_ast(self, ast, context=""): return ast

        # Initialize plugins
        registry.initialize_plugins(DummyHandlers())

        return registry

    def parse_template(self, text: str, registry: TemplateRegistry):
        """Helper function to parse template."""
        lexer = ContextualLexer(registry)
        tokens = lexer.tokenize(text)
        parser = ModularParser(registry)
        return parser.parse(tokens)

    def test_simple_task_placeholder(self, registry_with_plugin):
        """Test simple placeholder ${task}."""
        template = "${task}"
        ast = self.parse_template(template, registry_with_plugin)
        
        assert len(ast) == 1
        assert isinstance(ast[0], TaskNode)
        assert ast[0].default_prompt is None
    
    def test_task_with_default_prompt(self, registry_with_plugin):
        """Test placeholder with default value."""
        template = '${task:prompt:"Default task description"}'
        ast = self.parse_template(template, registry_with_plugin)
        
        assert len(ast) == 1
        assert isinstance(ast[0], TaskNode)
        assert ast[0].default_prompt == "Default task description"
    
    def test_task_with_escaped_quotes(self, registry_with_plugin):
        """Test with escaped quotes in default."""
        template = r'${task:prompt:"Fix \"critical\" bug"}'
        ast = self.parse_template(template, registry_with_plugin)
        
        assert len(ast) == 1
        assert isinstance(ast[0], TaskNode)
        assert ast[0].default_prompt == 'Fix "critical" bug'
    
    def test_task_with_newlines(self, registry_with_plugin):
        """Test with newlines in default."""
        template = r'${task:prompt:"Line 1\nLine 2\nLine 3"}'
        ast = self.parse_template(template, registry_with_plugin)
        
        assert len(ast) == 1
        assert isinstance(ast[0], TaskNode)
        assert ast[0].default_prompt == "Line 1\nLine 2\nLine 3"
    
    def test_task_with_whitespace(self, registry_with_plugin):
        """Test with spaces around components."""
        template = '${ task : prompt : "Default" }'
        ast = self.parse_template(template, registry_with_plugin)
        
        assert len(ast) == 1
        assert isinstance(ast[0], TaskNode)
        assert ast[0].default_prompt == "Default"
    
    def test_task_in_text_context(self, registry_with_plugin):
        """Test placeholder inside text."""
        template = "Current task: ${task}\n\nNext steps..."
        ast = self.parse_template(template, registry_with_plugin)
        
        assert len(ast) == 3
        assert isinstance(ast[0], TextNode)
        assert ast[0].text == "Current task: "
        assert isinstance(ast[1], TaskNode)
        assert isinstance(ast[2], TextNode)
        assert ast[2].text == "\n\nNext steps..."
    
    def test_multiple_task_placeholders(self, registry_with_plugin):
        """Test multiple task placeholders in template."""
        template = '${task}\n\n${task:prompt:"Default"}'
        ast = self.parse_template(template, registry_with_plugin)

        # Should be: TaskNode, TextNode, TaskNode
        assert len(ast) == 3
        assert isinstance(ast[0], TaskNode)
        assert ast[0].default_prompt is None
        assert isinstance(ast[1], TextNode)
        assert isinstance(ast[2], TaskNode)
        assert ast[2].default_prompt == "Default"
    
    def test_empty_default_prompt(self, registry_with_plugin):
        """Test with empty default value."""
        template = '${task:prompt:""}'
        ast = self.parse_template(template, registry_with_plugin)
        
        assert len(ast) == 1
        assert isinstance(ast[0], TaskNode)
        assert ast[0].default_prompt == ""
    
    def test_multiline_default_prompt(self, registry_with_plugin):
        """Test with multiline default value."""
        template = r'${task:prompt:"Task list:\n- Item 1\n- Item 2\n- Item 3"}'
        ast = self.parse_template(template, registry_with_plugin)
        
        assert len(ast) == 1
        assert isinstance(ast[0], TaskNode)
        expected = "Task list:\n- Item 1\n- Item 2\n- Item 3"
        assert ast[0].default_prompt == expected
    
    def test_canon_key_simple(self, registry_with_plugin):
        """Test canonical key generation for simple task."""
        template = "${task}"
        ast = self.parse_template(template, registry_with_plugin)
        
        assert isinstance(ast[0], TaskNode)
        assert ast[0].canon_key() == "task"
    
    def test_canon_key_with_prompt(self, registry_with_plugin):
        """Test canonical key generation with default."""
        template = '${task:prompt:"Some default text here"}'
        ast = self.parse_template(template, registry_with_plugin)

        assert isinstance(ast[0], TaskNode)
        # Key should contain "task:prompt:" and start of text
        key = ast[0].canon_key()
        assert key.startswith('task:prompt:"Some default text here')
        assert '"' in key


class TestTaskPlaceholderEdgeCases:
    """Tests for edge cases in parsing."""

    @pytest.fixture
    def registry_with_plugin(self, task_project):
        """Registry with registered task plugin."""
        registry = TemplateRegistry()
        run_ctx = make_run_context(task_project)
        template_ctx = TemplateContext(run_ctx)

        # Register all necessary plugins in the correct order
        from lg.template.common_placeholders import CommonPlaceholdersPlugin
        from lg.template.task_placeholder import TaskPlaceholderPlugin

        # First register basic placeholders
        common_plugin = CommonPlaceholdersPlugin(template_ctx)
        registry.register_plugin(common_plugin)

        # Then task plugin
        task_plugin = TaskPlaceholderPlugin(template_ctx)
        registry.register_plugin(task_plugin)

        # Create dummy handler for plugin initialization
        class DummyHandlers:
            def process_ast_node(self, context): return ""
            def process_section_ref(self, section_ref): return ""
            def parse_next_node(self, context): return None
            def resolve_ast(self, ast, context=""): return ast

        # Initialize plugins
        registry.initialize_plugins(DummyHandlers())

        return registry
    
    def parse_template(self, text: str, registry: TemplateRegistry):
        """Helper function to parse template."""
        lexer = ContextualLexer(registry)
        tokens = lexer.tokenize(text)
        parser = ModularParser(registry)
        return parser.parse(tokens)

    def test_not_a_task_placeholder(self, registry_with_plugin):
        """Check that ${tasks} is not recognized as task placeholder."""
        template = "${tasks}"
        ast = self.parse_template(template, registry_with_plugin)

        # Should be parsed as regular text or other placeholder
        # but not as TaskNode
        assert not any(isinstance(node, TaskNode) for node in ast)
    
    def test_malformed_prompt_no_colon(self, registry_with_plugin):
        """Test with incorrect syntax (missing colon)."""
        template = '${task:prompt"Default"}'

        # Should be parsing error
        with pytest.raises(Exception):
            self.parse_template(template, registry_with_plugin)
    
    def test_malformed_prompt_no_quotes(self, registry_with_plugin):
        """Test with incorrect syntax (missing quotes)."""
        template = '${task:prompt:Default}'

        # Should be parsing error
        with pytest.raises(Exception):
            self.parse_template(template, registry_with_plugin)
    
    def test_escaped_backslash(self, registry_with_plugin):
        """Test with escaped backslash."""
        template = r'${task:prompt:"Path: C:\\Users\\test"}'
        ast = self.parse_template(template, registry_with_plugin)

        assert len(ast) == 1
        assert isinstance(ast[0], TaskNode)
        # Should get correct path with backslashes
        assert ast[0].default_prompt == r"Path: C:\Users\test"
    
    def test_special_characters_in_default(self, registry_with_plugin):
        """Test with special characters in default value."""
        template = r'${task:prompt:"Fix: bug #123 (critical) & update docs"}'
        ast = self.parse_template(template, registry_with_plugin)

        assert len(ast) == 1
        assert isinstance(ast[0], TaskNode)
        assert ast[0].default_prompt == "Fix: bug #123 (critical) & update docs"
