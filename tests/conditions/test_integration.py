"""
Integration tests for the conditions system.

Tests the full pipeline: parsing -> evaluation,
as well as integration with ConditionContext.
"""

import pytest

from lg.conditions import (
    ConditionParser,
    ConditionEvaluator,
    evaluate_condition_string,
)
from lg.run_context import ConditionContext


class TestConditionsIntegration:
    
    def test_end_to_end_pipeline(self):
        """Test full conditions processing pipeline"""

        # Context setup
        context = ConditionContext(
            active_tags={"python", "tests", "api"},
            tagsets={
                "language": {"python", "javascript", "go"},
                "component": {"api", "ui", "db"},
                "stage": {"dev", "prod"}
            },
            origin=""
        )

        # Set of test cases: (condition, expected result)
        test_cases = [
            # Simple conditions
            ("tag:python", True),
            ("tag:javascript", False),

            # Tagset conditions
            ("TAGSET:language:python", True),      # specified tag is active
            ("TAGSET:language:javascript", False), # other tag in set is active
            ("TAGSET:stage:dev", True),           # no tags from set are active

            # Scopes
            ("scope:local", True),
            ("scope:parent", False),

            # Logical operators
            ("tag:python AND tag:tests", True),
            ("tag:python AND tag:javascript", False),
            ("tag:python OR tag:javascript", True),
            ("tag:javascript OR tag:go", False),

            # Negation
            ("NOT tag:javascript", True),
            ("NOT tag:python", False),
            ("NOT NOT tag:python", True),

            # Grouping
            ("(tag:python OR tag:javascript) AND tag:tests", True),
            ("(tag:javascript OR tag:go) AND tag:tests", False),
            ("tag:python AND (tag:tests OR tag:javascript)", True),

            # Complex expressions
            ("tag:python AND NOT tag:deprecated", True),
            ("TAGSET:language:python AND scope:local", True),
            ("NOT (tag:javascript OR tag:go) AND tag:api", True),
            (
                "tag:python AND (TAGSET:component:api OR scope:parent) AND NOT tag:deprecated",
                True
            ),
        ]

        parser = ConditionParser()
        evaluator = ConditionEvaluator(context)

        for condition_str, expected in test_cases:
            # Test through parser + evaluator
            ast = parser.parse(condition_str)
            result = evaluator.evaluate(ast)
            assert result == expected, f"Failed for condition: {condition_str}"

            # Test through convenient function
            result2 = evaluate_condition_string(condition_str, context)
            assert result2 == expected, f"Failed for condition (via function): {condition_str}"
    
    def test_context_methods(self):
        """Test ConditionContext methods"""

        context = ConditionContext(
            active_tags={"python", "api", "minimal"},
            tagsets={
                "language": {"python", "javascript", "go"},
                "component": {"api", "ui", "db"},
                "empty": set()
            },
            origin=""
        )

        # Test is_tag_active
        assert context.is_tag_active("python") is True
        assert context.is_tag_active("javascript") is False
        assert context.is_tag_active("nonexistent") is False

        # Test is_tagset_condition_met

        # Specified tag is active in the set
        assert context.is_tagset_condition_met("language", "python") is True

        # Specified tag is not active, but others in set are
        assert context.is_tagset_condition_met("language", "javascript") is False

        # In component set, api tag is active, so condition is true only for api
        assert context.is_tagset_condition_met("component", "ui") is False  # other tag is active
        assert context.is_tagset_condition_met("component", "db") is False  # other tag is active

        # Specified tag is active in the set (matches active)
        assert context.is_tagset_condition_met("component", "api") is True

        # Empty set
        assert context.is_tagset_condition_met("empty", "anything") is True

        # Non-existent set
        assert context.is_tagset_condition_met("nonexistent", "tag") is True  # non-existent = empty = True

        # Test is_scope_condition_met
        assert context.is_scope_condition_met("local") is True
        assert context.is_scope_condition_met("parent") is False
        assert context.is_scope_condition_met("invalid") is False
    
    def test_context_edge_cases(self):
        """Test context edge cases"""

        # Completely empty context
        empty_context = ConditionContext()

        assert empty_context.is_tag_active("anything") is False
        assert empty_context.is_tagset_condition_met("set", "tag") is True  # non-existent set = empty = True
        assert empty_context.is_scope_condition_met("local") is True  # empty string means local scope

        # Context with only active tags
        tags_only_context = ConditionContext(active_tags={"python", "api"})

        assert tags_only_context.is_tag_active("python") is True
        assert tags_only_context.is_tagset_condition_met("nonexistent", "python") is True  # non-existent set

        # Context with only tagsets
        tagsets_only_context = ConditionContext(
            tagsets={"language": {"python", "go"}}
        )

        assert tagsets_only_context.is_tag_active("python") is False  # not active
        assert tagsets_only_context.is_tagset_condition_met("language", "python") is True  # empty intersection
    
    def test_error_propagation(self):
        """Test error propagation through the entire pipeline"""

        context = ConditionContext()

        # Parsing errors should be raised
        with pytest.raises(Exception):
            evaluate_condition_string("invalid syntax @@", context)

        with pytest.raises(Exception):
            evaluate_condition_string("tag:", context)  # incomplete condition

        with pytest.raises(Exception):
            evaluate_condition_string("", context)  # empty condition
    
    def test_whitespace_and_formatting(self):
        """Test handling of various formatting options"""

        context = ConditionContext(active_tags={"python", "tests"})

        # Various whitespace options should produce the same result
        variants = [
            "tag:python AND tag:tests",
            "tag:python  AND  tag:tests",
            " tag:python AND tag:tests ",
            "tag : python AND tag : tests",
            "\ttag:python\tAND\ttag:tests\t",
            "tag:python\nAND\ntag:tests"
        ]

        expected_result = evaluate_condition_string("tag:python AND tag:tests", context)

        for variant in variants:
            result = evaluate_condition_string(variant, context)
            assert result == expected_result, f"Failed for variant: {repr(variant)}"
    
    def test_complex_real_world_scenarios(self):
        """Test complex scenarios similar to real-world use"""

        # Simulate a real development context
        context = ConditionContext(
            active_tags={"python", "backend", "api", "tests", "development"},
            tagsets={
                "language": {"python", "javascript", "typescript", "go"},
                "component": {"frontend", "backend", "api", "db"},
                "environment": {"development", "staging", "production"},
                "feature": {"auth", "payments", "notifications"}
            },
            origin=""
        )

        scenarios = [
            # Show code only for Python backend development
            (
                "tag:python AND tag:backend AND TAGSET:environment:development",
                True
            ),

            # Show tests only if enabled and not in production
            (
                "tag:tests AND NOT TAGSET:environment:production",
                True
            ),

            # Show API docs only for API component or if general tests
            (
                "TAGSET:component:api OR (tag:tests AND scope:local)",
                True
            ),

            # Hide experimental features in production
            (
                "NOT (tag:experimental AND TAGSET:environment:production)",
                True  # experimental is not active
            ),

            # Show only files relevant to current development
            (
                "(tag:python OR tag:javascript) AND "
                "(TAGSET:component:backend OR TAGSET:component:api) AND "
                "NOT tag:deprecated",
                True
            ),
        ]

        for condition_str, expected in scenarios:
            result = evaluate_condition_string(condition_str, context)
            assert result == expected, f"Failed for scenario: {condition_str}"
    
    def test_performance_with_complex_expressions(self):
        """Test performance with large expressions"""

        context = ConditionContext(
            active_tags={"tag1", "tag3", "tag5"},
            tagsets={
                f"set{i}": {f"tag{j}" for j in range(i, i+3)}
                for i in range(1, 6)
            }
        )

        # Large expression with multiple conditions
        large_condition = " OR ".join([
            f"(tag:tag{i} AND TAGSET:set{i%5+1}:tag{i} AND scope:local)"
            for i in range(1, 21)
        ])

        # Should work without errors and in reasonable time
        result = evaluate_condition_string(large_condition, context)
        assert isinstance(result, bool)

        # Test with deep nesting
        nested_condition = "(" * 10 + "tag:tag1" + ")" * 10
        result = evaluate_condition_string(nested_condition, context)
        assert result is True