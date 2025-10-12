/**
 * Kotlin module for testing literal optimization.
 */

package com.example.literals

// Short string literal (should be preserved)
const val SHORT_MESSAGE = "Hello, World!"

// Long string literal (candidate for trimming)
const val LONG_MESSAGE = """This is an extremely long message that contains a substantial amount of text content which might be considered for trimming when optimizing Kotlin code for AI context windows. The message continues with detailed explanations and verbose descriptions that may not be essential for understanding the core functionality and structure of the code. This raw string literal spans multiple conceptual lines even though it's defined as a single string literal."""

// Multi-line raw string with embedded expressions
val TEMPLATE_WITH_DATA = """
User Information:
- Name: ${getUserName()}
- Email: ${getUserEmail()}
- Registration Date: ${java.time.Instant.now()}
- Account Status: ${getAccountStatus()}
- Permissions: ${getPermissions().joinToString()}
- Last Login: ${getLastLogin()}
- Profile Completeness: ${getProfileCompleteness()}%
"""

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
        "version" to "1.0.0"
    )
    
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
            ),
            "retry" to mapOf(
                "attempts" to 3,
                "delay" to 1000,
                "backoff" to "exponential"
            )
        ),
        "cache" to mapOf(
            "redis" to mapOf(
                "host" to "localhost",
                "port" to 6379,
                "db" to 0,
                "ttl" to 3600
            ),
            "memory" to mapOf(
                "maxSize" to 1000,
                "ttl" to 1800
            )
        ),
        "api" to mapOf(
            "baseUrl" to "https://api.example.com",
            "timeout" to 30000,
            "retries" to 3,
            "rateLimit" to mapOf(
                "requests" to 100,
                "window" to 60000
            )
        ),
        "features" to mapOf(
            "authentication" to true,
            "authorization" to true,
            "logging" to true,
            "monitoring" to true,
            "analytics" to false,
            "caching" to true,
            "compression" to true
        )
    )
    
    private val supportedLanguages: List<String>
    private val allowedExtensions: Set<String>
    
    init {
        // Array with many elements (trimming candidate)
        supportedLanguages = listOf(
            "english", "spanish", "french", "german", "italian", "portuguese",
            "russian", "chinese", "japanese", "korean", "arabic", "hindi",
            "dutch", "swedish", "norwegian", "danish", "finnish", "polish",
            "czech", "hungarian", "romanian", "bulgarian", "croatian", "serbian"
        )
        
        // Set with many elements
        allowedExtensions = setOf(
            ".kt", ".kts", ".java", ".scala",
            ".py", ".js", ".ts", ".jsx", ".tsx",
            ".c", ".cpp", ".cs", ".go", ".rs",
            ".php", ".rb", ".swift", ".clj"
        )
    }
    
    fun processData(): DataContainer {
        // Function with various literal data
        val smallArray = listOf("one", "two", "three")
        
        val largeArray = listOf(
            "item_001", "item_002", "item_003", "item_004", "item_005",
            "item_006", "item_007", "item_008", "item_009", "item_010",
            "item_011", "item_012", "item_013", "item_014", "item_015",
            "item_016", "item_017", "item_018", "item_019", "item_020",
            "item_021", "item_022", "item_023", "item_024", "item_025",
            "item_026", "item_027", "item_028", "item_029", "item_030"
        )
        
        val nestedData = mapOf(
            "level1" to mapOf(
                "level2" to mapOf(
                    "level3" to mapOf(
                        "data" to listOf(
                            mapOf("id" to 1, "name" to "First", "active" to true),
                            mapOf("id" to 2, "name" to "Second", "active" to false),
                            mapOf("id" to 3, "name" to "Third", "active" to true),
                            mapOf("id" to 4, "name" to "Fourth", "active" to true),
                            mapOf("id" to 5, "name" to "Fifth", "active" to false)
                        ),
                        "metadata" to mapOf(
                            "created" to "2024-01-01",
                            "updated" to "2024-01-15",
                            "version" to 3,
                            "checksum" to "abcdef123456"
                        )
                    )
                )
            )
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
                users.id, users.username, users.email, users.created_at,
                profiles.first_name, profiles.last_name, profiles.bio, profiles.avatar_url,
                addresses.street, addresses.city, addresses.state, addresses.postal_code, addresses.country,
                subscriptions.plan_name, subscriptions.status, subscriptions.expires_at,
                payments.amount, payments.currency, payments.payment_date, payments.method
            FROM users 
            LEFT JOIN profiles ON users.id = profiles.user_id 
            LEFT JOIN addresses ON users.id = addresses.user_id 
            LEFT JOIN subscriptions ON users.id = subscriptions.user_id 
            LEFT JOIN payments ON users.id = payments.user_id 
            WHERE users.is_active = true 
                AND users.email_verified = true 
                AND profiles.is_public = true 
                AND subscriptions.status IN ('active', 'trial') 
            ORDER BY users.created_at DESC, subscriptions.expires_at ASC 
            LIMIT 100 OFFSET 0
        """.trimIndent()
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
        "SWITCHING_PROTOCOLS" to 101,
        "OK" to 200,
        "CREATED" to 201,
        "ACCEPTED" to 202,
        "NON_AUTHORITATIVE_INFORMATION" to 203,
        "NO_CONTENT" to 204,
        "RESET_CONTENT" to 205,
        "PARTIAL_CONTENT" to 206,
        "MULTIPLE_CHOICES" to 300,
        "MOVED_PERMANENTLY" to 301,
        "FOUND" to 302,
        "SEE_OTHER" to 303,
        "NOT_MODIFIED" to 304,
        "USE_PROXY" to 305,
        "TEMPORARY_REDIRECT" to 307,
        "PERMANENT_REDIRECT" to 308,
        "BAD_REQUEST" to 400,
        "UNAUTHORIZED" to 401,
        "PAYMENT_REQUIRED" to 402,
        "FORBIDDEN" to 403,
        "NOT_FOUND" to 404,
        "METHOD_NOT_ALLOWED" to 405,
        "NOT_ACCEPTABLE" to 406,
        "PROXY_AUTHENTICATION_REQUIRED" to 407,
        "REQUEST_TIMEOUT" to 408,
        "CONFLICT" to 409,
        "GONE" to 410,
        "LENGTH_REQUIRED" to 411,
        "PRECONDITION_FAILED" to 412,
        "PAYLOAD_TOO_LARGE" to 413,
        "URI_TOO_LONG" to 414,
        "UNSUPPORTED_MEDIA_TYPE" to 415,
        "RANGE_NOT_SATISFIABLE" to 416,
        "EXPECTATION_FAILED" to 417,
        "INTERNAL_SERVER_ERROR" to 500,
        "NOT_IMPLEMENTED" to 501,
        "BAD_GATEWAY" to 502,
        "SERVICE_UNAVAILABLE" to 503,
        "GATEWAY_TIMEOUT" to 504,
        "HTTP_VERSION_NOT_SUPPORTED" to 505
    ),
    "ERROR_MESSAGES" to mapOf(
        "VALIDATION_FAILED" to "Input validation failed. Please check your data and try again.",
        "AUTHENTICATION_REQUIRED" to "Authentication is required to access this resource.",
        "AUTHORIZATION_FAILED" to "You do not have permission to perform this action.",
        "RESOURCE_NOT_FOUND" to "The requested resource could not be found on the server.",
        "INTERNAL_ERROR" to "An internal server error occurred. Please try again later.",
        "RATE_LIMIT_EXCEEDED" to "Rate limit exceeded. Please wait before making another request.",
        "INVALID_REQUEST_FORMAT" to "The request format is invalid. Please check the documentation."
    )
)

// Helper functions that use literal data
fun getUserName(): String = "John Doe"
fun getUserEmail(): String = "john.doe@example.com"
fun getAccountStatus(): String = "active"
fun getPermissions(): List<String> = listOf("read", "write", "admin")
fun getLastLogin(): String = "2024-01-15T10:30:00Z"
fun getProfileCompleteness(): Int = 85

