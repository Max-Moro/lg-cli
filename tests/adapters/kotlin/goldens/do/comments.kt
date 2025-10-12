/**
 * Kotlin module for testing comment optimization.
 * 
 * This module contains various types of comments to test
 * different comment processing policies and edge cases.
 */

package com.example.comments

import kotlinx.coroutines.flow.Flow

// Single-line comment at module level
const val MODULE_VERSION = "1.0.0" // TODO: Move to config file

/**
 * Data class with KDoc documentation.
 * This should be preserved when keeping documentation comments.
 */
data class User(
    val id: Long,        // User identifier
    val name: String,    // FIXME: Should validate name format
    val email: String,   // User's email address
    // Optional profile data
    val profile: Profile? = null
)

data class Profile(
    val bio: String,
    val avatar: String? = null
)

class CommentedService(
    private val config: ServiceConfig,  // Service configuration
    private val logger: Logger? = null  // Optional logger
) {
    /**
     * Class constructor with detailed KDoc.
     * 
     * Initializes the service with the provided configuration
     * and sets up the logging system if logger is provided.
     */
    init {
        // Initialize service
        initialize()
        
        // TODO: Add configuration validation
        // FIXME: Logger should be required, not optional
    }
    
    /**
     * Process user data with validation.
     * 
     * This method performs comprehensive user data processing including
     * validation, transformation, and persistence operations. It handles
     * various edge cases and provides detailed error reporting.
     * 
     * @param userData The user data to process
     * @return The processed user
     * @throws ValidationException when data is invalid
     */
    suspend fun processUser(userData: Map<String, Any?>): User {
        // Pre-processing validation
        if (userData.isEmpty()) {
            throw IllegalArgumentException("User data is required")
        }
        
        /*
         * Multi-line comment explaining
         * the validation logic that follows.
         * This is important business logic.
         */
        val validationResult = validateUser(userData)
        if (!validationResult.isValid) {
            // Log validation failure
            logger?.error("Validation failed: ${validationResult.errors}")
            throw ValidationException(validationResult.errors)
        }
        
        // Transform data for storage
        val transformedData = transformUserData(userData)
        
        // Persist to database
        // NOTE: This could be optimized with batch operations
        val savedUser = saveUser(transformedData)
        
        return savedUser  // Return the saved user
    }
    
    private fun validateUser(userData: Map<String, Any?>): ValidationResult {
        // Simple validation logic
        val errors = mutableListOf<String>()
        
        // Check required fields
        if (userData["name"] == null) {
            errors.add("Name is required")  // Error message
        }
        
        if (userData["email"] == null) {
            errors.add("Email is required")
        }
        
        // Validate email format
        // Regular expression for email validation
        val emailRegex = Regex("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$")
        val email = userData["email"] as? String
        if (email != null && !emailRegex.matches(email)) {
            errors.add("Invalid email format")
        }
        
        return ValidationResult(
            isValid = errors.isEmpty(),
            errors = errors
        )
    }
    
    // Private helper method
    private fun transformUserData(userData: Map<String, Any?>): User {
        /*
         * Data transformation logic.
         * Convert partial user data to complete user object
         * with all required fields populated.
         */
        return User(
            id = generateUserId(),    // Generate unique ID
            name = (userData["name"] as String).trim(),  // Clean up name
            email = (userData["email"] as String).lowercase(),  // Normalize email
            profile = (userData["profile"] as? Profile) ?: Profile(bio = "")  // Default profile
        )
    }
    
    /** 
     * Generate unique user ID.
     * @return Generated user ID
     */
    private fun generateUserId(): Long {
        // Simple ID generation
        return (Math.random() * 1_000_000).toLong()
    }
    
    // TODO: Implement proper persistence layer
    private suspend fun saveUser(user: User): User {
        // Simulate database save
        // In real implementation, this would use a database
        
        // Log save operation
        logger?.info("Saving user: ${user.id}")
        
        // Simulate async operation
        kotlinx.coroutines.delay(100)
        
        return user  // Return saved user
    }
    
    private fun initialize() {
        // Service initialization
        // This method sets up the service state
        
        // TODO: Add proper initialization logic
        // WARNING: This is a placeholder implementation
    }
}

/**
 * Utility function with comprehensive documentation.
 * 
 * @param input The input string to process
 * @return Processed string result
 */
fun processString(input: String): String {
    // Input validation
    if (input.isEmpty()) {
        return ""  // Return empty string for invalid input
    }
    
    /* Process the string:
     * 1. Trim whitespace
     * 2. Convert to lowercase
     * 3. Remove special characters
     */
    val trimmed = input.trim()
    val lowercase = trimmed.lowercase()
    val cleaned = lowercase.replace(Regex("[^a-z0-9\\s]"), "")
    
    return cleaned  // Return processed string
}

// Module-level function without KDoc
fun undocumentedHelper() {
    // This function has no KDoc documentation
    // Only regular comments explaining implementation
    
    // Implementation details...
    val data = "helper data"
    
    // Process data
    println(data)  // Log the data
}

// Type definitions with comments
data class ValidationResult(
    val isValid: Boolean,     // Whether validation passed
    val errors: List<String>  // List of validation errors
)

data class ServiceConfig(
    // Configuration options
    val timeout: Long,      // Request timeout in milliseconds
    val retries: Int,       // Number of retry attempts
    val baseUrl: String     // Base URL for API calls
)

// Logger interface
interface Logger {
    fun info(message: String, data: Any? = null)    // Info level logging
    fun error(message: String, data: Any? = null)   // Error level logging
    fun warn(message: String, data: Any? = null)    // Warning level logging
}

// Validation error class
class ValidationException(val errors: List<String>) : Exception() {
    override val message: String
        get() = "Validation failed: ${errors.joinToString(", ")}"
}

/* 
 * Export default configuration
 * This is used when no custom config is provided
 */
val DEFAULT_CONFIG = ServiceConfig(
    timeout = 5000,    // 5 second timeout
    retries = 3,       // 3 retry attempts
    baseUrl = "http://localhost:3000"  // Default base URL
)

