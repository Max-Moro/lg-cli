"""
Tests for processing task placeholders.

Checks correct processing and substitution of values:
- With task_text set in RunOptions
- Without task_text (empty string)
- With default value
- Combinations of different cases
"""

from tests.infrastructure import write, write_context, render_template, make_run_options


class TestTaskPlaceholderProcessing:
    """Tests for processing task placeholders."""

    def test_simple_task_with_value(self, task_project, task_text_simple):
        """Test simple ${task} with value set."""
        write_context(task_project, "test", "Task: ${task}")
        
        options = make_run_options(task_text=task_text_simple)
        
        result = render_template(task_project, "ctx:test", options)
        
        assert task_text_simple in result
        assert "Task: Implement caching" in result
    
    def test_simple_task_without_value(self, task_project):
        """Test simple ${task} without value set."""
        write_context(task_project, "test", "Task: ${task}\nEnd")

        options = make_run_options()
        # task_text not set (None)

        result = render_template(task_project, "ctx:test", options)

        # Should be empty string instead of placeholder
        assert "Task: \nEnd" in result
    
    def test_task_with_default_used(self, task_project):
        """Test ${task:prompt:"..."} when task_text is not set."""
        template = '${task:prompt:"No specific task"}'
        write_context(task_project, "test", template)

        options = make_run_options()
        # task_text not set

        result = render_template(task_project, "ctx:test", options)

        assert "No specific task" in result
    
    def test_task_with_default_overridden(self, task_project, task_text_simple):
        """Test ${task:prompt:"..."} when task_text is set."""
        template = '${task:prompt:"Default task"}'
        write_context(task_project, "test", template)

        options = make_run_options(task_text=task_text_simple)

        result = render_template(task_project, "ctx:test", options)

        # Should use task_text, not default
        assert task_text_simple in result
        assert "Default task" not in result
    
    def test_multiline_task_text(self, task_project, task_text_multiline):
        """Test with multiline task text."""
        write_context(task_project, "test", "## Task\n\n${task}\n\n## Notes")
        
        options = make_run_options(task_text=task_text_multiline)
        
        result = render_template(task_project, "ctx:test", options)
        
        assert "Refactoring tasks:" in result
        assert "Extract common utilities" in result
        assert "Add type hints" in result
    
    def test_task_with_special_characters(self, task_project, task_text_with_quotes):
        """Test with special characters in task text."""
        write_context(task_project, "test", "${task}")
        
        options = make_run_options(task_text=task_text_with_quotes)
        
        result = render_template(task_project, "ctx:test", options)
        
        assert 'Fix "critical" bug' in result
    
    def test_multiple_task_placeholders_same_value(self, task_project, task_text_simple):
        """Test with multiple task placeholders in one template."""
        template = """# Overview
${task}

## Details
${task}
"""
        write_context(task_project, "test", template)

        options = make_run_options(task_text=task_text_simple)

        result = render_template(task_project, "ctx:test", options)

        # Both occurrences should be replaced
        assert result.count(task_text_simple) == 2
    
    def test_task_placeholder_in_template(self, task_project, task_text_simple):
        """Test task placeholder in nested template."""
        write(task_project / "lg-cfg" / "header.tpl.md", "Task: ${task}")
        write_context(task_project, "test", "${tpl:header}\n\n${src}")
        
        options = make_run_options(task_text=task_text_simple)
        
        result = render_template(task_project, "ctx:test", options)
        
        assert task_text_simple in result
    
    def test_empty_task_text(self, task_project):
        """Test with empty string in task_text."""
        write_context(task_project, "test", "Task: ${task}\nEnd")

        options = make_run_options(task_text="")

        result = render_template(task_project, "ctx:test", options)

        # Empty string should be treated as no task
        assert "Task: \nEnd" in result
    
    def test_whitespace_only_task_text(self, task_project):
        """Test with task_text containing only whitespace."""
        write_context(task_project, "test", "Task: ${task}\nEnd")

        options = make_run_options(task_text="   \n\t  ")

        result = render_template(task_project, "ctx:test", options)

        # Whitespace-only should be treated as no task
        assert "Task: \nEnd" in result


class TestTaskPlaceholderWithSections:
    """Tests for task placeholders in context with sections."""

    def test_task_before_section(self, task_project, task_text_simple):
        """Test task placeholder before section."""
        template = """# Context

## Task
${task}

## Source Code
${src}
"""
        write_context(task_project, "test", template)
        
        options = make_run_options(task_text=task_text_simple)
        
        result = render_template(task_project, "ctx:test", options)
        
        assert task_text_simple in result
        assert "def main():" in result
    
    def test_task_after_section(self, task_project, task_text_simple):
        """Test task placeholder after section."""
        template = """# Context

## Source Code
${src}

## Current Task
${task}
"""
        write_context(task_project, "test", template)

        options = make_run_options(task_text=task_text_simple)

        result = render_template(task_project, "ctx:test", options)

        assert task_text_simple in result
        assert "def main():" in result
        # Task should be after source
        task_pos = result.find(task_text_simple)
        code_pos = result.find("def main():")
        assert task_pos > code_pos
    
    def test_task_between_sections(self, task_project, task_text_simple):
        """Test task placeholder between sections."""
        template = """# Context

${docs}

## Task
${task}

${src}
"""
        write_context(task_project, "test", template)
        
        options = make_run_options(task_text=task_text_simple)
        
        result = render_template(task_project, "ctx:test", options)
        
        assert task_text_simple in result
        assert "Documentation here" in result
        assert "def main():" in result


class TestTaskPlaceholderEdgeCases:
    """Tests for edge cases in processing."""

    def test_task_with_markdown_formatting(self, task_project):
        """Test with Markdown formatting in task_text."""
        task_text = """# Main Task

- **Priority 1**: Fix bug
- **Priority 2**: Add tests

_Note_: See issue #123
"""
        write_context(task_project, "test", "${task}")
        
        options = make_run_options(task_text=task_text)
        
        result = render_template(task_project, "ctx:test", options)
        
        assert "# Main Task" in result
        assert "**Priority 1**" in result
        assert "_Note_" in result
    
    def test_default_with_escape_sequences(self, task_project):
        """Test default value with escape sequences."""
        template = r'${task:prompt:"Line 1\nLine 2\tTabbed"}'
        write_context(task_project, "test", template)

        options = make_run_options()
        # task_text not set

        result = render_template(task_project, "ctx:test", options)

        assert "Line 1" in result
        assert "Line 2" in result
        # Check that escape sequences are properly processed
        assert "\n" in result
        assert "\t" in result
    
    def test_task_none_vs_empty_string(self, task_project):
        """Test difference between None and empty string."""
        template = '${task:prompt:"Default"}'
        write_context(task_project, "test", template)

        # Case 1: task_text = None (default)
        options1 = make_run_options()
        result1 = render_template(task_project, "ctx:test", options1)
        assert "Default" in result1

        # Case 2: task_text = ""
        options2 = make_run_options(task_text="")
        result2 = render_template(task_project, "ctx:test", options2)
        # Empty string should also use default
        assert "Default" in result2
