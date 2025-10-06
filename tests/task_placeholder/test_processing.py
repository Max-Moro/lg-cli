"""
Тесты обработки task-плейсхолдеров.

Проверяет корректность обработки и подстановки значений:
- С заданным task_text в RunOptions
- Без task_text (пустая строка)
- С дефолтным значением
- Комбинации различных случаев
"""

from tests.infrastructure import write, render_template, make_run_options


class TestTaskPlaceholderProcessing:
    """Тесты обработки task-плейсхолдеров."""
    
    def test_simple_task_with_value(self, task_project, task_text_simple):
        """Тест простого ${task} с заданным значением."""
        write(task_project / "lg-cfg" / "test.ctx.md", "Task: ${task}")
        
        options = make_run_options(task_text=task_text_simple)
        
        result = render_template(task_project, "ctx:test", options)
        
        assert task_text_simple in result
        assert "Task: Implement caching" in result
    
    def test_simple_task_without_value(self, task_project):
        """Тест простого ${task} без заданного значения."""
        write(task_project / "lg-cfg" / "test.ctx.md", "Task: ${task}\nEnd")
        
        options = make_run_options()
        # task_text не задан (None)
        
        result = render_template(task_project, "ctx:test", options)
        
        # Должна быть пустая строка вместо плейсхолдера
        assert "Task: \nEnd" in result
    
    def test_task_with_default_used(self, task_project):
        """Тест ${task:prompt:"..."} когда task_text не задан."""
        template = '${task:prompt:"No specific task"}'
        write(task_project / "lg-cfg" / "test.ctx.md", template)
        
        options = make_run_options()
        # task_text не задан
        
        result = render_template(task_project, "ctx:test", options)
        
        assert "No specific task" in result
    
    def test_task_with_default_overridden(self, task_project, task_text_simple):
        """Тест ${task:prompt:"..."} когда task_text задан."""
        template = '${task:prompt:"Default task"}'
        write(task_project / "lg-cfg" / "test.ctx.md", template)
        
        options = make_run_options(task_text=task_text_simple)
        
        result = render_template(task_project, "ctx:test", options)
        
        # Должен использоваться task_text, а не дефолт
        assert task_text_simple in result
        assert "Default task" not in result
    
    def test_multiline_task_text(self, task_project, task_text_multiline):
        """Тест с многострочным текстом задачи."""
        write(task_project / "lg-cfg" / "test.ctx.md", "## Task\n\n${task}\n\n## Notes")
        
        options = make_run_options(task_text=task_text_multiline)
        
        result = render_template(task_project, "ctx:test", options)
        
        assert "Refactoring tasks:" in result
        assert "Extract common utilities" in result
        assert "Add type hints" in result
    
    def test_task_with_special_characters(self, task_project, task_text_with_quotes):
        """Тест с спецсимволами в тексте задачи."""
        write(task_project / "lg-cfg" / "test.ctx.md", "${task}")
        
        options = make_run_options(task_text=task_text_with_quotes)
        
        result = render_template(task_project, "ctx:test", options)
        
        assert 'Fix "critical" bug' in result
    
    def test_multiple_task_placeholders_same_value(self, task_project, task_text_simple):
        """Тест с несколькими task-плейсхолдерами в одном шаблоне."""
        template = """# Overview
${task}

## Details
${task}
"""
        write(task_project / "lg-cfg" / "test.ctx.md", template)
        
        options = make_run_options(task_text=task_text_simple)
        
        result = render_template(task_project, "ctx:test", options)
        
        # Оба вхождения должны быть заменены
        assert result.count(task_text_simple) == 2
    
    def test_task_placeholder_in_template(self, task_project, task_text_simple):
        """Тест task-плейсхолдера во вложенном шаблоне."""
        write(task_project / "lg-cfg" / "header.tpl.md", "Task: ${task}")
        write(task_project / "lg-cfg" / "test.ctx.md", "${tpl:header}\n\n${src}")
        
        options = make_run_options(task_text=task_text_simple)
        
        result = render_template(task_project, "ctx:test", options)
        
        assert task_text_simple in result
    
    def test_empty_task_text(self, task_project):
        """Тест с пустой строкой в task_text."""
        write(task_project / "lg-cfg" / "test.ctx.md", "Task: ${task}\nEnd")
        
        options = make_run_options(task_text="")
        
        result = render_template(task_project, "ctx:test", options)
        
        # Пустая строка должна рассматриваться как отсутствие задачи
        assert "Task: \nEnd" in result
    
    def test_whitespace_only_task_text(self, task_project):
        """Тест с task_text содержащим только пробелы."""
        write(task_project / "lg-cfg" / "test.ctx.md", "Task: ${task}\nEnd")
        
        options = make_run_options(task_text="   \n\t  ")
        
        result = render_template(task_project, "ctx:test", options)
        
        # Whitespace-only должен рассматриваться как отсутствие задачи
        assert "Task: \nEnd" in result


class TestTaskPlaceholderWithSections:
    """Тесты task-плейсхолдеров в контексте с секциями."""
    
    def test_task_before_section(self, task_project, task_text_simple):
        """Тест task-плейсхолдера перед секцией."""
        template = """# Context

## Task
${task}

## Source Code
${src}
"""
        write(task_project / "lg-cfg" / "test.ctx.md", template)
        
        options = make_run_options(task_text=task_text_simple)
        
        result = render_template(task_project, "ctx:test", options)
        
        assert task_text_simple in result
        assert "def main():" in result
    
    def test_task_after_section(self, task_project, task_text_simple):
        """Тест task-плейсхолдера после секции."""
        template = """# Context

## Source Code
${src}

## Current Task
${task}
"""
        write(task_project / "lg-cfg" / "test.ctx.md", template)
        
        options = make_run_options(task_text=task_text_simple)
        
        result = render_template(task_project, "ctx:test", options)
        
        assert task_text_simple in result
        assert "def main():" in result
        # Task должен быть после исходников
        task_pos = result.find(task_text_simple)
        code_pos = result.find("def main():")
        assert task_pos > code_pos
    
    def test_task_between_sections(self, task_project, task_text_simple):
        """Тест task-плейсхолдера между секциями."""
        template = """# Context

${docs}

## Task
${task}

${src}
"""
        write(task_project / "lg-cfg" / "test.ctx.md", template)
        
        options = make_run_options(task_text=task_text_simple)
        
        result = render_template(task_project, "ctx:test", options)
        
        assert task_text_simple in result
        assert "Documentation here" in result
        assert "def main():" in result


class TestTaskPlaceholderEdgeCases:
    """Тесты граничных случаев обработки."""
    
    def test_task_with_markdown_formatting(self, task_project):
        """Тест с Markdown-форматированием в task_text."""
        task_text = """# Main Task

- **Priority 1**: Fix bug
- **Priority 2**: Add tests

_Note_: See issue #123
"""
        write(task_project / "lg-cfg" / "test.ctx.md", "${task}")
        
        options = make_run_options(task_text=task_text)
        
        result = render_template(task_project, "ctx:test", options)
        
        assert "# Main Task" in result
        assert "**Priority 1**" in result
        assert "_Note_" in result
    
    def test_default_with_escape_sequences(self, task_project):
        """Тест дефолтного значения с escape-последовательностями."""
        template = r'${task:prompt:"Line 1\nLine 2\tTabbed"}'
        write(task_project / "lg-cfg" / "test.ctx.md", template)
        
        options = make_run_options()
        # task_text не задан
        
        result = render_template(task_project, "ctx:test", options)
        
        assert "Line 1" in result
        assert "Line 2" in result
        # Проверяем что escape-последовательности правильно обработаны
        assert "\n" in result
        assert "\t" in result
    
    def test_task_none_vs_empty_string(self, task_project):
        """Тест различия между None и пустой строкой."""
        template = '${task:prompt:"Default"}'
        write(task_project / "lg-cfg" / "test.ctx.md", template)
        
        # Случай 1: task_text = None (по умолчанию)
        options1 = make_run_options()
        result1 = render_template(task_project, "ctx:test", options1)
        assert "Default" in result1
        
        # Случай 2: task_text = ""
        options2 = make_run_options(task_text="")
        result2 = render_template(task_project, "ctx:test", options2)
        # Пустая строка также должна использовать дефолт
        assert "Default" in result2
