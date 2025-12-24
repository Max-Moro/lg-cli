"""
Tests for comment policy implementation in Java adapter.
"""

from lg.adapters.langs.java import JavaCfg
from lg.adapters.code_model import CommentConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestJavaCommentOptimization:
    """Test comment processing for Java code."""

    def test_keep_all_comments(self, do_comments):
        """Test keeping all comments (default policy)."""
        adapter = make_adapter(JavaCfg(comment_policy="keep_all"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("java.removed.comment", 0) == 0
        assert "// Single-line comment at module level" in result
        assert "Multi-line comment explaining" in result
        assert "* This method performs comprehensive" in result

        assert_golden_match(result, "comments", "keep_all")

    def test_strip_all_comments(self, do_comments):
        """Test stripping all comments."""
        adapter = make_adapter(JavaCfg(comment_policy="strip_all"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("java.removed.comment", 0) > 0
        assert "// … comment omitted" in result

        assert_golden_match(result, "comments", "strip_all")

    def test_keep_doc_comments(self, do_comments):
        """Test keeping only Javadoc documentation comments."""
        adapter = make_adapter(JavaCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("java.removed.comment", 0) > 0
        assert "/**" in result
        assert "// Single-line comment at module level" not in result

        assert_golden_match(result, "comments", "keep_doc")

    def test_keep_first_sentence_policy(self, do_comments):
        """Test keeping only first sentence of Javadoc comments."""
        adapter = make_adapter(JavaCfg(comment_policy="keep_first_sentence"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("java.removed.comment", 0) > 0

        assert_golden_match(result, "comments", "keep_first_sentence")

    def test_complex_comment_policy(self, do_comments):
        """Test complex comment policy with custom configuration."""
        comment_config = CommentConfig(
            policy="keep_doc",
            max_tokens=30,
            keep_annotations=["TODO", "FIXME", "NOTE"],
            strip_patterns=["WARNING"]
        )

        adapter = make_adapter(JavaCfg(comment_policy=comment_config))

        result, meta = adapter.process(lctx(do_comments))

        assert "TODO:" in result
        assert "FIXME:" in result
        assert "WARNING:" not in result
        assert "// … comment omitted" in result

        assert_golden_match(result, "comments", "complex_policy")


class TestJavaCommentEdgeCases:
    """Test edge cases for Java comment optimization."""

    def test_inline_comments_with_types(self):
        """Test handling of inline comments with Java types."""
        code = '''
class Config {
    private long timeout;      // Connection timeout in milliseconds
    private int retries;       // Number of retry attempts
    private boolean debug;     // Enable debug logging
}

Config config = new Config(
    5000,    // 5 seconds
    3,       // Try 3 times
    false    // Disable by default
);
'''

        adapter = make_adapter(JavaCfg(comment_policy="strip_all"))

        result, meta = adapter.process(lctx(code))

        assert "// Connection timeout in milliseconds" not in result
        assert "// Number of retry attempts" not in result
        assert meta.get("java.removed.comment", 0) > 0

    def test_javadoc_detection(self):
        """Test proper Javadoc comment detection."""
        code = '''
/**
 * This is a Javadoc comment
 * @param data Input data
 */
public void processData(String data) {
    /* This is a regular multi-line comment */
    // This is a single-line comment
    System.out.println(data);
}
'''

        adapter = make_adapter(JavaCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        assert "/**" in result and "This is a Javadoc comment" in result
        assert "@param data Input data" in result

        assert "/* This is a regular multi-line comment */" not in result
        assert "// This is a single-line comment" not in result

    def test_comment_preservation_in_classes(self):
        """Test comment preservation in Java classes."""
        code = '''
/**
 * User class definition.
 */
public class User {
    /** User's unique identifier */
    private long id;

    /** User's display name */
    private String name;

    // Internal field (not part of public API)
    private Map<String, Object> metadata;
}
'''

        adapter = make_adapter(JavaCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        assert "/**" in result and "User class definition" in result
        assert "/** User's unique identifier */" in result
        assert "/** User's display name */" in result

        assert "// Internal field" not in result

    def test_multiline_comment_styles(self):
        """Test different multiline comment styles."""
        code = '''
/*
 * Standard multiline comment
 * with multiple lines
 */
public void standardComment() {}

/**
 * Javadoc style comment
 * with documentation
 */
public void javadocComment() {}

/* Single line multiline comment */
public void singleLineMulti() {}
'''

        adapter = make_adapter(JavaCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        assert "/**" in result and "Javadoc style comment" in result

        assert "Standard multiline comment" not in result
        assert "Single line multiline comment" not in result

    def test_annotation_javadoc(self):
        """Test Javadoc on Java annotations."""
        code = '''
/**
 * Custom validation annotation.
 *
 * @author John Doe
 */
@Target(ElementType.FIELD)
@Retention(RetentionPolicy.RUNTIME)
public @interface ValidEmail {
    /**
     * Error message when validation fails.
     * @return The error message
     */
    String message() default "Invalid email";
}
'''

        adapter = make_adapter(JavaCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        assert "/**" in result and "Custom validation annotation" in result
        assert "@author John Doe" in result
        assert "Error message when validation fails" in result
