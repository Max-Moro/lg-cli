"""
Тесты для файловых меток в отрендеренном контенте.

Проверяют:
- Интеграцию меток в fenced-блоки (каждый файл в своем блоке)
- Различные режимы path_labels (scope_relative, relative, basename)
- Корректность меток при разных структурах проекта
"""

from pathlib import Path

from tests.infrastructure import (
    write_source_file, write_markdown,
    create_sections_yaml, create_template,
    make_engine
)


class TestFileLabelIntegration:
    """Тесты интеграции файловых меток в отрендеренный контент."""

    def test_python_files_have_individual_fence_blocks_with_labels(self, tmp_path: Path):
        """Каждый Python файл должен быть в своем fenced-блоке с меткой."""
        root = tmp_path
        
        # Создаем Python файлы
        write_source_file(root / "src" / "alpha.py", "def alpha(): pass")
        write_source_file(root / "src" / "beta.py", "def beta(): pass")
        
        # Конфигурация секции
        create_sections_yaml(root, {
            "python-src": {
                "extensions": [".py"],
                "path_labels": "relative",
                "filters": {
                    "mode": "allow",
                    "allow": ["/src/**"]
                }
            }
        })
        
        # Контекст
        create_template(root, "test", "${python-src}", template_type="ctx")
        
        # Рендерим
        engine = make_engine(root)
        result = engine.render_context("test")
        
        # Проверяем: два отдельных fenced-блока с метками
        assert "```python:src/alpha.py" in result
        assert "```python:src/beta.py" in result
        
        # Проверяем, что каждый файл в своем блоке (закрывающие ```)
        assert result.count("```python:") == 2
        assert result.count("```\n") >= 2  # как минимум 2 закрывающих блока

    def test_markdown_files_no_fence_blocks(self, tmp_path: Path):
        """Markdown файлы без fenced-блоков только когда ВСЕ файлы - markdown."""
        root = tmp_path
        
        # Создаем ТОЛЬКО Markdown файлы
        write_markdown(root / "docs" / "intro.md", "Introduction", "Some intro text")
        write_markdown(root / "docs" / "guide.md", "Guide", "Some guide text")
        
        # Конфигурация секции (ТОЛЬКО .md)
        create_sections_yaml(root, {
            "docs": {
                "extensions": [".md"],
                "markdown": {"max_heading_level": 2},
                "path_labels": "relative",
                "filters": {
                    "mode": "allow",
                    "allow": ["/docs/**"]
                }
            }
        })
        
        # Контекст
        create_template(root, "test", "${docs}", template_type="ctx")
        
        # Рендерим
        engine = make_engine(root)
        result = engine.render_context("test")
        
        # Проверяем: НЕТ fenced-блоков для markdown
        assert "```markdown" not in result
        assert "```" not in result
        
        # Контент присутствует напрямую (порядок: алфавитный)
        assert "## Guide" in result
        assert "Some guide text" in result
        assert "## Introduction" in result
        assert "Some intro text" in result
        
        # Проверяем порядок (guide идёт перед intro - алфавитный)
        guide_pos = result.find("## Guide")
        intro_pos = result.find("## Introduction")
        assert guide_pos < intro_pos


class TestPathLabelsMode:
    """Тесты различных режимов отображения меток."""

    def test_path_labels_relative(self, tmp_path: Path):
        """Режим 'relative': полный путь относительно корня репо."""
        root = tmp_path
        
        # Создаем файлы в разных папках
        write_source_file(root / "pkg" / "core" / "engine.py", "# Engine")
        write_source_file(root / "pkg" / "utils" / "helpers.py", "# Helpers")
        
        # Конфигурация
        create_sections_yaml(root, {
            "src": {
                "extensions": [".py"],
                "path_labels": "relative",
                "filters": {
                    "mode": "allow",
                    "allow": ["/pkg/**"]
                }
            }
        })
        
        create_template(root, "test", "${src}", template_type="ctx")
        
        # Рендерим
        engine = make_engine(root)
        result = engine.render_context("test")
        
        # Проверяем полные относительные пути
        assert "```python:pkg/core/engine.py" in result
        assert "```python:pkg/utils/helpers.py" in result

    def test_path_labels_basename(self, tmp_path: Path):
        """Режим 'basename': минимальный уникальный суффикс."""
        root = tmp_path
        
        # Создаем файлы с одинаковыми именами в разных папках
        write_source_file(root / "pkg" / "a" / "utils.py", "# Utils A")
        write_source_file(root / "pkg" / "b" / "utils.py", "# Utils B")
        write_source_file(root / "pkg" / "unique.py", "# Unique")
        
        # Конфигурация
        create_sections_yaml(root, {
            "src": {
                "extensions": [".py"],
                "path_labels": "basename",
                "filters": {
                    "mode": "allow",
                    "allow": ["/pkg/**"]
                }
            }
        })
        
        create_template(root, "test", "${src}", template_type="ctx")
        
        # Рендерим
        engine = make_engine(root)
        result = engine.render_context("test")
        
        # Проверяем: для utils.py - минимальные уникальные суффиксы (одна директория)
        assert "```python:a/utils.py" in result
        assert "```python:b/utils.py" in result
        
        # Для уникального файла - только basename
        assert "```python:unique.py" in result

    def test_path_labels_scope_relative(self, tmp_path: Path):
        """Режим 'scope_relative': относительно scope_dir (для локальных секций)."""
        root = tmp_path
        
        # Создаем файлы
        write_source_file(root / "app" / "web" / "server.py", "# Server")
        write_source_file(root / "app" / "web" / "routes.py", "# Routes")
        
        # Конфигурация в корневом lg-cfg
        create_sections_yaml(root, {
            "web-src": {
                "extensions": [".py"],
                "path_labels": "scope_relative",
                "filters": {
                    "mode": "allow",
                    "allow": ["/app/web/**"]
                }
            }
        })
        
        create_template(root, "test", "${web-src}", template_type="ctx")
        
        # Рендерим из корня (origin = "self")
        engine = make_engine(root)
        result = engine.render_context("test")
        
        # Для корневого скоупа scope_relative эквивалентно relative
        assert "```python:app/web/server.py" in result
        assert "```python:app/web/routes.py" in result


class TestComplexProjectStructure:
    """Тесты для сложных структур проектов."""

    def test_deep_nested_structure_with_basename(self, tmp_path: Path):
        """Глубокая вложенность с режимом basename."""
        root = tmp_path
        
        # Создаем глубоко вложенную структуру
        write_source_file(root / "pkg" / "core" / "engine" / "runtime.py", "# Runtime")
        write_source_file(root / "pkg" / "plugins" / "loader" / "runtime.py", "# Plugin Runtime")
        write_source_file(root / "pkg" / "utils" / "helpers.py", "# Helpers")
        
        # Конфигурация
        create_sections_yaml(root, {
            "all-src": {
                "extensions": [".py"],
                "path_labels": "basename",
                "filters": {
                    "mode": "allow",
                    "allow": ["/pkg/**"]
                }
            }
        })
        
        create_template(root, "test", "${all-src}", template_type="ctx")
        
        # Рендерим
        engine = make_engine(root)
        result = engine.render_context("test")
        
        # Проверяем минимальные уникальные суффиксы для runtime.py
        # Должны различаться по папкам
        lines = result.split("\n")
        runtime_labels = [line for line in lines if "runtime.py" in line and line.startswith("```python:")]
        
        assert len(runtime_labels) == 2
        # Должны быть разные метки
        assert runtime_labels[0] != runtime_labels[1]
        
        # helpers.py должен быть с минимальным суффиксом
        assert "```python:helpers.py" in result

    def test_mixed_languages_separate_fence_blocks(self, tmp_path: Path):
        """Смешанные языки: каждый файл в своем блоке со своим языком."""
        root = tmp_path
        
        # Создаем файлы разных языков
        write_source_file(root / "src" / "app.py", "# Python app", language="python")
        write_source_file(root / "src" / "types.ts", "// TypeScript types", language="typescript")
        write_markdown(root / "src" / "README.md", "Readme", "Documentation")
        
        # Конфигурация для всех типов
        create_sections_yaml(root, {
            "all-src": {
                "extensions": [".py", ".ts", ".md"],
                "path_labels": "relative",
                "markdown": {"max_heading_level": 2},
                "filters": {
                    "mode": "allow",
                    "allow": ["/src/**"]
                }
            }
        })
        
        create_template(root, "test", "${all-src}", template_type="ctx")
        
        # Рендерим
        engine = make_engine(root)
        result = engine.render_context("test")
        
        # ВАЖНО: Markdown тоже в fence-блоке (все файлы в индивидуальных блоках)
        assert "```markdown:src/README.md" in result
        assert "```python:src/app.py" in result
        assert "```typescript:src/types.ts" in result
        
        # Проверяем наличие контента
        assert "Documentation" in result
        assert "## Readme" in result


class TestEdgeCases:
    """Тесты граничных случаев."""

    def test_single_file_section(self, tmp_path: Path):
        """Секция с одним файлом."""
        root = tmp_path
        
        write_source_file(root / "main.py", "# Main application")
        
        create_sections_yaml(root, {
            "main": {
                "extensions": [".py"],
                "path_labels": "basename",
                "filters": {
                    "mode": "allow",
                    "allow": ["/main.py"]
                }
            }
        })
        
        create_template(root, "test", "${main}", template_type="ctx")
        
        # Рендерим
        engine = make_engine(root)
        result = engine.render_context("test")
        
        # Проверяем единственный блок
        assert result.count("```python:") == 1
        assert "```python:main.py" in result

    def test_empty_section_no_labels(self, tmp_path: Path):
        """Пустая секция (нет файлов) - нет меток."""
        root = tmp_path
        
        # Создаем секцию, но файлы не соответствуют фильтрам
        write_source_file(root / "other" / "file.py", "# Other")
        
        create_sections_yaml(root, {
            "empty": {
                "extensions": [".py"],
                "path_labels": "relative",
                "filters": {
                    "mode": "allow",
                    "allow": ["/nonexistent/**"]
                }
            }
        })
        
        create_template(root, "test", "${empty}", template_type="ctx")
        
        # Рендерим
        engine = make_engine(root)
        result = engine.render_context("test")
        
        # Проверяем: нет fenced-блоков
        assert "```python:" not in result
        # Результат должен быть пустым или почти пустым
        assert result.strip() == "" or len(result.strip()) < 10

    def test_files_with_same_basename_different_paths(self, tmp_path: Path):
        """Файлы с одинаковым basename в разных путях."""
        root = tmp_path
        
        # Создаем много файлов с одинаковым именем
        write_source_file(root / "a" / "b" / "c" / "utils.py", "# ABC Utils")
        write_source_file(root / "a" / "b" / "utils.py", "# AB Utils")
        write_source_file(root / "a" / "utils.py", "# A Utils")
        write_source_file(root / "utils.py", "# Root Utils")
        
        create_sections_yaml(root, {
            "all": {
                "extensions": [".py"],
                "path_labels": "basename",
                "filters": {
                    "mode": "allow",
                    "allow": ["/**"]
                }
            }
        })
        
        create_template(root, "test", "${all}", template_type="ctx")
        
        # Рендерим
        engine = make_engine(root)
        result = engine.render_context("test")
        
        # Все 4 файла должны быть в результате
        assert result.count("```python:") == 4
        
        # Метки должны быть уникальными
        lines = result.split("\n")
        labels = [line.strip() for line in lines if line.strip().startswith("```python:")]
        
        assert len(labels) == 4
        assert len(set(labels)) == 4  # Все уникальные


class TestLabelConsistency:
    """Тесты согласованности меток."""

    def test_labels_consistent_across_multiple_renders(self, tmp_path: Path):
        """Метки остаются стабильными при повторном рендеринге."""
        root = tmp_path
        
        # Создаем файлы
        write_source_file(root / "src" / "a.py", "# A")
        write_source_file(root / "src" / "b.py", "# B")
        write_source_file(root / "src" / "c.py", "# C")
        
        create_sections_yaml(root, {
            "src": {
                "extensions": [".py"],
                "path_labels": "basename",
                "filters": {
                    "mode": "allow",
                    "allow": ["/src/**"]
                }
            }
        })
        
        create_template(root, "test", "${src}", template_type="ctx")
        
        # Рендерим дважды
        engine1 = make_engine(root)
        result1 = engine1.render_context("test")
        
        engine2 = make_engine(root)
        result2 = engine2.render_context("test")
        
        # Результаты должны быть идентичными
        assert result1 == result2

    def test_labels_stable_with_file_order_change(self, tmp_path: Path):
        """Метки стабильны независимо от порядка файлов в FS."""
        root = tmp_path
        
        # Создаем файлы (порядок может варьироваться в FS)
        files = [
            root / "src" / "zebra.py",
            root / "src" / "alpha.py",
            root / "src" / "delta.py",
        ]
        
        for f in files:
            write_source_file(f, f"# {f.stem}")
        
        create_sections_yaml(root, {
            "src": {
                "extensions": [".py"],
                "path_labels": "relative",
                "filters": {
                    "mode": "allow",
                    "allow": ["/src/**"]
                }
            }
        })
        
        create_template(root, "test", "${src}", template_type="ctx")
        
        # Рендерим
        engine = make_engine(root)
        result = engine.render_context("test")
        
        # Проверяем, что все файлы присутствуют (порядок по алфавиту благодаря сортировке)
        assert "```python:src/alpha.py" in result
        assert "```python:src/delta.py" in result
        assert "```python:src/zebra.py" in result
        
        # Проверяем порядок (должен быть алфавитный)
        alpha_pos = result.find("```python:src/alpha.py")
        delta_pos = result.find("```python:src/delta.py")
        zebra_pos = result.find("```python:src/zebra.py")
        
        assert alpha_pos < delta_pos < zebra_pos
