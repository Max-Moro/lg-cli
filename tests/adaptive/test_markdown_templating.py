"""
Тесты адаптивных возможностей в Markdown-адаптере.

Проверяет работу условных конструкций и комментариев-инструкций
на базе HTML-комментариев в Markdown-документах.
"""

from __future__ import annotations

import textwrap
import pytest

from .conftest import (
    adaptive_project, make_run_options, render_template,
    TagConfig, TagSetConfig, create_tags_yaml, write
)


def test_markdown_conditional_blocks_basic(adaptive_project):
    """Тест базовых условных блоков в Markdown через HTML-комментарии."""
    root = adaptive_project
    
    # Создаем Markdown-файл с условными блоками
    markdown_content = textwrap.dedent("""
    # Project Documentation
    
    This is common documentation for all users.
    
    <!-- lg:if tag:python -->
    ## Python Setup
    
    ```bash
    pip install -r requirements.txt
    ```
    
    For Python development, make sure you have Python 3.10+.
    <!-- lg:endif -->
    
    <!-- lg:if tag:typescript -->
    ## TypeScript Setup
    
    ```bash
    npm install
    ```
    
    For TypeScript development, run `npm run dev`.
    <!-- lg:endif -->
    
    ## General Usage
    
    This section is always visible.
    """).strip() + "\n"
    
    write(root / "docs" / "setup.md", markdown_content)
    
    # Создаем секцию с включенной шаблонизацией
    sections_content = textwrap.dedent("""
    docs-adaptive:
      extensions: [".md"]
      code_fence: false
      markdown:
        max_heading_level: 2
        enable_templating: true
      filters:
        mode: allow
        allow:
          - "/docs/setup.md"
    """).strip() + "\n"
    
    write(root / "lg-cfg" / "sections.yaml", sections_content)
    
    # Тест без активных тегов - условные блоки не должны появиться
    result1 = render_template(root, "sec:docs-adaptive", make_run_options())
    
    assert "Project Documentation" in result1
    assert "General Usage" in result1
    assert "This section is always visible" in result1
    assert "Python Setup" not in result1
    assert "TypeScript Setup" not in result1
    assert "pip install" not in result1
    assert "npm install" not in result1
    
    # Тест с активным тегом python
    result2 = render_template(root, "sec:docs-adaptive", make_run_options(extra_tags={"python"}))
    
    assert "Project Documentation" in result2
    assert "Python Setup" in result2
    assert "pip install" in result2
    assert "TypeScript Setup" not in result2
    assert "npm install" not in result2
    assert "General Usage" in result2
    
    # Тест с активным тегом typescript
    result3 = render_template(root, "sec:docs-adaptive", make_run_options(extra_tags={"typescript"}))
    
    assert "Project Documentation" in result3
    assert "TypeScript Setup" in result3
    assert "npm install" in result3
    assert "Python Setup" not in result3
    assert "pip install" not in result3
    assert "General Usage" in result3


def test_markdown_if_else_blocks(adaptive_project):
    """Тест блоков if-else в Markdown."""
    root = adaptive_project
    
    markdown_content = textwrap.dedent("""
    # Development Guide
    
    <!-- lg:if tag:minimal -->
    ## Quick Start
    
    Minimal setup for getting started quickly.
    
    ```bash
    make quick-start
    ```
    <!-- lg:else -->
    ## Complete Setup
    
    Full development environment setup with all tools.
    
    ```bash
    make full-setup
    make install-dev-tools
    make configure-environment
    ```
    
    ### Additional Configuration
    
    Configure your IDE and debugging tools.
    <!-- lg:endif -->
    
    ## Next Steps
    
    Continue with the development process.
    """).strip() + "\n"
    
    write(root / "docs" / "guide.md", markdown_content)
    
    # Обновляем секцию
    sections_content = textwrap.dedent("""
    guide:
      extensions: [".md"]
      markdown:
        enable_templating: true
      filters:
        mode: allow
        allow:
          - "/docs/guide.md"
    """).strip() + "\n"
    
    write(root / "lg-cfg" / "sections.yaml", sections_content)
    
    # Без тега minimal - показываем else блок
    result1 = render_template(root, "sec:guide", make_run_options())
    
    assert "Development Guide" in result1
    assert "Complete Setup" in result1
    assert "make full-setup" in result1
    assert "Additional Configuration" in result1
    assert "Quick Start" not in result1
    assert "make quick-start" not in result1
    assert "Next Steps" in result1
    
    # С тегом minimal - показываем if блок
    result2 = render_template(root, "sec:guide", make_run_options(extra_tags={"minimal"}))
    
    assert "Development Guide" in result2
    assert "Quick Start" in result2
    assert "make quick-start" in result2
    assert "Complete Setup" not in result2
    assert "make full-setup" not in result2
    assert "Additional Configuration" not in result2
    assert "Next Steps" in result2


def test_markdown_elif_chains(adaptive_project):
    """Тест цепочек elif в Markdown."""
    root = adaptive_project
    
    markdown_content = textwrap.dedent("""
    # API Documentation
    
    ## Authentication
    
    <!-- lg:if tag:agent -->
    ### Agent Authentication
    
    For agent-based access, use API keys with extended permissions.
    
    ```python
    client = AgentClient(api_key="...", permissions=["read", "write", "execute"])
    ```
    <!-- lg:elif tag:review -->
    ### Review Authentication
    
    For code review access, use read-only tokens.
    
    ```python
    client = ReviewClient(token="...", readonly=True)
    ```
    <!-- lg:elif tag:minimal -->
    ### Basic Authentication
    
    Simple API key authentication for basic operations.
    
    ```python
    client = BasicClient(api_key="...")
    ```
    <!-- lg:else -->
    ### Standard Authentication
    
    Standard user authentication with username/password.
    
    ```python
    client = StandardClient(username="...", password="...")
    ```
    <!-- lg:endif -->
    
    ## Usage Examples
    
    All authentication methods support the same basic operations.
    """).strip() + "\n"
    
    write(root / "docs" / "api.md", markdown_content)
    
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    api-docs:
      extensions: [".md"]
      markdown:
        enable_templating: true
      filters:
        mode: allow
        allow:
          - "/docs/api.md"
    """).strip() + "\n")
    
    # Тест agent тега (первое условие)
    result1 = render_template(root, "sec:api-docs", make_run_options(extra_tags={"agent"}))
    assert "Agent Authentication" in result1
    assert "AgentClient" in result1
    assert "extended permissions" in result1
    assert "ReviewClient" not in result1
    assert "BasicClient" not in result1
    assert "StandardClient" not in result1
    
    # Тест review тега (elif)
    result2 = render_template(root, "sec:api-docs", make_run_options(extra_tags={"review"}))
    assert "Review Authentication" in result2
    assert "ReviewClient" in result2
    assert "readonly=True" in result2
    assert "AgentClient" not in result2
    
    # Тест minimal тега (elif)
    result3 = render_template(root, "sec:api-docs", make_run_options(extra_tags={"minimal"}))
    assert "Basic Authentication" in result3
    assert "BasicClient" in result3
    assert "ReviewClient" not in result3
    
    # Тест без тегов (else)
    result4 = render_template(root, "sec:api-docs", make_run_options())
    assert "Standard Authentication" in result4
    assert "StandardClient" in result4
    assert "username/password" in result4
    assert "AgentClient" not in result4


def test_markdown_complex_conditions(adaptive_project):
    """Тест сложных условий с AND/OR/NOT операторами."""
    root = adaptive_project
    
    markdown_content = textwrap.dedent("""
    # Advanced Configuration
    
    <!-- lg:if tag:agent AND tag:python -->
    ## Python Agent Configuration
    
    Configure Python-specific agent settings.
    
    ```python
    agent.configure_python_env()
    ```
    <!-- lg:endif -->
    
    <!-- lg:if tag:tests OR tag:review -->
    ## Quality Assurance
    
    Settings for testing and code review processes.
    
    - Enable linting
    - Configure test coverage
    <!-- lg:endif -->
    
    <!-- lg:if NOT tag:minimal -->
    ## Advanced Features
    
    Full feature set documentation.
    
    ### Performance Tuning
    
    Optimize for production environments.
    
    ### Monitoring Setup
    
    Configure metrics and alerting.
    <!-- lg:endif -->
    
    <!-- lg:if TAGSET:language:typescript AND NOT tag:minimal -->
    ## TypeScript Advanced
    
    TypeScript-specific advanced configuration.
    
    ```typescript
    const config: AdvancedConfig = {
      strictMode: true,
      optimizations: true
    };
    ```
    <!-- lg:endif -->
    """).strip() + "\n"
    
    write(root / "docs" / "advanced.md", markdown_content)
    
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    advanced:
      extensions: [".md"]
      markdown:
        enable_templating: true
      filters:
        mode: allow
        allow:
          - "/docs/advanced.md"
    """).strip() + "\n")
    
    # Тест AND условия
    result1 = render_template(root, "sec:advanced", make_run_options(extra_tags={"agent", "python"}))
    assert "Python Agent Configuration" in result1
    assert "agent.configure_python_env()" in result1
    
    result2 = render_template(root, "sec:advanced", make_run_options(extra_tags={"agent"}))  # только agent
    assert "Python Agent Configuration" not in result2
    
    # Тест OR условия
    result3 = render_template(root, "sec:advanced", make_run_options(extra_tags={"tests"}))
    assert "Quality Assurance" in result3
    assert "Enable linting" in result3
    
    result4 = render_template(root, "sec:advanced", make_run_options(extra_tags={"review"}))
    assert "Quality Assurance" in result4
    
    # Тест NOT условия
    result5 = render_template(root, "sec:advanced", make_run_options())  # без minimal
    assert "Advanced Features" in result5
    assert "Performance Tuning" in result5
    assert "Monitoring Setup" in result5
    
    result6 = render_template(root, "sec:advanced", make_run_options(extra_tags={"minimal"}))
    assert "Advanced Features" not in result6
    assert "Performance Tuning" not in result6
    
    # Тест TAGSET + NOT комбинации
    result7 = render_template(root, "sec:advanced", make_run_options(extra_tags={"typescript"}))
    assert "TypeScript Advanced" in result7
    assert "strictMode: true" in result7
    
    result8 = render_template(root, "sec:advanced", make_run_options(extra_tags={"typescript", "minimal"}))
    assert "TypeScript Advanced" not in result8  # minimal блокирует


def test_markdown_comment_instructions(adaptive_project):
    """Тест комментариев-инструкций в Markdown."""
    root = adaptive_project
    
    markdown_content = textwrap.dedent("""
    # Project README
    
    This is the main project documentation.
    
    <!-- lg:comment:start -->
    TODO: Add installation instructions
    TODO: Add contribution guidelines
    TODO: Update API examples
    
    These TODOs are visible in Markdown viewers but excluded from LG output.
    <!-- lg:comment:end -->
    
    ## Features
    
    Current project features are listed below.
    
    <!-- lg:comment:start -->
    NOTE: Remember to update this section after adding new features
    <!-- lg:comment:end -->
    
    <!-- lg:if tag:python -->
    ### Python Features
    
    Python-specific functionality.
    <!-- lg:endif -->
    """).strip() + "\n"
    
    write(root / "docs" / "readme.md", markdown_content)
    
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    readme:
      extensions: [".md"]
      markdown:
        enable_templating: true
      filters:
        mode: allow
        allow:
          - "/docs/readme.md"
    """).strip() + "\n")
    
    # Тест без тегов - комментарии должны быть исключены
    result1 = render_template(root, "sec:readme", make_run_options())
    
    assert "Project README" in result1
    assert "This is the main project documentation" in result1
    assert "Current project features are listed below" in result1
    
    # Комментарии-инструкции не должны попасть в результат
    assert "TODO: Add installation instructions" not in result1
    assert "TODO: Add contribution guidelines" not in result1
    assert "These TODOs are visible in Markdown viewers" not in result1
    assert "NOTE: Remember to update this section" not in result1
    
    # Условные блоки должны работать как обычно
    assert "Python Features" not in result1
    
    # Тест с тегом python - условные блоки работают, комментарии исключены
    result2 = render_template(root, "sec:readme", make_run_options(extra_tags={"python"}))
    
    assert "Python Features" in result2
    assert "Python-specific functionality" in result2
    assert "TODO: Add installation" not in result2
    assert "NOTE: Remember to update" not in result2


def test_markdown_templating_with_regular_drop_rules(adaptive_project):
    """Тест совместной работы шаблонизации с обычными правилами drop."""
    root = adaptive_project
    
    markdown_content = textwrap.dedent("""
    # Complete Guide
    
    ## Introduction
    
    Welcome to the project guide.
    
    <!-- lg:if tag:python -->
    ## Python Setup
    
    Python-specific setup instructions.
    <!-- lg:endif -->
    
    ## Installation
    
    This section would normally be dropped by drop rules.
    
    1. Download the package
    2. Run installation commands
    
    ## Usage
    
    <!-- lg:if tag:minimal -->
    Basic usage examples.
    <!-- lg:else -->
    Comprehensive usage documentation with examples.
    
    ### Advanced Usage
    
    Detailed advanced scenarios.
    <!-- lg:endif -->
    
    ## License
    
    This section would also be dropped by drop rules.
    """).strip() + "\n"
    
    write(root / "docs" / "complete.md", markdown_content)
    
    # Секция с шаблонизацией и правилами drop
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    complete-guide:
      extensions: [".md"]
      markdown:
        enable_templating: true
        max_heading_level: 2
        drop:
          sections:
            - match: { kind: text, pattern: "Installation" }
              reason: "user-facing install guide"
            - match: { kind: text, pattern: "License" }
              reason: "legal text not needed in prompts"
          placeholder:
            mode: summary
            template: "> *(Раздел «{title}» опущен)*"
      filters:
        mode: allow
        allow:
          - "/docs/complete.md"
    """).strip() + "\n")
    
    # Тест без тегов - шаблонизация не активирует блоки, drop правила работают
    result1 = render_template(root, "sec:complete-guide", make_run_options())
    
    assert "Complete Guide" in result1
    assert "Introduction" in result1
    assert "Usage" in result1
    assert "Comprehensive usage documentation" in result1  # else блок
    assert "Advanced Usage" in result1
    
    # Разделы должны быть удалены с плейсхолдерами
    assert "Download the package" not in result1
    assert "Run installation commands" not in result1
    assert "This section would also be dropped" not in result1
    assert "*(Раздел «Installation» опущен)*" in result1
    assert "*(Раздел «License» опущен)*" in result1
    
    # Условные блоки не активированы
    assert "Python Setup" not in result1
    assert "Basic usage examples" not in result1
    
    # Тест с тегами - шаблонизация активирует блоки, drop правила работают
    result2 = render_template(root, "sec:complete-guide", 
                             make_run_options(extra_tags={"python", "minimal"}))
    
    assert "Python Setup" in result2
    assert "Python-specific setup" in result2
    assert "Basic usage examples" in result2
    assert "Comprehensive usage documentation" not in result2  # if блок вместо else
    assert "Advanced Usage" not in result2  # часть else блока
    
    # Drop правила все еще работают
    assert "Download the package" not in result2
    assert "Run installation commands" not in result2
    assert "This section would also be dropped" not in result2
    assert "*(Раздел «Installation» опущен)*" in result2
    assert "*(Раздел «License» опущен)*" in result2


def test_markdown_templating_disabled(adaptive_project):
    """Тест отключения шаблонизации в Markdown."""
    root = adaptive_project
    
    markdown_content = textwrap.dedent("""
    # Documentation
    
    <!-- lg:if tag:python -->
    This should appear as-is when templating is disabled.
    <!-- lg:endif -->
    
    <!-- lg:comment:start -->
    This comment should also appear as-is.
    <!-- lg:comment:end -->
    
    Regular content works normally.
    """).strip() + "\n"
    
    write(root / "docs" / "notemplating.md", markdown_content)
    
    # Секция с отключенной шаблонизацией
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    no-templating:
      extensions: [".md"]
      markdown:
        enable_templating: false  # отключено
      filters:
        mode: allow
        allow:
          - "/docs/notemplating.md"
    """).strip() + "\n")
    
    result = render_template(root, "sec:no-templating", make_run_options(extra_tags={"python"}))
    
    # HTML-комментарии должны остаться как есть
    assert "<!-- lg:if tag:python -->" in result
    assert "<!-- lg:endif -->" in result
    assert "<!-- lg:comment:start -->" in result
    assert "<!-- lg:comment:end -->" in result
    assert "This should appear as-is when templating is disabled." in result
    assert "This comment should also appear as-is." in result
    assert "Regular content works normally." in result


def test_markdown_templating_error_handling(adaptive_project):
    """Тест обработки ошибок в Markdown шаблонизации."""
    root = adaptive_project
    
    # Markdown с синтаксическими ошибками
    invalid_markdown = textwrap.dedent("""
    # Invalid Template
    
    <!-- lg:if tag:python -->
    Python content
    <!-- lg:else -->
    Other content
    <!-- missing lg:endif here -->
    
    This should cause an error.
    """).strip() + "\n"
    
    write(root / "docs" / "invalid.md", invalid_markdown)
    
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    invalid-template:
      extensions: [".md"]
      markdown:
        enable_templating: true
      filters:
        mode: allow
        allow:
          - "/docs/invalid.md"
    """).strip() + "\n")
    
    # Должна возникнуть ошибка при обработке невалидного шаблона
    with pytest.raises(Exception):  # Конкретный тип ошибки зависит от реализации
        render_template(root, "sec:invalid-template", make_run_options())


@pytest.mark.parametrize("condition,active_tags,should_appear", [
    ("tag:python", {"python"}, True),
    ("tag:python", {"javascript"}, False),
    ("tag:python AND tag:tests", {"python", "tests"}, True),
    ("tag:python AND tag:tests", {"python"}, False),
    ("tag:python OR tag:javascript", {"python"}, True),
    ("tag:python OR tag:javascript", {"javascript"}, True),
    ("tag:python OR tag:javascript", {"typescript"}, False),
    ("NOT tag:minimal", set(), True),
    ("NOT tag:minimal", {"minimal"}, False),
    ("TAGSET:language:python", {"python"}, True),
    ("TAGSET:language:python", {"typescript"}, False),
    ("TAGSET:language:python", set(), True),  # пустой набор -> True
])
def test_markdown_condition_evaluation_parametrized(adaptive_project, condition, active_tags, should_appear):
    """Параметризованный тест оценки различных условий в Markdown."""
    root = adaptive_project
    
    markdown_content = f"""# Condition Test

<!-- lg:if {condition} -->
## Conditional Content
This should {'appear' if should_appear else 'not appear'}.
<!-- lg:endif -->

## Always Visible
Regular content.
"""
    
    write(root / "docs" / "condition_test.md", markdown_content)
    
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    condition-test:
      extensions: [".md"]
      markdown:
        enable_templating: true
      filters:
        mode: allow
        allow:
          - "/docs/condition_test.md"
    """).strip() + "\n")
    
    result = render_template(root, "sec:condition-test", make_run_options(extra_tags=active_tags))
    
    assert "Condition Test" in result
    assert "Always Visible" in result
    assert "Regular content" in result
    
    if should_appear:
        assert "Conditional Content" in result
        assert "This should appear" in result
    else:
        assert "Conditional Content" not in result
        assert "This should not appear" not in result