/**
 * Kotlin module for testing public API filtering.
 */

package com.example.publicapi

import java.time.Instant

// Public module-level constants (should be preserved)
const val PUBLIC_VERSION = "1.0.0"
const val API_ENDPOINT = "https://api.example.com"

// Private module-level constants (should be filtered out)
private const val PRIVATE_SECRET = "internal-use-only"
private const val INTERNAL_CONFIG = "debug"

// Public data class (should be preserved)
data class User(
    val id: Long,
    val name: String,
    val email: String,
    val createdAt: Instant
)

// Private data class (not exported, should be filtered out)
private data class InternalMetrics(
    val processTime: Long,
    val memoryUsage: Long
)

// Public type alias (should be preserved)
typealias UserRole = String

// Public class with mixed visibility members
class UserManager(private val apiEndpoint: String = API_ENDPOINT) {
    // Public properties
    val version: String = PUBLIC_VERSION
    var isInitialized: Boolean = false
    
    // Private properties (should be filtered out with public_api_only)
    private val internalCache: MutableMap<String, User> = mutableMapOf()
    private val metrics: InternalMetrics = InternalMetrics(0, 0)
    
    // Protected properties (should be filtered out)
    protected val config: MutableMap<String, Any> = mutableMapOf()
    
    init {
        initialize()
    }
    
    // Public methods (should be preserved)
    suspend fun createUser(userData: Map<String, Any?>): User {
        validateUserData(userData)
        
        val user = User(
            id = generateId(),
            name = userData["name"] as String,
            email = userData["email"] as String,
            createdAt = Instant.now()
        )
        
        internalCache[user.email] = user
        return user
    }
    
    suspend fun getUserById(id: Long): User? {
        for (user in internalCache.values) {
            if (user.id == id) {
                return user
            }
        }
        
        return fetchUserFromApi(id)
    }
    
    fun getAllUsers(): List<User> {
        return internalCache.values.toList()
    }
    
    // Private methods (should be filtered out)
    private fun validateUserData(userData: Map<String, Any?>) {
        if (userData["name"] == null || userData["email"] == null) {
            throw IllegalArgumentException("Name and email are required")
        }
        
        val email = userData["email"] as String
        if (!isValidEmail(email)) {
            throw IllegalArgumentException("Invalid email format")
        }
    }
    
    private fun generateId(): Long {
        return (Math.random() * 1_000_000).toLong()
    }
    
    private fun isValidEmail(email: String): Boolean {
        val emailRegex = Regex("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$")
        return emailRegex.matches(email)
    }
    
    private suspend fun fetchUserFromApi(id: Long): User? {
        return try {
            // Simulated API call
            null
        } catch (e: Exception) {
            logError("Failed to fetch user", e)
            null
        }
    }
    
    // Protected methods (should be filtered out)
    protected fun initialize() {
        config["initialized"] = true
        isInitialized = true
    }
    
    protected fun logError(message: String, error: Exception) {
        println("[UserManager] $message: ${error.message}")
    }
    
    // Public readonly property with getter
    val userCount: Int
        get() = internalCache.size
    
    // Private readonly property with getter (should be filtered out)
    private val internalState: Map<String, Any>
        get() = mapOf(
            "cacheSize" to internalCache.size,
            "metrics" to metrics
        )
    
    companion object {
        // Public static methods (should be preserved)
        fun validateUserRole(role: String): Boolean {
            return role in listOf("admin", "user", "guest")
        }
        
        fun createDefaultUser(): User {
            return User(
                id = 0,
                name = "Default User",
                email = "default@example.com",
                createdAt = Instant.now()
            )
        }
        
        // Private static methods (should be filtered out)
        private fun formatInternalId(id: Long): String {
            return "internal_${id.toString().padStart(6, '0')}"
        }
    }
}

// Private class (not exported, should be filtered out)
private class InternalLogger {
    private val logs: MutableList<String> = mutableListOf()
    
    fun log(message: String) {
        logs.add("${Instant.now()}: $message")
    }
    
    fun getLogs(): List<String> {
        return logs.toList()
    }
    
    private fun clearLogs() {
        logs.clear()
    }
}

// Public abstract class (should be preserved)
abstract class BaseService {
    protected abstract val serviceName: String
    
    abstract suspend fun initialize()
    
    fun getServiceInfo(): Map<String, String> {
        return mapOf(
            "name" to serviceName,
            "version" to PUBLIC_VERSION
        )
    }
    
    // Protected abstract method (should be filtered out in public API)
    protected abstract fun validateConfig(config: Map<String, Any>): Boolean
}

// Public enum (should be preserved)
enum class UserStatus {
    ACTIVE,
    INACTIVE,
    PENDING,
    BANNED
}

// Private enum (not exported, should be filtered out)
private enum class InternalEventType {
    USER_CREATED,
    USER_UPDATED,
    CACHE_CLEARED
}

// Public functions (should be preserved)
fun createUserManager(endpoint: String? = null): UserManager {
    return UserManager(endpoint ?: API_ENDPOINT)
}

fun isValidUserRole(role: Any): Boolean {
    return UserManager.validateUserRole(role.toString())
}

// Private functions (not exported, should be filtered out)
private fun logInternalEvent(event: InternalEventType, data: Any? = null) {
    println("[Internal] $event: $data")
}

private fun processInternalMetrics(metrics: InternalMetrics) {
    // Process internal metrics
    println("Processing metrics: $metrics")
}

// Public object (should be preserved)
object UserUtils {
    fun formatUserName(user: User): String {
        return "${user.name} (${user.email})"
    }
    
    fun getUserAge(user: User): Long {
        val now = Instant.now()
        val created = user.createdAt
        return (now.toEpochMilli() - created.toEpochMilli()) / (1000 * 60 * 60 * 24)
    }
    
    // Private object member (should be filtered out)
    private fun internalFormatting(text: String): String {
        return text.lowercase().replace(Regex("\\s+"), "_")
    }
}

// Private object (not exported, should be filtered out)
private object InternalUtils {
    fun debugLog(message: String) {
        if (INTERNAL_CONFIG == "debug") {
            println("[Debug] $message")
        }
    }
    
    fun <T> measurePerformance(fn: () -> T): T {
        val start = System.nanoTime()
        val result = fn()
        val end = System.nanoTime()
        println("Performance: ${(end - start) / 1_000_000}ms")
        return result
    }
}

// ============= Examples with Kotlin annotations =============

// Simple annotation examples
@Target(AnnotationTarget.FUNCTION, AnnotationTarget.CLASS)
annotation class Logged

@Target(AnnotationTarget.FUNCTION)
annotation class Validate

@Logged
private class PrivateAnnotatedClass {
    /**
     * Private class with annotation - should be removed completely including @Logged.
     */
    
    private var data: String = "private"
    
    @Validate
    private fun processData(): String {
        return data.uppercase()
    }
}

@Logged
@Validate
class PublicAnnotatedClass {
    /**
     * Public class with multiple annotations - should be preserved with annotations.
     */
    
    var data: String = "public"
    
    @Logged
    fun processData(): String {
        return data.uppercase()
    }
    
    @Validate
    private fun internalProcess() {
        // Private method with annotation - should remove method and annotation
    }
}

// Annotated functions
@Logged
private fun privateAnnotatedFunction(data: String): String {
    /**
     * Private function with annotation - should remove function and @Logged annotation.
     */
    return data.lowercase()
}

@Logged
@Validate
fun publicAnnotatedFunction(data: String): String {
    /**
     * Public function with annotations - should preserve function and annotations.
     */
    return data.uppercase()
}

// Class with mixed annotated members
class MixedAnnotatedClass {
    @Logged
    fun publicAnnotatedMethod() {
        // Public method with annotation - should preserve both
    }
    
    @Logged
    @Validate
    private fun privateAnnotatedMethod() {
        // Private method with annotations - should remove method and both annotations
    }
    
    @Validate
    protected fun protectedAnnotatedMethod() {
        // Protected method with annotation - should remove method and annotation
    }
}

// Multiple stacked annotations on private elements
@Logged
@Validate
private class PrivateMultiAnnotatedClass {
    /**
     * Private class with multiple annotations - should remove class and all annotations.
     */
    
    @Logged
    @Validate
    private fun multiAnnotatedMethod() {
        // Multiple annotations on private method
    }
}

@Logged
@Validate
class PublicMultiAnnotatedClass {
    /**
     * Public class with multiple annotations - should preserve class and all annotations.
     */
    
    @Logged
    @Validate
    fun multiAnnotatedMethod() {
        // Multiple annotations on public method - should preserve all
    }
}

