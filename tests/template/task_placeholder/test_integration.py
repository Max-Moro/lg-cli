"""
Integration tests for task placeholders.

Checks:
- Conditions {% if task %}
- CLI integration (--task, @file, stdin)
- Interaction with other placeholders
"""

from tests.infrastructure import write, write_context, render_template, make_run_options, run_cli, jload


class TestTaskConditionals:
    """Tests for conditions with task."""

    def test_if_task_condition_with_value(self, task_project, task_text_simple):
        """Test condition {% if task %} when task is set."""
        template = """# Context

{% if task %}
## Current Task

${task}
{% endif %}

## Code
${src}
"""
        write_context(task_project, "test", template)

        options = make_run_options(task_text=task_text_simple)
        result = render_template(task_project, "ctx:test", options)

        assert "## Current Task" in result
        assert task_text_simple in result
        assert "def main():" in result
    
    def test_if_task_condition_without_value(self, task_project):
        """Test condition {% if task %} when task is not set."""
        template = """# Context

{% if task %}
## Current Task

${task}
{% endif %}

## Code
${src}
"""
        write_context(task_project, "test", template)

        options = make_run_options()
        result = render_template(task_project, "ctx:test", options)

        # Task block should not be displayed
        assert "## Current Task" not in result
        # But the rest should be
        assert "## Code" in result
        assert "def main():" in result
    
    def test_if_not_task_condition(self, task_project):
        """Test condition {% if NOT task %}."""
        template = """# Context

{% if NOT task %}
_No specific task provided. General overview._
{% endif %}

${src}
"""
        write_context(task_project, "test", template)

        options = make_run_options()
        result = render_template(task_project, "ctx:test", options)

        assert "_No specific task provided" in result
    
    def test_if_not_task_with_value(self, task_project, task_text_simple):
        """Test condition {% if NOT task %} when task is set."""
        template = """# Context

{% if NOT task %}
_No task_
{% endif %}

${src}
"""
        write_context(task_project, "test", template)

        options = make_run_options(task_text=task_text_simple)
        result = render_template(task_project, "ctx:test", options)

        assert "_No task_" not in result
    
    def test_task_with_multiple_conditions(self, task_project, task_text_simple):
        """Test task with other conditions."""
        template = """# Context

{% if task AND tag:review %}
## Task for Review

${task}
{% endif %}

${src}
"""
        write_context(task_project, "test", template)

        # task is set, but tag is not active
        options1 = make_run_options(task_text=task_text_simple)
        result1 = render_template(task_project, "ctx:test", options1)
        assert "## Task for Review" not in result1

        # task is set and tag is active
        options2 = make_run_options(task_text=task_text_simple, extra_tags={"review"})
        result2 = render_template(task_project, "ctx:test", options2)
        assert "## Task for Review" in result2
        assert task_text_simple in result2
    
    def test_task_in_else_branch(self, task_project, task_text_simple):
        """Test task in else branch."""
        template = """# Context

{% if tag:minimal %}
Minimal view
{% else %}
Full view with task: ${task}
{% endif %}
"""
        write_context(task_project, "test", template)

        options = make_run_options(task_text=task_text_simple)
        result = render_template(task_project, "ctx:test", options)

        assert "Full view with task:" in result
        assert task_text_simple in result


class TestTaskCLIIntegration:
    """Tests for CLI integration."""

    def test_cli_render_with_task_arg(self, task_project, task_text_simple):
        """Test rendering via CLI with --task."""
        write_context(task_project, "test", "Task: ${task}")

        result = run_cli(
            task_project,
            "render", "ctx:test",
            "--task", task_text_simple
        )

        assert result.returncode == 0
        assert task_text_simple in result.stdout
    
    def test_cli_render_without_task_arg(self, task_project):
        """Test rendering via CLI without --task."""
        write_context(task_project, "test", "Task: ${task}")

        result = run_cli(task_project, "render", "ctx:test")

        assert result.returncode == 0
        assert "Task: " in result.stdout
    
    def test_cli_render_with_task_from_file(self, task_project, task_text_multiline):
        """Test --task @file."""
        # Create file with task
        task_file = task_project / "current-task.txt"
        write(task_file, task_text_multiline)

        write_context(task_project, "test", "${task}")

        result = run_cli(
            task_project,
            "render", "ctx:test",
            "--task", f"@{task_file.name}"
        )

        assert result.returncode == 0
        assert "Refactoring tasks:" in result.stdout
    
    def test_cli_report_with_task(self, task_project, task_text_simple):
        """Test report command with --task."""
        write_context(task_project, "test", "Task: ${task}")

        result = run_cli(
            task_project,
            "report", "ctx:test",
            "--task", task_text_simple
        )

        assert result.returncode == 0
        data = jload(result.stdout)
        # Check API v4 structure
        assert "target" in data
        assert "protocol" in data
        assert data["protocol"] >= 1
        assert "total" in data
        assert "files" in data


class TestTaskWithOtherPlaceholders:
    """Tests for interaction of task with other placeholders."""

    def test_task_with_section_placeholders(self, task_project, task_text_simple):
        """Test task together with sections."""
        template = """# Context

## Task
${task}

## Documentation
${docs}

## Source
${src}
"""
        write_context(task_project, "test", template)

        options = make_run_options(task_text=task_text_simple)
        result = render_template(task_project, "ctx:test", options)

        assert task_text_simple in result
        assert "Documentation here" in result
        assert "def main():" in result
    
    def test_task_with_template_placeholders(self, task_project, task_text_simple):
        """Test task together with tpl placeholders."""
        write(task_project / "lg-cfg" / "header.tpl.md", "Project Overview")
        template = """${tpl:header}

Task: ${task}

${src}
"""
        write_context(task_project, "test", template)

        options = make_run_options(task_text=task_text_simple)
        result = render_template(task_project, "ctx:test", options)

        assert "Project Overview" in result
        assert task_text_simple in result
        assert "def main():" in result
    
    def test_task_default_with_section(self, task_project):
        """Test task:prompt together with sections."""
        template = """# Context

${task:prompt:"Review the following code"}

${src}
"""
        write_context(task_project, "test", template)

        options = make_run_options()
        result = render_template(task_project, "ctx:test", options)

        assert "Review the following code" in result
        assert "def main():" in result
    
    def test_multiple_different_placeholders(self, task_project, task_text_simple):
        """Test combination of different placeholder types."""
        write(task_project / "lg-cfg" / "intro.tpl.md", "# Introduction\n\nWelcome")

        template = """${tpl:intro}

## Current Task
${task}

## Documentation
${docs}

## Source Code
${src}

## Tests
${tests}
"""
        write_context(task_project, "test", template)

        options = make_run_options(task_text=task_text_simple)
        result = render_template(task_project, "ctx:test", options)

        assert "# Introduction" in result
        assert task_text_simple in result
        assert "Documentation here" in result
        assert "def main():" in result


class TestTaskEdgeCasesIntegration:
    """Edge cases in integration scenarios."""

    def test_task_with_very_long_text(self, task_project):
        """Test with very long task text."""
        long_task = "Task: " + "A" * 10000
        write_context(task_project, "test", "${task}")

        options = make_run_options(task_text=long_task)
        result = render_template(task_project, "ctx:test", options)

        assert long_task in result
    
    def test_task_with_unicode(self, task_project):
        """Test with Unicode characters in task."""
        unicode_task = "Task: fix bug 🐛 in authentication module 🔐"
        write_context(task_project, "test", "${task}")

        options = make_run_options(task_text=unicode_task)
        result = render_template(task_project, "ctx:test", options)

        assert unicode_task in result
    
    def test_nested_conditionals_with_task(self, task_project, task_text_simple):
        """Test nested conditions with task."""
        template = """# Context

{% if tag:debug %}
Debug mode
{% if task %}
Debug task: ${task}
{% endif %}
{% endif %}
"""
        write_context(task_project, "test", template)

        # Without debug tag - nothing is displayed
        options1 = make_run_options(task_text=task_text_simple)
        result1 = render_template(task_project, "ctx:test", options1)
        assert "Debug mode" not in result1

        # With debug tag and task - everything is displayed
        options2 = make_run_options(task_text=task_text_simple, extra_tags={"debug"})
        result2 = render_template(task_project, "ctx:test", options2)
        assert "Debug mode" in result2
        assert "Debug task:" in result2
        assert task_text_simple in result2
