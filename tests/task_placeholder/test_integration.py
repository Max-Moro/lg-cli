"""
Интеграционные тесты для task-плейсхолдеров.

Проверяет:
- Условия {% if task %}
- CLI интеграцию (--task, @file, stdin)
- Взаимодействие с другими плейсхолдерами
"""

from tests.infrastructure import write, render_template, make_run_options, run_cli, jload


class TestTaskConditionals:
    """Тесты условий с task."""
    
    def test_if_task_condition_with_value(self, task_project, task_text_simple):
        """Тест условия {% if task %} когда task задан."""
        template = """# Context

{% if task %}
## Current Task

${task}
{% endif %}

## Code
${src}
"""
        write(task_project / "lg-cfg" / "test.ctx.md", template)
        
        options = make_run_options(task_text=task_text_simple)
        result = render_template(task_project, "ctx:test", options)
        
        assert "## Current Task" in result
        assert task_text_simple in result
        assert "def main():" in result
    
    def test_if_task_condition_without_value(self, task_project):
        """Тест условия {% if task %} когда task не задан."""
        template = """# Context

{% if task %}
## Current Task

${task}
{% endif %}

## Code
${src}
"""
        write(task_project / "lg-cfg" / "test.ctx.md", template)
        
        options = make_run_options()
        result = render_template(task_project, "ctx:test", options)
        
        # Блок задачи не должен отображаться
        assert "## Current Task" not in result
        # Но остальное должно быть
        assert "## Code" in result
        assert "def main():" in result
    
    def test_if_not_task_condition(self, task_project):
        """Тест условия {% if NOT task %}."""
        template = """# Context

{% if NOT task %}
_No specific task provided. General overview._
{% endif %}

${src}
"""
        write(task_project / "lg-cfg" / "test.ctx.md", template)
        
        options = make_run_options()
        result = render_template(task_project, "ctx:test", options)
        
        assert "_No specific task provided" in result
    
    def test_if_not_task_with_value(self, task_project, task_text_simple):
        """Тест условия {% if NOT task %} когда task задан."""
        template = """# Context

{% if NOT task %}
_No task_
{% endif %}

${src}
"""
        write(task_project / "lg-cfg" / "test.ctx.md", template)
        
        options = make_run_options(task_text=task_text_simple)
        result = render_template(task_project, "ctx:test", options)
        
        assert "_No task_" not in result
    
    def test_task_with_multiple_conditions(self, task_project, task_text_simple):
        """Тест task с другими условиями."""
        template = """# Context

{% if task AND tag:review %}
## Task for Review

${task}
{% endif %}

${src}
"""
        write(task_project / "lg-cfg" / "test.ctx.md", template)
        
        # task задан, но тег не активен
        options1 = make_run_options(task_text=task_text_simple)
        result1 = render_template(task_project, "ctx:test", options1)
        assert "## Task for Review" not in result1
        
        # task задан и тег активен
        options2 = make_run_options(task_text=task_text_simple, extra_tags={"review"})
        result2 = render_template(task_project, "ctx:test", options2)
        assert "## Task for Review" in result2
        assert task_text_simple in result2
    
    def test_task_in_else_branch(self, task_project, task_text_simple):
        """Тест task в ветке else."""
        template = """# Context

{% if tag:minimal %}
Minimal view
{% else %}
Full view with task: ${task}
{% endif %}
"""
        write(task_project / "lg-cfg" / "test.ctx.md", template)
        
        options = make_run_options(task_text=task_text_simple)
        result = render_template(task_project, "ctx:test", options)
        
        assert "Full view with task:" in result
        assert task_text_simple in result


class TestTaskCLIIntegration:
    """Тесты CLI интеграции."""
    
    def test_cli_render_with_task_arg(self, task_project, task_text_simple):
        """Тест рендеринга через CLI с --task."""
        write(task_project / "lg-cfg" / "test.ctx.md", "Task: ${task}")
        
        result = run_cli(
            task_project,
            "render", "ctx:test",
            "--task", task_text_simple
        )
        
        assert result.returncode == 0
        assert task_text_simple in result.stdout
    
    def test_cli_render_without_task_arg(self, task_project):
        """Тест рендеринга через CLI без --task."""
        write(task_project / "lg-cfg" / "test.ctx.md", "Task: ${task}")
        
        result = run_cli(task_project, "render", "ctx:test")
        
        assert result.returncode == 0
        assert "Task: " in result.stdout
    
    def test_cli_render_with_task_from_file(self, task_project, task_text_multiline):
        """Тест --task @file."""
        # Создаем файл с задачей
        task_file = task_project / "current-task.txt"
        write(task_file, task_text_multiline)
        
        write(task_project / "lg-cfg" / "test.ctx.md", "${task}")
        
        result = run_cli(
            task_project,
            "render", "ctx:test",
            "--task", f"@{task_file.name}"
        )
        
        assert result.returncode == 0
        assert "Refactoring tasks:" in result.stdout
    
    def test_cli_report_with_task(self, task_project, task_text_simple):
        """Тест report команды с --task."""
        write(task_project / "lg-cfg" / "test.ctx.md", "Task: ${task}")
        
        result = run_cli(
            task_project,
            "report", "ctx:test",
            "--task", task_text_simple
        )
        
        assert result.returncode == 0
        data = jload(result.stdout)
        assert "target" in data
        assert "sections" in data


class TestTaskWithOtherPlaceholders:
    """Тесты взаимодействия task с другими плейсхолдерами."""
    
    def test_task_with_section_placeholders(self, task_project, task_text_simple):
        """Тест task вместе с секциями."""
        template = """# Context

## Task
${task}

## Documentation
${docs}

## Source
${src}
"""
        write(task_project / "lg-cfg" / "test.ctx.md", template)
        
        options = make_run_options(task_text=task_text_simple)
        result = render_template(task_project, "ctx:test", options)
        
        assert task_text_simple in result
        assert "Documentation here" in result
        assert "def main():" in result
    
    def test_task_with_template_placeholders(self, task_project, task_text_simple):
        """Тест task вместе с tpl-плейсхолдерами."""
        write(task_project / "lg-cfg" / "header.tpl.md", "Project Overview")
        template = """${tpl:header}

Task: ${task}

${src}
"""
        write(task_project / "lg-cfg" / "test.ctx.md", template)
        
        options = make_run_options(task_text=task_text_simple)
        result = render_template(task_project, "ctx:test", options)
        
        assert "Project Overview" in result
        assert task_text_simple in result
        assert "def main():" in result
    
    def test_task_default_with_section(self, task_project):
        """Тест task:prompt вместе с секциями."""
        template = """# Context

${task:prompt:"Review the following code"}

${src}
"""
        write(task_project / "lg-cfg" / "test.ctx.md", template)
        
        options = make_run_options()
        result = render_template(task_project, "ctx:test", options)
        
        assert "Review the following code" in result
        assert "def main():" in result
    
    def test_multiple_different_placeholders(self, task_project, task_text_simple):
        """Тест комбинации различных типов плейсхолдеров."""
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
        write(task_project / "lg-cfg" / "test.ctx.md", template)
        
        options = make_run_options(task_text=task_text_simple)
        result = render_template(task_project, "ctx:test", options)
        
        assert "# Introduction" in result
        assert task_text_simple in result
        assert "Documentation here" in result
        assert "def main():" in result


class TestTaskEdgeCasesIntegration:
    """Граничные случаи в интеграционных сценариях."""
    
    def test_task_with_very_long_text(self, task_project):
        """Тест с очень длинным текстом задачи."""
        long_task = "Task: " + "A" * 10000
        write(task_project / "lg-cfg" / "test.ctx.md", "${task}")
        
        options = make_run_options(task_text=long_task)
        result = render_template(task_project, "ctx:test", options)
        
        assert long_task in result
    
    def test_task_with_unicode(self, task_project):
        """Тест с Unicode символами в задаче."""
        unicode_task = "Задача: исправить баг 🐛 в модуле авторизации 🔐"
        write(task_project / "lg-cfg" / "test.ctx.md", "${task}")
        
        options = make_run_options(task_text=unicode_task)
        result = render_template(task_project, "ctx:test", options)
        
        assert unicode_task in result
    
    def test_nested_conditionals_with_task(self, task_project, task_text_simple):
        """Тест вложенных условий с task."""
        template = """# Context

{% if tag:debug %}
Debug mode
{% if task %}
Debug task: ${task}
{% endif %}
{% endif %}
"""
        write(task_project / "lg-cfg" / "test.ctx.md", template)
        
        # Без debug тега - ничего не показывается
        options1 = make_run_options(task_text=task_text_simple)
        result1 = render_template(task_project, "ctx:test", options1)
        assert "Debug mode" not in result1
        
        # С debug тегом и task - показывается всё
        options2 = make_run_options(task_text=task_text_simple, extra_tags={"debug"})
        result2 = render_template(task_project, "ctx:test", options2)
        assert "Debug mode" in result2
        assert "Debug task:" in result2
        assert task_text_simple in result2
