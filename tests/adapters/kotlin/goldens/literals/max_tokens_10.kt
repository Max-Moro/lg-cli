/**
 * Kotlin module for testing literal optimization.
 */

package com.example.literals

// Short string literal (should be preserved)
const val SHORT_MESSAGE = "Hello, World!"

// Long string literal (candidate for trimming)
const val LONG_MESSAGE = """This is an extremely long message that cont…""" // literal string (−63 tokens)

// Multi-line raw string with embedded expressions
val TEMPLATE_WITH_DATA = """
User Information:
- Name: ${g…""" // literal string (−58 tokens)

data class DataContainer(
    // Small array (should be preserved)
    val tags: List<String>,
    
    // Large array (candidate for trimming)
    val items: List<String>,
    
    // Small object (should be preserved)
    val metadata: Map<String, Any>,
    
    // Large object (candidate for trimming)
    val configuration: Map<String, Any>
)

class LiteralDataManager {
    // Class properties with various literal types
    private val smallConfig = mapOf(
        "debug" to true,
        "…" to "…"
    ) // literal object (−5 tokens)
    
    private val largeConfig = mapOf(
        "…" to "…"
    ) // literal object (−334 tokens)
    
    private val supportedLanguages: List<String>
    private val allowedExtensions: Set<String>
    
    init {
        // Array with many elements (trimming candidate)
        supportedLanguages = listOf(
            "english",
            "spanish",
            "…"
        ) // literal array (−89 tokens)
        
        // Set with many elements
        allowedExtensions = setOf(
            ".kt",
            ".kts",
            "…"
        ) // literal set (−47 tokens)
    }
    
    fun processData(): DataContainer {
        // Function with various literal data
        val smallArray = listOf("one", "two", "…")
        
        val largeArray = listOf(
            "item_001",
            "…"
        ) // literal array (−146 tokens)
        
        val nestedData = mapOf(
            "…" to "…"
        ) // literal object (−205 tokens)
        
        return DataContainer(
            tags = smallArray,
            items = largeArray,
            metadata = mapOf("type" to "test", "…" to "…"), // literal object (−2 tokens)
            configuration = nestedData
        )
    }
    
    fun getLongQuery(): String {
        // Very long SQL-like query string
        return """
            SELECT 
                use…""" /* literal string (−181 tokens) */.trimIndent()
    }
}

// Module-level constants with different sizes
val SMALL_CONSTANTS = mapOf(
    "API_VERSION" to "v1",
    "…" to "…"
) // literal object (−2 tokens)

val LARGE_CONSTANTS = mapOf(
    "…" to "…"
) // literal object (−556 tokens)

// Helper functions that use literal data
fun getUserName(): String = "John Doe"
fun getUserEmail(): String = "john.doe@example.com"
fun getAccountStatus(): String = "active"
fun getPermissions(): List<String> = listOf("read", "write", "…")
fun getLastLogin(): String = "2024-01-15T1…" // literal string (−5 tokens)
fun getProfileCompleteness(): Int = 85
