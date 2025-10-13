"""
Tests for public API filtering in Kotlin adapter.
"""

from lg.adapters.kotlin import KotlinCfg
from .conftest import lctx_kt, do_public_api, assert_golden_match, make_adapter


class TestKotlinPublicApiOptimization:
    """Test public API filtering for Kotlin code."""
    
    def test_public_api_only_basic(self, do_public_api):
        """Test basic public API filtering."""
        adapter = make_adapter(KotlinCfg(public_api_only=True))
        
        result, meta = adapter.process(lctx_kt(do_public_api))
        
        # Private elements should be removed
        assert meta.get("kotlin.removed.method", 0) == 14
        assert meta.get("kotlin.removed.function", 0) == 3
        assert meta.get("kotlin.removed.object", 0) == 1
        assert meta.get("kotlin.removed.property", 0) == 9
        assert meta.get("kotlin.removed.class", 0) == 5
        
        # Public exports should remain
        assert "class UserManager" in result
        assert "fun createUserManager" in result
        
        # Private elements should be removed
        assert "private val internalCache" not in result
        assert "private fun validateUserData" not in result
        assert "private class InternalLogger" not in result

        assert_golden_match(result, "public_api", "basic")

    def test_visibility_detection(self):
        """Test detection of public/private elements."""
        code = '''
// Public elements
class PublicClass {
    fun publicMethod() {}
    private fun privateMethod() {}
}

fun publicFunction() {}

private fun privateFunction() {}

const val PUBLIC_CONSTANT = "value"
private const val PRIVATE_CONSTANT = "value"
'''
        
        adapter = make_adapter(KotlinCfg(public_api_only=True))
        
        result, meta = adapter.process(lctx_kt(code))
        
        # Public elements should remain
        assert "class PublicClass" in result
        assert "fun publicMethod" in result
        assert "fun publicFunction" in result
        assert "PUBLIC_CONSTANT" in result
        
        # Private elements should be removed
        assert "private fun privateFunction" not in result
        assert "PRIVATE_CONSTANT" not in result

    def test_data_class_and_companion_objects(self):
        """Test data classes and companion objects in public API."""
        code = '''
data class User(
    val id: Long,
    val name: String,
    private val internalData: String
)

class Service {
    companion object {
        fun create(): Service = Service()
        private fun internalCreate(): Service = Service()
    }
}

private data class InternalData(val value: String)
'''
        
        adapter = make_adapter(KotlinCfg(public_api_only=True))
        
        result, meta = adapter.process(lctx_kt(code))
        
        # Public data class should remain
        assert "data class User" in result
        
        # Companion object's public methods should remain
        assert "companion object" in result
        assert "fun create()" in result
        
        # Private data class should be removed
        assert "InternalData" not in result

    def test_annotation_handling(self):
        """Test handling of annotations in public API mode."""
        code = '''
@Target(AnnotationTarget.FUNCTION)
annotation class Logged

@Logged
class PublicClass {
    @Logged
    fun publicMethod() {}
    
    @Logged
    private fun privateMethod() {}
}

@Logged
private class PrivateClass {
    fun method() {}
}
'''
        
        adapter = make_adapter(KotlinCfg(public_api_only=True))
        
        result, meta = adapter.process(lctx_kt(code))
        
        # Public annotated elements should preserve annotations
        assert "@Logged" in result
        assert "class PublicClass" in result
        
        # Private annotated elements should be removed with annotations
        assert "PrivateClass" not in result

