"""
Tests for adaptive features in the Markdown adapter.

Tests conditional constructs and comment-instructions
based on HTML comments in Markdown documents.
"""

from __future__ import annotations

import textwrap

import pytest

from .conftest import adaptive_project, make_run_options, render_template, write


def test_markdown_conditional_blocks_basic(adaptive_project):
    """Test basic conditional blocks in Markdown via HTML comments."""
    root = adaptive_project

    # Create Markdown file with conditional blocks
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

    # Create section with templating enabled
    sections_content = textwrap.dedent("""
    docs-adaptive:
      extensions: [".md"]
      markdown:
        max_heading_level: 2
        enable_templating: true
      filters:
        mode: allow
        allow:
          - "/docs/setup.md"
    """).strip() + "\n"

    write(root / "lg-cfg" / "sections.yaml", sections_content)

    # Test without active tags - conditional blocks should not appear
    result1 = render_template(root, "sec:docs-adaptive", make_run_options())

    assert "Project Documentation" in result1
    assert "General Usage" in result1
    assert "This section is always visible" in result1
    assert "Python Setup" not in result1
    assert "TypeScript Setup" not in result1
    assert "pip install" not in result1
    assert "npm install" not in result1

    # Test with active python tag
    result2 = render_template(root, "sec:docs-adaptive", make_run_options(extra_tags={"python"}))

    assert "Project Documentation" in result2
    assert "Python Setup" in result2
    assert "pip install" in result2
    assert "TypeScript Setup" not in result2
    assert "npm install" not in result2
    assert "General Usage" in result2

    # Test with active typescript tag
    result3 = render_template(root, "sec:docs-adaptive", make_run_options(extra_tags={"typescript"}))

    assert "Project Documentation" in result3
    assert "TypeScript Setup" in result3
    assert "npm install" in result3
    assert "Python Setup" not in result3
    assert "pip install" not in result3
    assert "General Usage" in result3


def test_markdown_if_else_blocks(adaptive_project):
    """Test if-else blocks in Markdown."""
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

    # Update section
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

    # Without minimal tag - show else block
    result1 = render_template(root, "sec:guide", make_run_options())

    assert "Development Guide" in result1
    assert "Complete Setup" in result1
    assert "make full-setup" in result1
    assert "Additional Configuration" in result1
    assert "Quick Start" not in result1
    assert "make quick-start" not in result1
    assert "Next Steps" in result1

    # With minimal tag - show if block
    result2 = render_template(root, "sec:guide", make_run_options(extra_tags={"minimal"}))

    assert "Development Guide" in result2
    assert "Quick Start" in result2
    assert "make quick-start" in result2
    assert "Complete Setup" not in result2
    assert "make full-setup" not in result2
    assert "Additional Configuration" not in result2
    assert "Next Steps" in result2


def test_markdown_elif_chains(adaptive_project):
    """Test elif chains in Markdown."""
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
    
    # Test agent tag (first condition)
    result1 = render_template(root, "sec:api-docs", make_run_options(extra_tags={"agent"}))
    assert "Agent Authentication" in result1
    assert "AgentClient" in result1
    assert "extended permissions" in result1
    assert "ReviewClient" not in result1
    assert "BasicClient" not in result1
    assert "StandardClient" not in result1

    # Test review tag (elif)
    result2 = render_template(root, "sec:api-docs", make_run_options(extra_tags={"review"}))
    assert "Review Authentication" in result2
    assert "ReviewClient" in result2
    assert "readonly=True" in result2
    assert "AgentClient" not in result2

    # Test minimal tag (elif)
    result3 = render_template(root, "sec:api-docs", make_run_options(extra_tags={"minimal"}))
    assert "Basic Authentication" in result3
    assert "BasicClient" in result3
    assert "ReviewClient" not in result3

    # Test without tags (else)
    result4 = render_template(root, "sec:api-docs", make_run_options())
    assert "Standard Authentication" in result4
    assert "StandardClient" in result4
    assert "username/password" in result4
    assert "AgentClient" not in result4


def test_markdown_complex_conditions(adaptive_project):
    """Test complex conditions with AND/OR/NOT operators."""
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
    
    # Test AND condition
    result1 = render_template(root, "sec:advanced", make_run_options(extra_tags={"agent", "python"}))
    assert "Python Agent Configuration" in result1
    assert "agent.configure_python_env()" in result1

    result2 = render_template(root, "sec:advanced", make_run_options(extra_tags={"agent"}))  # only agent
    assert "Python Agent Configuration" not in result2

    # Test OR condition
    result3 = render_template(root, "sec:advanced", make_run_options(extra_tags={"tests"}))
    assert "Quality Assurance" in result3
    assert "Enable linting" in result3

    result4 = render_template(root, "sec:advanced", make_run_options(extra_tags={"review"}))
    assert "Quality Assurance" in result4

    # Test NOT condition
    result5 = render_template(root, "sec:advanced", make_run_options())  # without minimal
    assert "Advanced Features" in result5
    assert "Performance Tuning" in result5
    assert "Monitoring Setup" in result5

    result6 = render_template(root, "sec:advanced", make_run_options(extra_tags={"minimal"}))
    assert "Advanced Features" not in result6
    assert "Performance Tuning" not in result6

    # Test TAGSET + NOT combination
    result7 = render_template(root, "sec:advanced", make_run_options(extra_tags={"typescript"}))
    assert "TypeScript Advanced" in result7
    assert "strictMode: true" in result7

    result8 = render_template(root, "sec:advanced", make_run_options(extra_tags={"typescript", "minimal"}))
    assert "TypeScript Advanced" not in result8  # minimal blocks


def test_markdown_comment_instructions(adaptive_project):
    """Test comment instructions in Markdown."""
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

    # Test without tags - comment instructions should be excluded
    result1 = render_template(root, "sec:readme", make_run_options())

    assert "Project README" in result1
    assert "This is the main project documentation" in result1
    assert "Current project features are listed below" in result1

    # Comment instructions should not appear in output
    assert "TODO: Add installation instructions" not in result1
    assert "TODO: Add contribution guidelines" not in result1
    assert "These TODOs are visible in Markdown viewers" not in result1
    assert "NOTE: Remember to update this section" not in result1

    # Conditional blocks should work as usual
    assert "Python Features" not in result1

    # Test with python tag - conditional blocks work, comments excluded
    result2 = render_template(root, "sec:readme", make_run_options(extra_tags={"python"}))

    assert "Python Features" in result2
    assert "Python-specific functionality" in result2
    assert "TODO: Add installation" not in result2
    assert "NOTE: Remember to update" not in result2


def test_markdown_templating_with_regular_drop_rules(adaptive_project):
    """Test interaction of templating with regular drop rules."""
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
    
    # Section with templating and drop rules
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
            template: "> *(Section «{title}» omitted)*"
      filters:
        mode: allow
        allow:
          - "/docs/complete.md"
    """).strip() + "\n")
    
    # Test without tags - templating does not activate blocks, drop rules work
    result1 = render_template(root, "sec:complete-guide", make_run_options())

    assert "Complete Guide" in result1
    assert "Introduction" in result1
    assert "Usage" in result1
    assert "Comprehensive usage documentation" in result1  # else block
    assert "Advanced Usage" in result1

    # Sections should be removed with placeholders
    assert "Download the package" not in result1
    assert "Run installation commands" not in result1
    assert "This section would also be dropped" not in result1
    assert "> *(Section «Installation» omitted)*" in result1 or "omitted" in result1
    assert "> *(Section «License» omitted)*" in result1 or "omitted" in result1

    # Conditional blocks not activated
    assert "Python Setup" not in result1
    assert "Basic usage examples" not in result1

    # Test with tags - templating activates blocks, drop rules work
    result2 = render_template(root, "sec:complete-guide",
                             make_run_options(extra_tags={"python", "minimal"}))

    assert "Python Setup" in result2
    assert "Python-specific setup" in result2
    assert "Basic usage examples" in result2
    assert "Comprehensive usage documentation" not in result2  # if block instead of else
    assert "Advanced Usage" not in result2  # part of else block

    # Drop rules still work
    assert "Download the package" not in result2
    assert "Run installation commands" not in result2
    assert "This section would also be dropped" not in result2
    assert "> *(Section «Installation» omitted)*" in result2 or "omitted" in result2
    assert "> *(Section «License» omitted)*" in result2 or "omitted" in result2


def test_markdown_templating_disabled(adaptive_project):
    """Test disabling templating in Markdown."""
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
    
    # Section with templating disabled
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    no-templating:
      extensions: [".md"]
      markdown:
        enable_templating: false
      filters:
        mode: allow
        allow:
          - "/docs/notemplating.md"
    """).strip() + "\n")

    result = render_template(root, "sec:no-templating", make_run_options(extra_tags={"python"}))

    # HTML comments should remain as-is
    assert "<!-- lg:if tag:python -->" in result
    assert "<!-- lg:endif -->" in result
    assert "<!-- lg:comment:start -->" in result
    assert "<!-- lg:comment:end -->" in result
    assert "This should appear as-is when templating is disabled." in result
    assert "This comment should also appear as-is." in result
    assert "Regular content works normally." in result


def test_markdown_raw_blocks_basic(adaptive_project):
    """Test basic raw blocks in Markdown - suppression of HTML comment processing."""
    root = adaptive_project
    
    markdown_content = textwrap.dedent("""
    # Documentation with Examples
    
    ## Regular Conditional Section
    
    <!-- lg:if tag:python -->
    This Python section WILL be processed by LG.
    <!-- lg:endif -->
    
    ## Example of LG Syntax (Raw Block)
    
    Here is how you use LG conditional syntax in your documents:
    
    <!-- lg:raw:start -->
    <!-- lg:if tag:python -->
    Python-specific content goes here.
    <!-- lg:endif -->
    
    <!-- lg:comment:start -->
    This is a comment visible in Markdown viewers.
    <!-- lg:comment:end -->
    <!-- lg:raw:end -->
    
    The above example shows LG syntax without processing it.
    
    ## Another Regular Section
    
    <!-- lg:if tag:typescript -->
    This TypeScript section WILL be processed.
    <!-- lg:endif -->
    """).strip() + "\n"
    
    write(root / "docs" / "examples.md", markdown_content)
    
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    examples:
      extensions: [".md"]
      markdown:
        enable_templating: true
      filters:
        mode: allow
        allow:
          - "/docs/examples.md"
    """).strip() + "\n")
    
    # Test with python tag - conditional blocks outside raw work, inside raw remain as-is
    result = render_template(root, "sec:examples", make_run_options(extra_tags={"python"}))

    assert "Documentation with Examples" in result
    assert "Regular Conditional Section" in result
    assert "This Python section WILL be processed by LG." in result

    # Inside raw block all HTML comments should remain untouched
    assert "<!-- lg:if tag:python -->" in result
    assert "<!-- lg:endif -->" in result
    assert "<!-- lg:comment:start -->" in result
    assert "<!-- lg:comment:end -->" in result
    assert "Python-specific content goes here." in result
    assert "This is a comment visible in Markdown viewers." in result

    # Conditional blocks outside raw should not show (typescript tag not active)
    assert "This TypeScript section WILL be processed." not in result

    # Test without tags - conditional blocks outside raw don't show, raw block remains
    result2 = render_template(root, "sec:examples", make_run_options())

    assert "Documentation with Examples" in result2
    assert "This Python section WILL be processed by LG." not in result2
    assert "This TypeScript section WILL be processed." not in result2

    # Raw block still present with all HTML comments
    assert "<!-- lg:if tag:python -->" in result2
    assert "<!-- lg:endif -->" in result2


def test_markdown_raw_blocks_nested(adaptive_project):
    """Test nested raw blocks."""
    root = adaptive_project
    
    markdown_content = textwrap.dedent("""
    # Nested Raw Blocks
    
    ## Outer Content
    
    <!-- lg:if tag:docs -->
    This is processed.
    <!-- lg:endif -->
    
    ## Examples Section
    
    <!-- lg:raw:start -->
    ### Example 1: Basic Conditional
    
    <!-- lg:if tag:python -->
    Python code here
    <!-- lg:endif -->
    
    ### Example 2: Nested Raw
    
    <!-- lg:raw:start -->
    This is a nested raw block showing raw syntax:
    <!-- lg:if condition -->
    Nested content
    <!-- lg:endif -->
    <!-- lg:raw:end -->
    
    Back to outer raw block.
    <!-- lg:raw:end -->
    
    ## After Raw
    
    <!-- lg:if tag:typescript -->
    TypeScript content is processed.
    <!-- lg:endif -->
    """).strip() + "\n"
    
    write(root / "docs" / "nested.md", markdown_content)
    
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    nested:
      extensions: [".md"]
      markdown:
        enable_templating: true
      filters:
        mode: allow
        allow:
          - "/docs/nested.md"
    """).strip() + "\n")
    
    result = render_template(root, "sec:nested",
                            make_run_options(extra_tags={"docs", "typescript"}))

    assert "Nested Raw Blocks" in result

    # Conditional blocks outside raw are processed
    assert "This is processed." in result
    assert "TypeScript content is processed." in result

    # Content of outer raw block remains as-is
    assert "<!-- lg:if tag:python -->" in result
    assert "Python code here" in result

    # Nested raw block also remains as-is
    assert "<!-- lg:raw:start -->" in result
    assert "This is a nested raw block showing raw syntax:" in result
    assert "<!-- lg:if condition -->" in result
    assert "Nested content" in result
    assert "<!-- lg:raw:end -->" in result
    assert "Back to outer raw block." in result


def test_markdown_raw_blocks_with_conditional_blocks(adaptive_project):
    """Test interaction of raw blocks with conditional blocks."""
    root = adaptive_project
    
    markdown_content = textwrap.dedent("""
    # Mixed Content
    
    <!-- lg:if tag:show-examples -->
    ## LG Syntax Examples
    
    Below are examples of how to use LG conditional syntax:
    
    <!-- lg:raw:start -->
    ### Example: Simple Condition
    
    ```markdown
    <!-- lg:if tag:python -->
    Python-specific documentation
    <!-- lg:endif -->
    ```
    
    ### Example: If-Else
    
    ```markdown
    <!-- lg:if tag:minimal -->
    Quick start guide
    <!-- lg:else -->
    Complete documentation
    <!-- lg:endif -->
    ```
    <!-- lg:raw:end -->
    
    These examples will not be processed by LG.
    <!-- lg:endif -->
    
    <!-- lg:if tag:python -->
    ## Python Section
    
    This section IS processed and shows only when python tag is active.
    <!-- lg:endif -->
    """).strip() + "\n"
    
    write(root / "docs" / "mixed.md", markdown_content)
    
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    mixed:
      extensions: [".md"]
      markdown:
        enable_templating: true
      filters:
        mode: allow
        allow:
          - "/docs/mixed.md"
    """).strip() + "\n")
    
    # Test with show-examples - outer conditional block active, raw inside it
    result1 = render_template(root, "sec:mixed",
                             make_run_options(extra_tags={"show-examples"}))

    assert "LG Syntax Examples" in result1
    assert "Below are examples" in result1

    # Raw block inside conditional block remains untouched
    assert "<!-- lg:if tag:python -->" in result1
    assert "<!-- lg:endif -->" in result1
    assert "<!-- lg:if tag:minimal -->" in result1
    assert "<!-- lg:else -->" in result1
    assert "Python-specific documentation" in result1
    assert "Quick start guide" in result1

    assert "Python Section" not in result1  # python tag not active

    # Test without show-examples but with python
    result2 = render_template(root, "sec:mixed",
                             make_run_options(extra_tags={"python"}))

    assert "LG Syntax Examples" not in result2  # conditional block not active
    assert "<!-- lg:if tag:python -->" not in result2  # raw block inside inactive condition
    assert "Python Section" in result2
    assert "This section IS processed" in result2

    # Test with all tags
    result3 = render_template(root, "sec:mixed",
                             make_run_options(extra_tags={"show-examples", "python"}))

    assert "LG Syntax Examples" in result3
    assert "<!-- lg:if tag:python -->" in result3  # raw block
    assert "Python Section" in result3  # regular conditional block


def test_markdown_raw_blocks_empty(adaptive_project):
    """Test empty and nearly empty raw blocks."""
    root = adaptive_project

    markdown_content = textwrap.dedent("""
    # Raw Block Edge Cases

    ## Empty Raw Block

    <!-- lg:raw:start -->
    <!-- lg:raw:end -->

    ## Raw Block with Only Whitespace

    <!-- lg:raw:start -->


    <!-- lg:raw:end -->

    ## Raw Block with Only Comments

    <!-- lg:raw:start -->
    <!-- lg:if tag:test -->
    <!-- lg:endif -->
    <!-- lg:raw:end -->

    ## Normal Content

    This is regular content.
    """).strip() + "\n"

    write(root / "docs" / "edge.md", markdown_content)

    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    edge:
      extensions: [".md"]
      markdown:
        enable_templating: true
      filters:
        mode: allow
        allow:
          - "/docs/edge.md"
    """).strip() + "\n")

    result = render_template(root, "sec:edge", make_run_options())

    assert "Raw Block Edge Cases" in result
    assert "Empty Raw Block" in result
    assert "Raw Block with Only Whitespace" in result
    assert "Raw Block with Only Comments" in result
    assert "Normal Content" in result
    assert "This is regular content." in result

    # Comments in raw block should remain
    assert "<!-- lg:if tag:test -->" in result
    assert "<!-- lg:endif -->" in result


def test_markdown_raw_blocks_complex_content(adaptive_project):
    """Test raw blocks with complex content."""
    root = adaptive_project
    
    markdown_content = textwrap.dedent("""
    # Complex Raw Content
    
    ## Documentation Template Example
    
    <!-- lg:raw:start -->
    # Project Title
    
    ## Setup Instructions
    
    <!-- lg:if TAGSET:language:python -->
    ### Python Setup
    ```bash
    pip install -r requirements.txt
    ```
    <!-- lg:elif TAGSET:language:typescript -->
    ### TypeScript Setup
    ```bash
    npm install
    ```
    <!-- lg:else -->
    ### General Setup
    Generic setup instructions.
    <!-- lg:endif -->
    
    ## Advanced Configuration
    
    <!-- lg:if tag:agent AND NOT tag:minimal -->
    Configure agent-specific settings:
    
    ```yaml
    agent:
      enabled: true
      permissions: [read, write, execute]
    ```
    <!-- lg:endif -->
    
    <!-- lg:comment:start -->
    TODO: Add more examples
    TODO: Update configuration section
    <!-- lg:comment:end -->
    <!-- lg:raw:end -->
    
    The above template shows various LG features.
    """).strip() + "\n"
    
    write(root / "docs" / "complex.md", markdown_content)
    
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    complex:
      extensions: [".md"]
      markdown:
        enable_templating: true
      filters:
        mode: allow
        allow:
          - "/docs/complex.md"
    """).strip() + "\n")
    
    result = render_template(root, "sec:complex", make_run_options())

    assert "Complex Raw Content" in result
    assert "Documentation Template Example" in result

    # All HTML comments and markdown inside raw should remain
    assert "<!-- lg:if TAGSET:language:python -->" in result
    assert "<!-- lg:elif TAGSET:language:typescript -->" in result
    assert "<!-- lg:else -->" in result
    assert "<!-- lg:endif -->" in result
    assert "<!-- lg:if tag:agent AND NOT tag:minimal -->" in result
    assert "<!-- lg:comment:start -->" in result
    assert "<!-- lg:comment:end -->" in result

    # Content inside directives should also remain
    assert "### Python Setup" in result
    assert "pip install -r requirements.txt" in result
    assert "### TypeScript Setup" in result
    assert "npm install" in result
    assert "Configure agent-specific settings:" in result
    assert "TODO: Add more examples" in result
    assert "TODO: Update configuration section" in result

    assert "The above template shows various LG features." in result


def test_markdown_raw_blocks_disabled_templating(adaptive_project):
    """Test raw blocks with templating disabled."""
    root = adaptive_project

    markdown_content = textwrap.dedent("""
    # Document with Raw

    <!-- lg:raw:start -->
    <!-- lg:if tag:python -->
    Python content
    <!-- lg:endif -->
    <!-- lg:raw:end -->

    <!-- lg:if tag:typescript -->
    TypeScript content
    <!-- lg:endif -->
    """).strip() + "\n"

    write(root / "docs" / "notemplate_raw.md", markdown_content)

    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    notemplate-raw:
      extensions: [".md"]
      markdown:
        enable_templating: false
      filters:
        mode: allow
        allow:
          - "/docs/notemplate_raw.md"
    """).strip() + "\n")

    result = render_template(root, "sec:notemplate-raw",
                            make_run_options(extra_tags={"python", "typescript"}))

    # With templating disabled ALL HTML comments remain as-is
    assert "<!-- lg:raw:start -->" in result
    assert "<!-- lg:raw:end -->" in result
    assert "<!-- lg:if tag:python -->" in result
    assert "<!-- lg:endif -->" in result
    assert "<!-- lg:if tag:typescript -->" in result

    # All content is present
    assert "Python content" in result
    assert "TypeScript content" in result


def test_markdown_templating_error_handling(adaptive_project):
    """Test error handling in Markdown templating."""
    root = adaptive_project

    # Markdown with syntax errors
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

    # Should raise error when processing invalid template
    with pytest.raises(Exception):  # Specific error type depends on implementation
        render_template(root, "sec:invalid-template", make_run_options())


def test_markdown_raw_blocks_error_unclosed(adaptive_project):
    """Test error handling for unclosed raw block."""
    root = adaptive_project

    invalid_markdown = textwrap.dedent("""
    # Invalid Raw Block

    <!-- lg:raw:start -->
    This raw block is never closed.

    <!-- lg:if tag:python -->
    Python content
    <!-- lg:endif -->

    Missing lg:raw:end
    """).strip() + "\n"

    write(root / "docs" / "invalid_raw.md", invalid_markdown)

    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    invalid-raw:
      extensions: [".md"]
      markdown:
        enable_templating: true
      filters:
        mode: allow
        allow:
          - "/docs/invalid_raw.md"
    """).strip() + "\n")

    # Should raise error when processing unclosed raw block
    with pytest.raises(Exception):
        render_template(root, "sec:invalid-raw", make_run_options())


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
    ("TAGSET:language:python", set(), True),  # empty set -> True
])
def test_markdown_condition_evaluation_parametrized(adaptive_project, condition, active_tags, should_appear):
    """Parametrized test for evaluating various conditions in Markdown."""
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