"""
Тесты для резолвера ссылок шаблонов.

Проверяет работу нового TemplateResolver для федеративной
логики резолвинга адресных ссылок на секции и включения.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from lg.run_context import RunContext
from lg.template.nodes import SectionNode, IncludeNode, TextNode
from lg.template.resolver import TemplateResolver, ResolverError
from lg.types import RunOptions


class TestTemplateResolver:
    """Тесты основного класса TemplateResolver."""
    
    @pytest.fixture
    def mock_run_ctx(self):
        """Создает мок контекста выполнения для тестов."""
        run_ctx = Mock(spec=RunContext)
        run_ctx.root = Path("/test/repo")
        run_ctx.options = RunOptions()
        return run_ctx
    
    @pytest.fixture
    def resolver(self, mock_run_ctx):
        """Создает экземпляр TemplateResolver для тестов."""
        def mock_load_template(cfg_root, name):
            return Path(f"{cfg_root}/{name}.tpl.md"), f"Template content for {name}"
        
        def mock_load_context(cfg_root, name):
            return Path(f"{cfg_root}/{name}.ctx.md"), f"Context content for {name}"
        
        return TemplateResolver(
            mock_run_ctx, 
            validate_paths=False,
            load_template_fn=mock_load_template,
            load_context_fn=mock_load_context
        )
    
    def test_init(self, mock_run_ctx):
        """Тест инициализации TemplateResolver."""
        resolver = TemplateResolver(mock_run_ctx, validate_paths=False)
        
        assert resolver.run_ctx == mock_run_ctx
        assert resolver.repo_root == Path("/test/repo")
        assert resolver.current_cfg_root == Path("/test/repo/lg-cfg")
        assert resolver.validate_paths is False
        assert resolver._resolved_includes == {}
        assert resolver._resolution_stack == []
    
    def test_resolve_section_node_simple(self, resolver):
        """Тест резолвинга простой секции без адресности."""
        section_node = SectionNode(section_name="test_section")
        
        resolved = resolver._resolve_section_node(section_node)
        
        assert resolved.section_name == "test_section"
        assert resolved.resolved_ref is not None
        assert resolved.resolved_ref.name == "test_section"
        assert resolved.resolved_ref.scope_rel == ""  # текущий скоуп
        assert str(resolved.resolved_ref.scope_dir).replace("\\", "/").endswith("/test/repo")
    
    def test_resolve_section_node_with_origin(self, resolver):
        """Тест резолвинга секции с указанием origin."""
        section_node = SectionNode(section_name="@other:test_section")
        
        resolved = resolver._resolve_section_node(section_node)
        
        assert resolved.section_name == "test_section"
        assert resolved.resolved_ref is not None
        assert resolved.resolved_ref.name == "test_section"
        assert resolved.resolved_ref.scope_rel == "other"
        assert str(resolved.resolved_ref.scope_dir).replace("\\", "/").endswith("/test/repo/other")
    
    def test_resolve_section_node_with_bracketed_origin(self, resolver):
        """Тест резолвинга секции с origin в скобках."""
        section_node = SectionNode(section_name="@[my:origin]:test_section")
        
        resolved = resolver._resolve_section_node(section_node)
        
        assert resolved.section_name == "test_section"
        assert resolved.resolved_ref is not None
        assert resolved.resolved_ref.name == "test_section"
        assert resolved.resolved_ref.scope_rel == "my:origin"
        assert str(resolved.resolved_ref.scope_dir).replace("\\", "/").endswith("/test/repo/my:origin")
    
    def test_resolve_include_node_template(self, resolver):
        """Тест резолвинга включения шаблона."""
        include_node = IncludeNode(kind="tpl", name="header", origin="self")
        
        resolved = resolver._resolve_include_node(include_node)
        
        assert resolved.kind == "tpl"
        assert resolved.name == "header"
        assert resolved.origin == "self"
        assert resolved.children is not None
        assert len(resolved.children) == 1
    
    def test_resolve_include_node_context(self, resolver):
        """Тест резолвинга включения контекста."""
        include_node = IncludeNode(kind="ctx", name="intro", origin="self")
        
        resolved = resolver._resolve_include_node(include_node)
        
        assert resolved.kind == "ctx"
        assert resolved.name == "intro"
        assert resolved.origin == "self"
        assert resolved.children is not None
        assert len(resolved.children) == 1
    
    def test_resolve_include_node_with_origin(self, resolver):
        """Тест резолвинга включения из другого скоупа."""
        include_node = IncludeNode(kind="tpl", name="shared", origin="common")
        
        resolved = resolver._resolve_include_node(include_node)
        
        assert resolved.kind == "tpl"
        assert resolved.name == "shared"
        assert resolved.origin == "common"
        assert resolved.children is not None
    
    def test_resolve_template_references_mixed(self, resolver):
        """Тест резолвинга шаблона с разными типами узлов."""
        ast = [
            TextNode(text="Start"),
            SectionNode(section_name="@other:config"),
            IncludeNode(kind="tpl", name="header", origin="self"),
            TextNode(text="End")
        ]
        
        resolved_ast = resolver.resolve_template_references(ast, "test")
        
        assert len(resolved_ast) == 4
        
        # Текстовые узлы остаются как есть
        assert resolved_ast[0].text == "Start"
        assert resolved_ast[3].text == "End"
        
        # Секция резолвлена
        assert resolved_ast[1].section_name == "config"
        assert resolved_ast[1].resolved_ref.scope_rel == "other"
        
        # Включение резолвлено
        assert resolved_ast[2].kind == "tpl"
        assert resolved_ast[2].children is not None
    
    def test_resolve_include_with_load_error(self, mock_run_ctx):
        """Тест обработки ошибок загрузки включений."""
        def failing_load_template(cfg_root, name):
            raise FileNotFoundError(f"Template {name} not found")
        
        resolver = TemplateResolver(
            mock_run_ctx,
            validate_paths=False,
            load_template_fn=failing_load_template,
            load_context_fn=None
        )
        
        include_node = IncludeNode(kind="tpl", name="missing", origin="self")
        
        with pytest.raises(ResolverError) as exc_info:
            resolver._resolve_include_node(include_node)
        
        assert "Failed to load tpl 'missing'" in str(exc_info.value)
    
    def test_cycle_detection(self, mock_run_ctx):
        """Тест обнаружения циклических включений."""
        def cyclic_load_template(cfg_root, name):
            # level1 включает level2, level2 включает level1
            if name == "level1":
                return Path("level1.tpl.md"), "${tpl:level2}"
            elif name == "level2":
                return Path("level2.tpl.md"), "${tpl:level1}" 
            else:
                return Path(f"{name}.tpl.md"), f"Content for {name}"
        
        resolver = TemplateResolver(
            mock_run_ctx,
            validate_paths=False,
            load_template_fn=cyclic_load_template,
            load_context_fn=None
        )
        
        include_node = IncludeNode(kind="tpl", name="level1", origin="self")
        
        with pytest.raises(ResolverError) as exc_info:
            resolver._resolve_include_node(include_node)
        
        assert "Circular include detected" in str(exc_info.value)
    
    def test_caching_prevents_duplicate_loading(self, mock_run_ctx):
        """Тест кэширования предотвращает повторную загрузку."""
        load_count = 0
        
        def counting_load_template(cfg_root, name):
            nonlocal load_count
            load_count += 1
            return Path(f"{name}.tpl.md"), f"Template {name} (load #{load_count})"
        
        resolver = TemplateResolver(
            mock_run_ctx,
            validate_paths=False,
            load_template_fn=counting_load_template,
            load_context_fn=None
        )
        
        # Резолвим один и тот же include дважды
        include_node = IncludeNode(kind="tpl", name="cached", origin="self")
        
        result1 = resolver._resolve_include_node(include_node)
        result2 = resolver._resolve_include_node(include_node)
        
        # Функция должна быть вызвана только один раз (кэширование работает)
        assert load_count == 1
        
        # Результаты должны иметь children
        assert result1.children is not None
        assert result2.children is not None
        assert result1.children == result2.children  # Один и тот же объект из кэша