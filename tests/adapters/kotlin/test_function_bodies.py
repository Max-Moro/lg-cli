"""
Tests for function body optimization in Kotlin adapter.
"""

from lg.adapters.kotlin import KotlinCfg
from lg.adapters.code_model import FunctionBodyConfig
from .conftest import lctx_kt, do_function_bodies, assert_golden_match, make_adapter


class TestKotlinFunctionBodyOptimization:
    """Test function body stripping for Kotlin code."""
    
    def test_basic_function_stripping(self, do_function_bodies):
        """Test basic function body stripping."""
        adapter = make_adapter(KotlinCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx_kt(do_function_bodies))
        
        # Check that functions were processed
        assert meta.get("kotlin.removed.function_body", 0) > 0
        assert meta.get("kotlin.removed.method_body", 0) > 0
        assert "// … method body omitted" in result or "// … function body omitted" in result
        
        # Golden file test
        assert_golden_match(result, "function_bodies", "basic_strip")
    
    def test_large_only_method_stripping(self, do_function_bodies):
        """Test stripping only large methods."""
        adapter = make_adapter(KotlinCfg(
            strip_function_bodies=FunctionBodyConfig(
                mode="large_only",
                min_lines=4  # Higher threshold for Kotlin
            )
        ))
        
        result, meta = adapter.process(lctx_kt(do_function_bodies))
        
        # Should have fewer removals than basic test
        assert_golden_match(result, "function_bodies", "large_only_strip")
    
    def test_lambda_function_handling(self):
        """Test handling of lambda functions."""
        lambda_code = '''
val simple = { "hello" }

val complex = { a: Int, b: Int ->
    val result = a + b
    println("Computing: $result")
    result
}

val multiline: (List<User>) -> List<String> = { users ->
    users
        .filter { it.active }
        .map { it.name }
        .sorted()
}
'''
        
        adapter = make_adapter(KotlinCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx_kt(lambda_code))
        
        # Should only strip multiline lambda functions (complex and multiline)
        assert 'val simple = { "hello" }' in result  # Single line preserved
        
        # Lambda function signatures preserved
        assert "val complex = { a: Int, b: Int ->" in result or "val complex" in result
        assert "val multiline: (List<User>) -> List<String>" in result or "val multiline" in result
        
        assert_golden_match(result, "function_bodies", "lambda_functions")
    
    def test_class_method_preservation(self):
        """Test that class structure is preserved while stripping method bodies."""
        class_code = '''
class Calculator(private val name: String) {
    private val history: MutableList<String> = mutableListOf()
    
    fun add(a: Int, b: Int): Int {
        val result = a + b
        history.add("$a + $b = $result")
        return result
    }
    
    fun getHistory(): List<String> {
        return history.toList()
    }
}
'''
        
        adapter = make_adapter(KotlinCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx_kt(class_code))
        
        # Class structure should be preserved
        assert "class Calculator" in result
        assert "private val history: MutableList<String> = mutableListOf()" in result
        
        # Methods should be stripped but signatures preserved
        assert "fun add(a: Int, b: Int): Int" in result
        assert "fun getHistory(): List<String>" in result
        
        assert_golden_match(result, "function_bodies", "class_methods")
    
    def test_no_stripping_preserves_original(self):
        """Test that disabling stripping preserves original code."""
        code = "fun test(): Int { return 42 }"
        
        adapter = make_adapter(KotlinCfg(strip_function_bodies=False))
        
        result, meta = adapter.process(lctx_kt(code))
        
        # Should be nearly identical to original
        assert "return 42" in result
        assert meta.get("kotlin.removed.function_body", 0) == 0
        assert meta.get("kotlin.removed.method_bodies", 0) == 0

    def test_public_only_method_stripping(self):
        """Test public_only mode for Kotlin method body stripping."""
        code = '''class Calculator {
    fun add(a: Int, b: Int): Int {
        val result = a + b
        println("Adding $a, $b")
        return result
    }
    
    private fun multiply(a: Int, b: Int): Int {
        val result = a * b
        println("Multiplying $a, $b")
        return result
    }
}
'''
        
        function_config = FunctionBodyConfig(mode="public_only")
        adapter = make_adapter(KotlinCfg(strip_function_bodies=function_config))
        
        result, meta = adapter.process(lctx_kt(code))
        
        # Public method body should be stripped
        assert "fun add(a: Int, b: Int): Int" in result
        assert "// … method body omitted" in result or "// … function body omitted" in result
        assert "val result = a + b" not in result
        
        # Private method body should be preserved (it's not public)
        assert "private fun multiply(a: Int, b: Int): Int" in result
        assert "val result = a * b" in result


class TestKotlinFunctionBodyEdgeCases:
    """Test edge cases for Kotlin function body optimization."""
    
    def test_single_line_functions(self):
        """Test that single-line functions are handled correctly."""
        code = '''fun simple() = 42

fun complex(): Int {
    val x = 1
    val y = 2
    return x + y
}
'''
        
        adapter = make_adapter(KotlinCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx_kt(code))
        
        # Single-line function should not be stripped (important for simple functions)
        assert "fun simple() = 42" in result
        
        # Multi-line function should be stripped
        assert "fun complex(): Int" in result
        assert "// … function body omitted" in result
        assert "val x = 1" not in result
    
    def test_nested_functions(self):
        """Test handling of nested functions."""
        code = '''fun outer(): String {
    fun inner(): String {
        return "inner"
    }
    
    val result = inner()
    return "outer: $result"
}
'''
        
        adapter = make_adapter(KotlinCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx_kt(code))
        
        # Outer function body should be stripped
        assert "fun outer(): String" in result
        assert "// … function body omitted" in result
        assert "fun inner():" not in result  # Should be part of stripped body
    
    def test_data_class_and_interface_preservation(self):
        """Test that data classes and interfaces are preserved."""
        code = '''data class User(
    val id: Long,
    val name: String
)

interface UserRepository {
    fun findById(id: Long): User?
    fun save(user: User): User
}

fun processUser(user: User): User {
    return user.copy(name = user.name.uppercase())
}
'''
        
        adapter = make_adapter(KotlinCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx_kt(code))
        
        # Data classes and interfaces should be preserved
        assert "data class User" in result
        assert "interface UserRepository" in result
        assert "val id: Long" in result
        assert "val name: String" in result
        
        # Function body should be stripped
        assert "fun processUser(user: User): User" in result
        assert "// … function body omitted" in result
        assert "return user.copy" not in result


class TestKotlinDocstringPreservation:
    """Test preservation of KDoc when stripping function bodies."""
    
    def test_function_with_kdoc_preserved(self):
        """Test that function KDoc is preserved when bodies are stripped."""
        code = '''fun calculateSum(a: Int, b: Int): Int {
    /**
     * Calculate the sum of two numbers.
     * 
     * @param a First number
     * @param b Second number
     * @return Sum of a and b
     */
    // This is a comment
    val result = a + b
    println("Sum: $result")
    return result
}
'''
        
        adapter = make_adapter(KotlinCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx_kt(code))
        
        # Function signature should be preserved
        assert "fun calculateSum(a: Int, b: Int): Int" in result
        
        # KDoc should be preserved completely
        assert "/**" in result and "Calculate the sum of two numbers" in result
        assert "@param" in result
        assert "@return" in result
        
        # Function body should be removed
        assert "val result = a + b" not in result
        assert "println" not in result
        assert "return result" not in result
        
        # Should have placeholder for removed body
        assert "// … function body omitted" in result
    
    def test_method_with_kdoc_preserved(self):
        """Test that method KDoc is preserved when bodies are stripped."""
        code = '''class Calculator {
    /**
     * Multiply two numbers together.
     * 
     * This method performs multiplication operation.
     */
    fun multiply(a: Int, b: Int): Int {
        val temp = a * b
        history.add("multiply($a, $b) = $temp")
        return temp
    }
}
'''
        
        adapter = make_adapter(KotlinCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx_kt(code))
        
        # Method signature should be preserved
        assert "fun multiply(a: Int, b: Int): Int" in result
        
        # KDoc should be preserved
        assert "/**" in result and "Multiply two numbers together" in result
        assert "This method performs multiplication operation" in result
        
        # Method body should be removed
        assert "val temp = a * b" not in result
        assert "history.add" not in result
        assert "return temp" not in result
        
        # Should have placeholder for removed body
        assert "// … method body omitted" in result or "// … function body omitted" in result
    
    def test_function_without_kdoc_full_removal(self):
        """Test that functions without KDoc have bodies fully removed."""
        code = '''fun simpleFunction(): Int {
    // Just a comment, no KDoc
    val x = 1
    val y = 2
    return x + y
}
'''
        
        adapter = make_adapter(KotlinCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx_kt(code))
        
        # Function signature should be preserved
        assert "fun simpleFunction(): Int" in result
        
        # Everything else should be removed
        assert "// Just a comment" not in result
        assert "val x = 1" not in result
        assert "return x + y" not in result
        
        # Should have placeholder
        assert "// … function body omitted" in result
    
    def test_mixed_functions_with_without_kdoc(self):
        """Test mixed functions - some with KDoc, some without."""
        code = '''/**
 * This function has documentation.
 */
fun documentedFunction(): String {
    val complexLogic = true
    if (complexLogic) {
        return "documented"
    }
    return "fallback"
}

fun undocumentedFunction(): String {
    // No KDoc here
    val simpleReturn = "undocumented"
    return simpleReturn
}
'''
        
        adapter = make_adapter(KotlinCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx_kt(code))
        
        # Both function signatures should be preserved
        assert "fun documentedFunction(): String" in result
        assert "fun undocumentedFunction(): String" in result
        
        # Only the KDoc should be preserved
        assert "/**" in result and "This function has documentation" in result
        assert "// No KDoc here" not in result
        
        # All logic should be removed
        assert "val complexLogic" not in result
        assert "val simpleReturn" not in result
        assert 'return "documented"' not in result
        assert 'return "undocumented"' not in result
        
        # Should have placeholders
        assert "// … function body omitted" in result

