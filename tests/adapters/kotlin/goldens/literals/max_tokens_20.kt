/**
 * Kotlin module for testing literal optimization.
 */

package com.example.literals

// Short string literal (should be preserved)
const val SHORT_MESSAGE = "Hello, World!"

// Long string literal (candidate for trimming)
const val LONG_MESSAGE = """This is an extremely long message that contains a substantial amount of text content which might be consi…""" // literal string (−55 tokens)

// Multi-line raw string with embedded expressions
val TEMPLATE_WITH_DATA = """
User Information:
- Name: ${getUserName()}
- Email: ${getUserEmail()}
-…""" // literal string (−50 tokens)

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
        // … (1 more, −11 tokens)
    )
    
    private val largeConfig = mapOf(
        "database" to mapOf(
            "host" to "localhost",
            // … (5 more, −103 tokens)
        ),
        // … (3 more, −312 tokens)
    )
    
    private val supportedLanguages: List<String>
    private val allowedExtensions: Set<String>
    
    init {
        // Array with many elements (trimming candidate)
        supportedLanguages = listOf(
            "english",
            "spanish",
            "french"
            // … (21 more, −82 tokens)
        )
        
        // Set with many elements
        allowedExtensions = setOf(
            ".kt",
            ".kts",
            ".java",
            ".scala"
            // … (14 more, −43 tokens)
        )
    }
    
    fun processData(): DataContainer {
        // Function with various literal data
        val smallArray = listOf("one", "two", "three")
        
        val largeArray = listOf(
            "item_001",
            "item_002"
            // … (28 more, −140 tokens)
        )
        
        val nestedData = mapOf(
            "level1" to mapOf(
                "level2" to mapOf(
                    "level3" to mapOf(
                        "data" to listOf(
                            mapOf("id" to 1, "name" to "First", "active" to true),
                            // … (4 more, −89 tokens)
                        ),
                        // … (1 more, −142 tokens)
                    ),
                ),
            ),
        )
        
        return DataContainer(
            tags = smallArray,
            items = largeArray,
            metadata = mapOf("type" to "test", "count" to smallArray.size),
            configuration = nestedData
        )
    }
    
    fun getLongQuery(): String {
        // Very long SQL-like query string
        return """
            SELECT 
                users.id, users.username, users.email, users.created_at,…""" /* literal string (−171 tokens) */.trimIndent()
    }
}

// Module-level constants with different sizes
val SMALL_CONSTANTS = mapOf(
    "API_VERSION" to "v1",
    "DEFAULT_LIMIT" to 50
)

val LARGE_CONSTANTS = mapOf(
    "HTTP_STATUS_CODES" to mapOf(
        "CONTINUE" to 100,
        // … (40 more, −319 tokens)
    ),
    // … (1 more, −459 tokens)
)

// Helper functions that use literal data
fun getUserName(): String = "John Doe"
fun getUserEmail(): String = "john.doe@example.com"
fun getAccountStatus(): String = "active"
fun getPermissions(): List<String> = listOf("read", "write", "admin")
fun getLastLogin(): String = "2024-01-15T10:30:00Z"
fun getProfileCompleteness(): Int = 85
