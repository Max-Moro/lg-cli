/**
 * Kotlin module for testing public API filtering.
 */

package com.example.publicapi

import java.time.Instant

// Public module-level constants (should be preserved)
const val PUBLIC_VERSION = "1.0.0"
const val API_ENDPOINT = "https://api.example.com"

// Private module-level constants (should be filtered out)
// … 2 properties omitted

// Public data class (should be preserved)
data class User(
    val id: Long,
    val name: String,
    val email: String,
    val createdAt: Instant
)

// Private data class (not exported, should be filtered out)
// … class omitted

// Public type alias (should be preserved)
typealias UserRole = String

// Public class with mixed visibility members
class UserManager(private val apiEndpoint: String = API_ENDPOINT) {
    // Public properties
    val version: String = PUBLIC_VERSION
    var isInitialized: Boolean = false
    
    // Private properties (should be filtered out with public_api_only)
    // … 2 properties omitted
    
    // Protected properties (should be filtered out)
    // … property omitted
    
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
    // … 4 methods omitted
    
    // Protected methods (should be filtered out)
    // … 2 methods omitted
    
    // Public readonly property with getter
    val userCount: Int
        get() = internalCache.size
    
    // Private readonly property with getter (should be filtered out)
    // … property omitted
    
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
        // … method omitted
    }
}

// Private class (not exported, should be filtered out)
// … class omitted

// Public abstract class (should be preserved)
abstract class BaseService {
    // … property omitted
    
    abstract suspend fun initialize()
    
    fun getServiceInfo(): Map<String, String> {
        return mapOf(
            "name" to serviceName,
            "version" to PUBLIC_VERSION
        )
    }
    
    // Protected abstract method (should be filtered out in public API)
    // … method omitted
}

// Public enum (should be preserved)
enum class UserStatus {
    ACTIVE,
    INACTIVE,
    PENDING,
    BANNED
}

// Private enum (not exported, should be filtered out)
// … class omitted

// Public functions (should be preserved)
fun createUserManager(endpoint: String? = null): UserManager {
    return UserManager(endpoint ?: API_ENDPOINT)
}

fun isValidUserRole(role: Any): Boolean {
    return UserManager.validateUserRole(role.toString())
}

// Private functions (not exported, should be filtered out)
// … 2 functions omitted

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
    // … method omitted
}

// Private object (not exported, should be filtered out)
// … object omitted

// ============= Examples with Kotlin annotations =============

// Simple annotation examples
@Target(AnnotationTarget.FUNCTION, AnnotationTarget.CLASS)
annotation class Logged

@Target(AnnotationTarget.FUNCTION)
annotation class Validate

// … class omitted

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
    
    // … method omitted
}

// Annotated functions
// … function omitted

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
    
    // … 2 methods omitted
}

// Multiple stacked annotations on private elements
// … class omitted

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
