"""
Tests for conditional adapter options.

Tests the functionality of conditional `when` blocks in language adapter configuration,
including dynamic behavior changes based on active tags.
"""

from __future__ import annotations

import textwrap

from .conftest import (
    adaptive_project, make_run_options, render_template,
    create_conditional_template, TagConfig, create_tags_yaml,
    write
)


def test_conditional_python_adapter_options(adaptive_project):
    """
    Test conditional Python adapter options via tags.

    Tests the ability to include trivial __init__.py files in listings
    when a special tag is activated.
    """
    root = adaptive_project

    # Add a special tag to manage __init__.py files
    special_tags = {
        "include-inits": TagConfig(
            title="Include __init__.py files",
            description="Show even trivial __init__.py in listings"
        )
    }
    create_tags_yaml(root, global_tags=special_tags, append=True)

    # Create package structure with __init__.py files
    write(root / "src" / "__init__.py", "pass")  # trivial
    write(root / "src" / "package1" / "__init__.py", "pass")  # trivial
    write(root / "src" / "package1" / "module.py", "def func1():\n    return 'package1'\n")
    write(root / "src" / "package2" / "__init__.py", "__version__ = '1.0.0'\n")  # non-trivial
    write(root / "src" / "package2" / "core.py", "def func2():\n    return 'package2'\n")

    # Create two sections: one with conditional option, one without
    sections_content = textwrap.dedent("""
    python-default:
      extensions: [".py"]
      python:
        skip_trivial_inits: true  # standard behavior - skip trivial
      filters:
        mode: allow
        allow:
          - "/src/**"

    python-with-inits:
      extensions: [".py"]
      python:
        skip_trivial_inits: true  # base value
        when:
          - condition: "tag:include-inits"
            skip_trivial_inits: false  # override when tag active
      filters:
        mode: allow
        allow:
          - "/src/**"
    """).strip() + "\n"

    write(root / "lg-cfg" / "sections.yaml", sections_content)

    # Create a template using both sections for comparison
    template_content = """# Conditional Adapter Options Test

## Default Python section (always skips trivial __init__.py)

${python-default}

## Conditional Python section (includes __init__.py when tag active)

${python-with-inits}
"""

    create_conditional_template(root, "adapter-options-test", template_content)

    # Test 1: without active tag - both sections should skip trivial __init__.py
    result1 = render_template(root, "ctx:adapter-options-test", make_run_options())

    # Check that trivial __init__.py are absent in both sections
    init_markers = [
        "python:src/__init__.py",
        "python:src/package1/__init__.py"
    ]
    for marker in init_markers:
        assert marker not in result1, f"Trivial {marker} should be skipped without tag"

        # Non-trivial __init__.py should be present
        assert "python:src/package2/__init__.py" in result1
        assert "__version__ = '1.0.0'" in result1

        # Regular modules should be present
        assert "python:src/package1/module.py" in result1
        assert "python:src/package2/core.py" in result1

    # Test 2: with active tag - only second section should include trivial __init__.py
    options = make_run_options(extra_tags={"include-inits"})
    result2 = render_template(root, "ctx:adapter-options-test", options)

    # In first section (python-default) trivial __init__.py should still be absent
    # In second section (python-with-inits) they should be present

    # Count occurrences of each file
    trivial_init1_count = result2.count("python:src/__init__.py")
    trivial_init2_count = result2.count("python:src/package1/__init__.py")
    nontrivial_init_count = result2.count("python:src/package2/__init__.py")

    # Trivial __init__.py should appear only once (in second section)
    assert trivial_init1_count == 1, f"Expected 1 occurrence of __init__.py, got {trivial_init1_count}"
    assert trivial_init2_count == 1, f"Expected 1 occurrence of package1/__init__.py, got {trivial_init2_count}"

    # Non-trivial should appear twice (in both sections)
    assert nontrivial_init_count == 2, f"Expected 2 occurrences of package2/__init__.py, got {nontrivial_init_count}"


def test_multiple_conditional_adapter_options(adaptive_project):
    """
    Test multiple conditional adapter options.

    Tests combining several conditional rules in one adapter.
    """
    root = adaptive_project
    
    # Add multiple tags to control behavior
    special_tags = {
        "include-inits": TagConfig(title="Include __init__.py"),
        "strip-bodies": TagConfig(title="Strip function bodies"),
        "verbose-mode": TagConfig(title="Verbose mode")
    }
    create_tags_yaml(root, global_tags=special_tags, append=True)

    # Create files with different content
    write(root / "src" / "__init__.py", "pass")
    write(root / "src" / "api.py", textwrap.dedent("""
    def public_function():
        '''Public API function.'''
        # Perform internal logic
        result = internal_logic()
        # Log the result
        log_api_call("public_function", result)
        # Return processed result
        return process_result(result)

    def _internal_function():
        '''Internal function.'''
        # Complex calculations
        data = complex_computation()
        # Validate data
        if not validate_data(data):
            raise ValueError("Invalid data")
        # Process and return
        return transform_data(data)
    """).strip() + "\n")    # Create section with multiple conditional options
    sections_content = textwrap.dedent("""
    adaptive-python:
      extensions: [".py"]
      python:
        skip_trivial_inits: true
        strip_function_bodies: false
        when:
          - condition: "tag:include-inits"
            skip_trivial_inits: false
          - condition: "tag:strip-bodies AND NOT tag:verbose-mode"
            strip_function_bodies: true
          - condition: "tag:verbose-mode"
            strip_function_bodies: false
            skip_trivial_inits: false
      filters:
        mode: allow
        allow:
          - "/src/**"
    """).strip() + "\n"
    
    write(root / "lg-cfg" / "sections.yaml", sections_content)
    
    template_content = """# Multiple Conditional Options Test

${adaptive-python}
"""
    
    create_conditional_template(root, "multiple-options-test", template_content)
    
    # Test 1: include-inits only
    result1 = render_template(root, "ctx:multiple-options-test",
                             make_run_options(extra_tags={"include-inits"}))

    assert "python:src/__init__.py" in result1  # __init__.py included
    assert "def public_function():" in result1  # function bodies preserved
    assert "internal_logic()" in result1

    # Test 2: strip-bodies only (without verbose-mode)
    result2 = render_template(root, "ctx:multiple-options-test",
                             make_run_options(extra_tags={"strip-bodies"}))

    assert "python:src/__init__.py" not in result2  # __init__.py skipped
    assert "def public_function():" in result2     # signatures present
    assert "internal_logic()" not in result2      # function bodies removed

    # Test 3: strip-bodies + verbose-mode (verbose-mode overrides strip-bodies)
    result3 = render_template(root, "ctx:multiple-options-test",
                             make_run_options(extra_tags={"strip-bodies", "verbose-mode"}))

    assert "python:src/__init__.py" in result3     # __init__.py included (verbose-mode)
    assert "def public_function():" in result3    # signatures present
    assert "internal_logic()" in result3          # function bodies preserved (verbose-mode takes priority)

    # Test 4: all three tags (verbose-mode should dominate)
    result4 = render_template(root, "ctx:multiple-options-test",
                             make_run_options(extra_tags={"include-inits", "strip-bodies", "verbose-mode"}))

    assert "python:src/__init__.py" in result4     # __init__.py included
    assert "def public_function():" in result4    # signatures present
    assert "internal_logic()" in result4          # function bodies preserved


def test_conditional_options_with_complex_conditions(adaptive_project):
    """
    Test conditional adapter options with complex conditions.

    Tests AND/OR/NOT operators in adapter conditions.
    """
    root = adaptive_project
    
    # Tags for complex conditions
    complex_tags = {
        "production": TagConfig(title="Production mode"),
        "debug": TagConfig(title="Debug mode"),
        "api-docs": TagConfig(title="API documentation"),
        "internal-docs": TagConfig(title="Internal documentation")
    }
    create_tags_yaml(root, global_tags=complex_tags, append=True)

    # Create files
    write(root / "src" / "__init__.py", "pass")  # trivial
    write(root / "src" / "debug.py", textwrap.dedent("""
    def debug_function():
        '''Debug utility function.'''
        # Print debug information
        print("Debug info")
        # Collect system information
        system_info = collect_system_info()
        # Log details
        log_debug_details(system_info)
        return True

    def production_function():
        '''Production function.'''
        # Process production data
        data = get_production_data()
        # Apply business logic
        processed = apply_business_rules(data)
        # Return result
        return processed
    """).strip() + "\n")    # Create section with complex conditional options
    sections_content = textwrap.dedent("""
    complex-conditions:
      extensions: [".py"]
      python:
        skip_trivial_inits: true
        strip_function_bodies: false
        when:
          # In production without debugging, remove __init__.py for compactness
          - condition: "tag:production AND NOT tag:debug"
            skip_trivial_inits: true
            strip_function_bodies: true
          # In debug mode or for internal documentation, show everything
          - condition: "tag:debug OR tag:internal-docs"
            skip_trivial_inits: false
            strip_function_bodies: false
          # For API documentation, show only signatures
          - condition: "tag:api-docs AND NOT tag:internal-docs"
            strip_function_bodies: true
      filters:
        mode: allow
        allow:
          - "/src/**"
    """).strip() + "\n"
    
    write(root / "lg-cfg" / "sections.yaml", sections_content)
    
    template_content = """# Complex Conditions Test

${complex-conditions}
"""
    
    create_conditional_template(root, "complex-conditions-test", template_content)
    
    # Test 1: production without debug - maximum compactness
    result1 = render_template(root, "ctx:complex-conditions-test",
                             make_run_options(extra_tags={"production"}))

    assert "def debug_function():" in result1      # signatures present
    assert "collect_system_info()" not in result1  # function bodies removed
    assert "def production_function():" in result1
    assert "get_production_data()" not in result1  # function bodies removed

    # Test 2: debug mode - all details
    result2 = render_template(root, "ctx:complex-conditions-test",
                             make_run_options(extra_tags={"debug"}))

    assert "python:src/__init__.py" in result2        # __init__.py included
    assert "def debug_function():" in result2     # signatures present
    assert "collect_system_info()" in result2    # function bodies preserved
    assert "get_production_data()" in result2    # function bodies preserved

    # Test 3: api-docs without internal-docs - signatures only
    result3 = render_template(root, "ctx:complex-conditions-test",
                             make_run_options(extra_tags={"api-docs"}))

    assert "def debug_function():" in result3     # signatures present
    assert "collect_system_info()" not in result3 # function bodies removed
    assert "get_production_data()" not in result3 # function bodies removed

    # Test 4: api-docs + internal-docs - internal-docs cancels strip_function_bodies
    result4 = render_template(root, "ctx:complex-conditions-test",
                             make_run_options(extra_tags={"api-docs", "internal-docs"}))

    assert "python:src/__init__.py" in result4        # __init__.py included (internal-docs)
    assert "def debug_function():" in result4     # signatures present
    assert "collect_system_info()" in result4    # function bodies preserved (internal-docs takes priority)
    assert "get_production_data()" in result4    # function bodies preserved (internal-docs takes priority)


def test_conditional_options_inheritance_and_priority(adaptive_project):
    """
    Test priority and inheritance of conditional adapter options.

    Verifies that later when rules override earlier ones.
    """
    root = adaptive_project
    
    # Tags for testing priority
    priority_tags = {
        "base-mode": TagConfig(title="Base mode"),
        "override-mode": TagConfig(title="Override mode"),
        "final-mode": TagConfig(title="Final mode")
    }
    create_tags_yaml(root, global_tags=priority_tags, append=True)

    write(root / "src" / "__init__.py", "pass")
    write(root / "src" / "example.py", "def func(): pass\n")

    # Create section with priority rules
    sections_content = textwrap.dedent("""
    priority-test:
      extensions: [".py"]
      python:
        skip_trivial_inits: true  # base value
        when:
          # First rule
          - condition: "tag:base-mode"
            skip_trivial_inits: false
          # Second rule overrides first when conditions match
          - condition: "tag:base-mode AND tag:override-mode"
            skip_trivial_inits: true
          # Third rule with highest priority
          - condition: "tag:final-mode"
            skip_trivial_inits: false
      filters:
        mode: allow
        allow:
          - "/src/**"
    """).strip() + "\n"

    write(root / "lg-cfg" / "sections.yaml", sections_content)

    template_content = """# Priority Test

${priority-test}
"""

    create_conditional_template(root, "priority-test", template_content)

    # Test 1: base-mode only - first rule is active
    result1 = render_template(root, "ctx:priority-test",
                             make_run_options(extra_tags={"base-mode"}))

    assert "python:src/__init__.py" in result1  # skip_trivial_inits: false

    # Test 2: base-mode + override-mode - second rule overrides first
    result2 = render_template(root, "ctx:priority-test",
                             make_run_options(extra_tags={"base-mode", "override-mode"}))

    assert "python:src/__init__.py" not in result2  # skip_trivial_inits: true (overridden)

    # Test 3: all three tags - final-mode has highest priority
    result3 = render_template(root, "ctx:priority-test",
                             make_run_options(extra_tags={"base-mode", "override-mode", "final-mode"}))

    assert "python:src/__init__.py" in result3  # skip_trivial_inits: false (final-mode)

    # Test 4: final-mode only - does not depend on other rules
    result4 = render_template(root, "ctx:priority-test",
                             make_run_options(extra_tags={"final-mode"}))

    assert "python:src/__init__.py" in result4  # skip_trivial_inits: false