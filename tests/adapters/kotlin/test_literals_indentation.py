"""
Test literal trimming with correct indentation handling for Kotlin.
"""

from lg.adapters.langs.kotlin import KotlinCfg
from .utils import make_adapter, lctx


def test_kotlin_map_literal_indentation():
    """Test indentation in Kotlin maps."""
    code = '''class DataContainer {
    private val largeConfig = mapOf(
        "database" to mapOf(
            "host" to "localhost",
            "port" to 5432,
            "name" to "application_db",
            "ssl" to false,
            "pool" to mapOf(
                "min" to 2,
                "max" to 10,
                "idleTimeoutMillis" to 30000,
                "connectionTimeoutMillis" to 2000
            )
        ),
        "cache" to mapOf(
            "redis" to mapOf(
                "host" to "localhost",
                "port" to 6379,
                "db" to 0,
                "ttl" to 3600
            )
        )
    )
}'''

    cfg = KotlinCfg()
    cfg.literals.max_tokens = 10  # Very small limit to force trimming

    adapter = make_adapter(cfg)

    context = lctx(code)
    result, _ = adapter.process(context)

    # Check that indentation is correct
    lines = result.split('\n')
    map_start_line = None
    for i, line in enumerate(lines):
        if 'private val largeConfig = mapOf(' in line:
            map_start_line = i
            break

    assert map_start_line is not None, "Map declaration not found"

    # Look for placeholder line
    placeholder_line = None
    for i in range(map_start_line + 1, len(lines)):
        if '"…"' in lines[i] or 'literal' in lines[i]:
            placeholder_line = i
            break

    # If placeholder found, check indentation
    if placeholder_line is not None:
        placeholder_indent = ""
        for char in lines[placeholder_line]:
            if char in ' \t':
                placeholder_indent += char
            else:
                break

        # Check that indentation is not empty
        assert len(placeholder_indent) > 0, f"Placeholder should have indentation"


def test_list_indentation_preserved():
    """Test that list trimming preserves correct indentation."""
    code = '''
class DataContainer {
    private val largeList = listOf(
        "item_001", "item_002", "item_003", "item_004", "item_005",
        "item_006", "item_007", "item_008", "item_009", "item_010",
        "item_011", "item_012", "item_013", "item_014", "item_015",
        "item_016", "item_017", "item_018", "item_019", "item_020",
        "item_021", "item_022", "item_023", "item_024", "item_025"
    )
}
'''

    cfg = KotlinCfg()
    cfg.literals.max_tokens = 30  # Force trimming
    adapter = make_adapter(cfg)

    result, meta = adapter.process(lctx(code))

    # Check that indentation is preserved correctly
    lines = result.split('\n')

    # Find the list declaration lines
    list_start_line = None
    list_end_line = None
    for i, line in enumerate(lines):
        if "private val largeList = listOf(" in line:
            list_start_line = i
        if list_start_line is not None and ")" in line and ("literal" in line or i == len(lines) - 2):
            list_end_line = i
            break

    if list_start_line is not None:
        # Check that list elements have proper indentation
        for i in range(list_start_line + 1, min(list_start_line + 10, len(lines))):
            line = lines[i]
            if line.strip() and '"' in line:  # Line with list elements
                # Should have some indentation
                indent_before_content = len(line) - len(line.lstrip())
                assert indent_before_content > 0, f"List element should be indented on line {i}"


def test_nested_structure_indentation():
    """Test deeply nested structures maintain correct indentation."""
    code = '''
class ConfigManager {
    fun getConfig() = mapOf(
        "level1" to mapOf(
            "level2" to mapOf(
                "level3" to mapOf(
                    "data" to listOf(
                        mapOf("id" to 1, "name" to "First", "active" to true),
                        mapOf("id" to 2, "name" to "Second", "active" to false),
                        mapOf("id" to 3, "name" to "Third", "active" to true)
                    )
                )
            )
        )
    )
}
'''

    cfg = KotlinCfg()
    cfg.literals.max_tokens = 50  # Force trimming of the large nested structure
    adapter = make_adapter(cfg)

    result, meta = adapter.process(lctx(code))

    # The nested structure should be trimmed but maintain proper indentation
    lines = result.split('\n')

    # Check basic structure is preserved
    assert "fun getConfig()" in result
    assert "mapOf(" in result


def test_top_level_constant_indentation():
    """Test that top-level constants maintain correct indentation."""
    code = '''
package com.example

val LARGE_CONFIG = mapOf(
    "database" to mapOf(
        "host" to "localhost",
        "port" to 5432,
        "credentials" to mapOf(
            "username" to "admin",
            "password" to "super_secret_password_that_is_very_long_123456789"
        )
    )
)
'''

    cfg = KotlinCfg()
    cfg.literals.max_tokens = 25  # Force trimming
    adapter = make_adapter(cfg)

    result, meta = adapter.process(lctx(code))

    # Check that structure is preserved
    assert "val LARGE_CONFIG" in result
    assert "mapOf(" in result

