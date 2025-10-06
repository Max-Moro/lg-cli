"""
Тесты парсинга task-плейсхолдеров.

Проверяет корректность парсинга различных форм плейсхолдеров:
- ${task}
- ${task:prompt:"default text"}
- С whitespace
- С escape-последовательностями
"""

import pytest

from lg.template.lexer import ContextualLexer
from lg.template.parser import ModularParser
from lg.template.registry import TemplateRegistry
from lg.template.task_placeholder.nodes import TaskNode
from lg.template.nodes import TextNode
from lg.template.task_placeholder import TaskPlaceholderPlugin
from lg.template.context import TemplateContext
from tests.infrastructure import make_run_context


class TestTaskPlaceholderParsing:
    """Тесты парсинга task-плейсхолдеров."""
    
    @pytest.fixture
    def registry_with_plugin(self, task_project):
        """Реестр с зарегистрированным task-плагином."""
        registry = TemplateRegistry()
        run_ctx = make_run_context(task_project)
        template_ctx = TemplateContext(run_ctx)
        
        # Регистрируем все необходимые плагины в правильном порядке
        from lg.template.common_placeholders import CommonPlaceholdersPlugin
        from lg.template.task_placeholder import TaskPlaceholderPlugin
        
        # Сначала регистрируем базовые плейсхолдеры
        common_plugin = CommonPlaceholdersPlugin(template_ctx)
        registry.register_plugin(common_plugin)
        
        # Затем task-плагин
        task_plugin = TaskPlaceholderPlugin(template_ctx)
        registry.register_plugin(task_plugin)
        
        # Создаем фиктивный обработчик для инициализации плагинов
        class DummyHandlers:
            def process_ast_node(self, context): return ""
            def process_section_ref(self, section_ref): return ""
            def parse_next_node(self, context): return None
            def resolve_ast(self, ast, context=""): return ast
        
        # Инициализируем плагины
        registry.initialize_plugins(DummyHandlers())
        
        return registry
    
    def parse_template(self, text: str, registry: TemplateRegistry):
        """Вспомогательная функция для парсинга шаблона."""
        lexer = ContextualLexer(registry)
        tokens = lexer.tokenize(text)
        parser = ModularParser(registry)
        return parser.parse(tokens)
    
    def test_simple_task_placeholder(self, registry_with_plugin):
        """Тест простого плейсхолдера ${task}."""
        template = "${task}"
        ast = self.parse_template(template, registry_with_plugin)
        
        assert len(ast) == 1
        assert isinstance(ast[0], TaskNode)
        assert ast[0].default_prompt is None
    
    def test_task_with_default_prompt(self, registry_with_plugin):
        """Тест плейсхолдера с дефолтным значением."""
        template = '${task:prompt:"Default task description"}'
        ast = self.parse_template(template, registry_with_plugin)
        
        assert len(ast) == 1
        assert isinstance(ast[0], TaskNode)
        assert ast[0].default_prompt == "Default task description"
    
    def test_task_with_escaped_quotes(self, registry_with_plugin):
        """Тест с экранированными кавычками в дефолте."""
        template = r'${task:prompt:"Fix \"critical\" bug"}'
        ast = self.parse_template(template, registry_with_plugin)
        
        assert len(ast) == 1
        assert isinstance(ast[0], TaskNode)
        assert ast[0].default_prompt == 'Fix "critical" bug'
    
    def test_task_with_newlines(self, registry_with_plugin):
        """Тест с переносами строк в дефолте."""
        template = r'${task:prompt:"Line 1\nLine 2\nLine 3"}'
        ast = self.parse_template(template, registry_with_plugin)
        
        assert len(ast) == 1
        assert isinstance(ast[0], TaskNode)
        assert ast[0].default_prompt == "Line 1\nLine 2\nLine 3"
    
    def test_task_with_whitespace(self, registry_with_plugin):
        """Тест с пробелами вокруг компонентов."""
        template = '${ task : prompt : "Default" }'
        ast = self.parse_template(template, registry_with_plugin)
        
        assert len(ast) == 1
        assert isinstance(ast[0], TaskNode)
        assert ast[0].default_prompt == "Default"
    
    def test_task_in_text_context(self, registry_with_plugin):
        """Тест плейсхолдера внутри текста."""
        template = "Current task: ${task}\n\nNext steps..."
        ast = self.parse_template(template, registry_with_plugin)
        
        assert len(ast) == 3
        assert isinstance(ast[0], TextNode)
        assert ast[0].text == "Current task: "
        assert isinstance(ast[1], TaskNode)
        assert isinstance(ast[2], TextNode)
        assert ast[2].text == "\n\nNext steps..."
    
    def test_multiple_task_placeholders(self, registry_with_plugin):
        """Тест нескольких task-плейсхолдеров в шаблоне."""
        template = '${task}\n\n${task:prompt:"Default"}'
        ast = self.parse_template(template, registry_with_plugin)
        
        # Должно быть: TaskNode, TextNode, TaskNode
        assert len(ast) == 3
        assert isinstance(ast[0], TaskNode)
        assert ast[0].default_prompt is None
        assert isinstance(ast[1], TextNode)
        assert isinstance(ast[2], TaskNode)
        assert ast[2].default_prompt == "Default"
    
    def test_empty_default_prompt(self, registry_with_plugin):
        """Тест с пустым дефолтным значением."""
        template = '${task:prompt:""}'
        ast = self.parse_template(template, registry_with_plugin)
        
        assert len(ast) == 1
        assert isinstance(ast[0], TaskNode)
        assert ast[0].default_prompt == ""
    
    def test_multiline_default_prompt(self, registry_with_plugin):
        """Тест с многострочным дефолтным значением."""
        template = r'${task:prompt:"Task list:\n- Item 1\n- Item 2\n- Item 3"}'
        ast = self.parse_template(template, registry_with_plugin)
        
        assert len(ast) == 1
        assert isinstance(ast[0], TaskNode)
        expected = "Task list:\n- Item 1\n- Item 2\n- Item 3"
        assert ast[0].default_prompt == expected
    
    def test_canon_key_simple(self, registry_with_plugin):
        """Тест генерации канонического ключа для простого task."""
        template = "${task}"
        ast = self.parse_template(template, registry_with_plugin)
        
        assert isinstance(ast[0], TaskNode)
        assert ast[0].canon_key() == "task"
    
    def test_canon_key_with_prompt(self, registry_with_plugin):
        """Тест генерации канонического ключа с дефолтом."""
        template = '${task:prompt:"Some default text here"}'
        ast = self.parse_template(template, registry_with_plugin)
        
        assert isinstance(ast[0], TaskNode)
        # Ключ должен содержать "task:prompt:" и начало текста
        key = ast[0].canon_key()
        assert key.startswith('task:prompt:"Some default text here')
        assert '"' in key


class TestTaskPlaceholderEdgeCases:
    """Тесты граничных случаев парсинга."""
    
    @pytest.fixture
    def registry_with_plugin(self, task_project):
        """Реестр с зарегистрированным task-плагином."""
        registry = TemplateRegistry()
        run_ctx = make_run_context(task_project)
        template_ctx = TemplateContext(run_ctx)
        
        # Регистрируем все необходимые плагины в правильном порядке
        from lg.template.common_placeholders import CommonPlaceholdersPlugin
        from lg.template.task_placeholder import TaskPlaceholderPlugin
        
        # Сначала регистрируем базовые плейсхолдеры
        common_plugin = CommonPlaceholdersPlugin(template_ctx)
        registry.register_plugin(common_plugin)
        
        # Затем task-плагин
        task_plugin = TaskPlaceholderPlugin(template_ctx)
        registry.register_plugin(task_plugin)
        
        # Создаем фиктивный обработчик для инициализации плагинов
        class DummyHandlers:
            def process_ast_node(self, context): return ""
            def process_section_ref(self, section_ref): return ""
            def parse_next_node(self, context): return None
            def resolve_ast(self, ast, context=""): return ast
        
        # Инициализируем плагины
        registry.initialize_plugins(DummyHandlers())
        
        return registry
    
    def parse_template(self, text: str, registry: TemplateRegistry):
        """Вспомогательная функция для парсинга шаблона."""
        lexer = ContextualLexer(registry)
        tokens = lexer.tokenize(text)
        parser = ModularParser(registry)
        return parser.parse(tokens)
    
    def test_not_a_task_placeholder(self, registry_with_plugin):
        """Проверка что ${tasks} не распознается как task-плейсхолдер."""
        template = "${tasks}"
        ast = self.parse_template(template, registry_with_plugin)
        
        # Должен распарситься как обычный текст или другой плейсхолдер
        # но не как TaskNode
        assert not any(isinstance(node, TaskNode) for node in ast)
    
    def test_malformed_prompt_no_colon(self, registry_with_plugin):
        """Тест с некорректным синтаксисом (отсутствие двоеточия)."""
        template = '${task:prompt"Default"}'
        
        # Должна быть ошибка парсинга
        with pytest.raises(Exception):
            self.parse_template(template, registry_with_plugin)
    
    def test_malformed_prompt_no_quotes(self, registry_with_plugin):
        """Тест с некорректным синтаксисом (отсутствие кавычек)."""
        template = '${task:prompt:Default}'
        
        # Должна быть ошибка парсинга
        with pytest.raises(Exception):
            self.parse_template(template, registry_with_plugin)
    
    def test_escaped_backslash(self, registry_with_plugin):
        """Тест с экранированным обратным слэшем."""
        template = r'${task:prompt:"Path: C:\\Users\\test"}'
        ast = self.parse_template(template, registry_with_plugin)
        
        assert len(ast) == 1
        assert isinstance(ast[0], TaskNode)
        # Должны получить корректный путь с обратными слэшами
        assert ast[0].default_prompt == r"Path: C:\Users\test"
    
    def test_special_characters_in_default(self, registry_with_plugin):
        """Тест со специальными символами в дефолтном значении."""
        template = r'${task:prompt:"Fix: bug #123 (critical) & update docs"}'
        ast = self.parse_template(template, registry_with_plugin)
        
        assert len(ast) == 1
        assert isinstance(ast[0], TaskNode)
        assert ast[0].default_prompt == "Fix: bug #123 (critical) & update docs"
