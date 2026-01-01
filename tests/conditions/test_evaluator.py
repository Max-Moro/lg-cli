"""
Tests for the condition evaluator.
"""

import pytest

from lg.conditions.evaluator import ConditionEvaluator, evaluate_condition_string
from lg.conditions.parser import ConditionParser
from lg.run_context import ConditionContext


class TestConditionEvaluator:
    
    def setup_method(self):
        self.parser = ConditionParser()

        # Create test context
        self.context = ConditionContext(
            active_tags={"python", "tests", "minimal"},
            tagsets={
                "language": {"python", "javascript", "typescript"},
                "feature": {"auth", "api", "ui"},
                "empty_set": set()
            },
            origin="",
        )
        
        self.evaluator = ConditionEvaluator(self.context)
    
    def test_simple_tag_conditions(self):
        """Test simple tag conditions"""

        # Active tag
        condition = self.parser.parse("tag:python")
        assert self.evaluator.evaluate(condition) is True

        # Inactive tag
        condition = self.parser.parse("tag:javascript")
        assert self.evaluator.evaluate(condition) is False

        # Other active tags
        condition = self.parser.parse("tag:tests")
        assert self.evaluator.evaluate(condition) is True

        condition = self.parser.parse("tag:minimal")
        assert self.evaluator.evaluate(condition) is True
    
    def test_tagset_conditions(self):
        """Test tagset conditions"""

        # Specified tag is active in the set
        condition = self.parser.parse("TAGSET:language:python")
        assert self.evaluator.evaluate(condition) is True

        # Specified tag is not active, but others in the set are
        condition = self.parser.parse("TAGSET:language:javascript")
        assert self.evaluator.evaluate(condition) is False

        # No tags from the set are active
        condition = self.parser.parse("TAGSET:feature:auth")
        assert self.evaluator.evaluate(condition) is True

        condition = self.parser.parse("TAGSET:feature:api")
        assert self.evaluator.evaluate(condition) is True

        # Empty tag set
        condition = self.parser.parse("TAGSET:empty_set:anything")
        assert self.evaluator.evaluate(condition) is True

    def test_tagonly_conditions(self):
        """Test exclusive tag conditions - tag must be the ONLY active tag from set"""

        # Specified tag is active AND is the only active tag from the set
        # Context has python active, and only python is in active_tags intersection with language set
        condition = self.parser.parse("TAGONLY:language:python")
        assert self.evaluator.evaluate(condition) is True

        # Specified tag is not active (javascript not in active_tags)
        condition = self.parser.parse("TAGONLY:language:javascript")
        assert self.evaluator.evaluate(condition) is False

        # No tags from the set are active (feature set has no active tags)
        condition = self.parser.parse("TAGONLY:feature:auth")
        assert self.evaluator.evaluate(condition) is False

        # Empty/non-existent set - always False
        condition = self.parser.parse("TAGONLY:empty_set:anything")
        assert self.evaluator.evaluate(condition) is False

        # Non-existent set - always False
        condition = self.parser.parse("TAGONLY:nonexistent:tag")
        assert self.evaluator.evaluate(condition) is False

    def test_tagonly_with_multiple_active_tags(self):
        """Test TAGONLY when multiple tags from set are active"""

        # Create context where multiple tags from set are active
        context_multi = ConditionContext(
            active_tags={"python", "javascript", "tests"},
            tagsets={
                "language": {"python", "javascript", "typescript", "go"},
            },
            origin="",
        )
        evaluator_multi = ConditionEvaluator(context_multi)

        # python is active but javascript is also active from same set
        condition = self.parser.parse("TAGONLY:language:python")
        assert evaluator_multi.evaluate(condition) is False

        # javascript is active but python is also active from same set
        condition = self.parser.parse("TAGONLY:language:javascript")
        assert evaluator_multi.evaluate(condition) is False

    def test_tagonly_in_complex_expressions(self):
        """Test TAGONLY in complex expressions with other operators"""

        # TAGONLY with NOT
        condition = self.parser.parse("NOT TAGONLY:language:javascript")
        assert self.evaluator.evaluate(condition) is True

        # TAGONLY with AND
        condition = self.parser.parse("TAGONLY:language:python AND tag:tests")
        assert self.evaluator.evaluate(condition) is True

        # TAGONLY with OR
        condition = self.parser.parse("TAGONLY:language:javascript OR tag:python")
        assert self.evaluator.evaluate(condition) is True

        # Complex expression
        condition = self.parser.parse("(TAGONLY:language:python OR tag:minimal) AND NOT tag:deprecated")
        assert self.evaluator.evaluate(condition) is True

    def test_scope_conditions(self):
        """Test scope conditions"""

        # Current scope = local
        condition = self.parser.parse("scope:local")
        assert self.evaluator.evaluate(condition) is True

        condition = self.parser.parse("scope:parent")
        assert self.evaluator.evaluate(condition) is False

        # Change scope
        context_parent = ConditionContext(
            active_tags=set(),
            tagsets={},
            origin="parent",
        )
        evaluator_parent = ConditionEvaluator(context_parent)

        condition = self.parser.parse("scope:local")
        assert evaluator_parent.evaluate(condition) is False

        condition = self.parser.parse("scope:parent")
        assert evaluator_parent.evaluate(condition) is True
    
    def test_not_conditions(self):
        """Test NOT conditions"""

        # NOT of active tag
        condition = self.parser.parse("NOT tag:python")
        assert self.evaluator.evaluate(condition) is False

        # NOT of inactive tag
        condition = self.parser.parse("NOT tag:javascript")
        assert self.evaluator.evaluate(condition) is True

        # Double negation
        condition = self.parser.parse("NOT NOT tag:python")
        assert self.evaluator.evaluate(condition) is True

        condition = self.parser.parse("NOT NOT tag:javascript")
        assert self.evaluator.evaluate(condition) is False
    
    def test_and_conditions(self):
        """Test AND conditions"""

        # Both tags active
        condition = self.parser.parse("tag:python AND tag:tests")
        assert self.evaluator.evaluate(condition) is True

        # One tag active, other inactive
        condition = self.parser.parse("tag:python AND tag:javascript")
        assert self.evaluator.evaluate(condition) is False

        # Both tags inactive
        condition = self.parser.parse("tag:javascript AND tag:java")
        assert self.evaluator.evaluate(condition) is False

        # Triple AND
        condition = self.parser.parse("tag:python AND tag:tests AND tag:minimal")
        assert self.evaluator.evaluate(condition) is True

        condition = self.parser.parse("tag:python AND tag:tests AND tag:javascript")
        assert self.evaluator.evaluate(condition) is False
    
    def test_or_conditions(self):
        """Test OR conditions"""

        # Both tags active
        condition = self.parser.parse("tag:python OR tag:tests")
        assert self.evaluator.evaluate(condition) is True

        # One tag active, other inactive
        condition = self.parser.parse("tag:python OR tag:javascript")
        assert self.evaluator.evaluate(condition) is True

        # Both tags inactive
        condition = self.parser.parse("tag:javascript OR tag:java")
        assert self.evaluator.evaluate(condition) is False

        # Triple OR
        condition = self.parser.parse("tag:javascript OR tag:java OR tag:python")
        assert self.evaluator.evaluate(condition) is True

        condition = self.parser.parse("tag:javascript OR tag:java OR tag:go")
        assert self.evaluator.evaluate(condition) is False
    
    def test_operator_precedence_evaluation(self):
        """Test operator precedence during evaluation"""

        # tag:python OR tag:javascript AND tag:tests
        # Should be: tag:python OR (tag:javascript AND tag:tests)
        # python=True, javascript=False, tests=True
        # Result: True OR (False AND True) = True OR False = True
        condition = self.parser.parse("tag:python OR tag:javascript AND tag:tests")
        assert self.evaluator.evaluate(condition) is True

        # tag:javascript OR tag:go AND tag:tests
        # Result: False OR (False AND True) = False OR False = False
        condition = self.parser.parse("tag:javascript OR tag:go AND tag:tests")
        assert self.evaluator.evaluate(condition) is False
    
    def test_grouping_evaluation(self):
        """Test evaluation with grouping in parentheses"""

        # (tag:python OR tag:javascript) AND tag:tests
        # (True OR False) AND True = True AND True = True
        condition = self.parser.parse("(tag:python OR tag:javascript) AND tag:tests")
        assert self.evaluator.evaluate(condition) is True

        # (tag:javascript OR tag:go) AND tag:tests
        # (False OR False) AND True = False AND True = False
        condition = self.parser.parse("(tag:javascript OR tag:go) AND tag:tests")
        assert self.evaluator.evaluate(condition) is False

        # tag:python AND (tag:tests OR tag:javascript)
        # True AND (True OR False) = True AND True = True
        condition = self.parser.parse("tag:python AND (tag:tests OR tag:javascript)")
        assert self.evaluator.evaluate(condition) is True
    
    def test_complex_expressions(self):
        """Test complex expressions"""

        # tag:python AND (NOT tag:deprecated OR scope:local)
        # python=True, deprecated=False, scope:local=True
        # True AND (NOT False OR True) = True AND (True OR True) = True AND True = True
        condition = self.parser.parse("tag:python AND (NOT tag:deprecated OR scope:local)")
        assert self.evaluator.evaluate(condition) is True

        # NOT (tag:javascript OR tag:go) AND tag:python
        # NOT (False OR False) AND True = NOT False AND True = True AND True = True
        condition = self.parser.parse("NOT (tag:javascript OR tag:go) AND tag:python")
        assert self.evaluator.evaluate(condition) is True

        # TAGSET:language:javascript OR (tag:python AND tag:tests)
        # False OR (True AND True) = False OR True = True
        condition = self.parser.parse("TAGSET:language:javascript OR (tag:python AND tag:tests)")
        assert self.evaluator.evaluate(condition) is True
    
    def test_short_circuit_evaluation(self):
        """Test short-circuit evaluation"""

        # Create a context that raises an error when accessing unknown tags
        class StrictContext(ConditionContext):
            def is_tag_active(self, tag_name: str) -> bool:
                if tag_name not in {"python", "tests"}:
                    raise ValueError(f"Unknown tag: {tag_name}")
                return tag_name in {"python", "tests"}

        strict_context = StrictContext(active_tags={"python", "tests"})
        strict_evaluator = ConditionEvaluator(strict_context)

        # tag:python OR tag:unknown_tag
        # First operand is True, second should not be evaluated
        condition = self.parser.parse("tag:python OR tag:unknown_tag")
        assert strict_evaluator.evaluate(condition) is True

        # tag:unknown_tag AND tag:python
        # First operand will raise an error
        condition = self.parser.parse("tag:unknown_tag AND tag:python")
        with pytest.raises(ValueError, match="Unknown tag"):
            strict_evaluator.evaluate(condition)
    
    def test_evaluate_condition_string_function(self):
        """Test the convenient evaluate_condition_string function"""

        # Successful evaluation
        result = evaluate_condition_string("tag:python AND tag:tests", self.context)
        assert result is True

        result = evaluate_condition_string("tag:javascript", self.context)
        assert result is False

        # Parsing error
        with pytest.raises(Exception):  # ParseError or ValueError
            evaluate_condition_string("invalid syntax", self.context)
    
    def test_empty_context(self):
        """Test with empty context"""
        empty_context = ConditionContext()
        empty_evaluator = ConditionEvaluator(empty_context)

        # All tags are inactive
        condition = self.parser.parse("tag:python")
        assert empty_evaluator.evaluate(condition) is False

        # NOT should work
        condition = self.parser.parse("NOT tag:python")
        assert empty_evaluator.evaluate(condition) is True

        # Empty tag sets
        condition = self.parser.parse("TAGSET:language:python")
        assert empty_evaluator.evaluate(condition) is True  # Empty set is always True
    
    def test_unknown_tagset(self):
        """Test with unknown tagset"""

        # Unknown set should behave like empty
        condition = self.parser.parse("TAGSET:unknown_set:python")
        assert self.evaluator.evaluate(condition) is True
    
    def test_case_sensitivity(self):
        """Test case sensitivity"""

        # Tags are case sensitive
        condition = self.parser.parse("tag:Python")  # With capital P
        assert self.evaluator.evaluate(condition) is False  # python with lowercase p is active

        condition = self.parser.parse("tag:python")  # With lowercase p
        assert self.evaluator.evaluate(condition) is True