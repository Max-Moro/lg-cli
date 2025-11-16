"""
Tests for section and template placeholders.

This package contains high-level tests for the main functionality
of the Listing Generator template engine, testing the external contract
without dependency on internal implementation.

Test structure:

- test_basic_section_placeholders.py - basic section placeholders ${section}
- test_addressed_placeholders.py - addressed placeholders ${@origin:section}
- test_template_placeholders.py - template placeholders ${tpl:name}
- test_context_placeholders.py - context placeholders ${ctx:name}
- test_complex_scenarios.py - complex integration scenarios

These tests are intended to ensure functionality remains intact
during refactoring of the template engine to a modular architecture.
"""
