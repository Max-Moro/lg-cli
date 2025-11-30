/**
 * Scala module for testing comment optimization.
 *
 * This module contains various types of comments to test
 * different comment processing policies and edge cases.
 */

package com.example.comments

// Single-line comment at module level
object Constants {
  val MODULE_VERSION = "1.0.0" // TODO: Move to config file
}

/**
 * Case class with Scaladoc documentation.
 * This should be preserved when keeping documentation comments.
 */
case class User(
  id: Long,        // User identifier
  name: String,    // FIXME: Should validate name format
  email: String,   // User's email address
  // Optional profile data
  profile: Option[Profile] = None
)

case class Profile(
  bio: String,
  avatar: Option[String] = None
)

class CommentedService(
  private val config: ServiceConfig,  // Service configuration
  private val logger: Option[Logger] = None  // Optional logger
) {
  /**
   * Class initialization with detailed Scaladoc.
   *
   * Initializes the service with the provided configuration
   * and sets up the logging system if logger is provided.
   */
  initialize()

  // TODO: Add configuration validation
  // FIXME: Logger should be required, not optional

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
  def processUser(userData: Map[String, Any]): User = {
    // Pre-processing validation
    if (userData.isEmpty) {
      throw new IllegalArgumentException("User data is required")
    }

    /*
     * Multi-line comment explaining
     * the validation logic that follows.
     * This is important business logic.
     */
    val validationResult = validateUser(userData)
    if (!validationResult.isValid) {
      // Log validation failure
      logger.foreach(_.error(s"Validation failed: ${validationResult.errors}"))
      throw new ValidationException(validationResult.errors)
    }

    // Transform data for storage
    val transformedData = transformUserData(userData)

    // Persist to database
    // NOTE: This could be optimized with batch operations
    val savedUser = saveUser(transformedData)

    savedUser  // Return the saved user
  }

  private def validateUser(userData: Map[String, Any]): ValidationResult = {
    // Simple validation logic
    val errors = scala.collection.mutable.ListBuffer[String]()

    // Check required fields
    if (!userData.contains("name")) {
      errors += "Name is required"  // Error message
    }

    if (!userData.contains("email")) {
      errors += "Email is required"
    }

    // Validate email format
    // Regular expression for email validation
    val emailRegex = "^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$".r
    userData.get("email").foreach { email =>
      if (!emailRegex.matches(email.toString)) {
        errors += "Invalid email format"
      }
    }

    ValidationResult(
      isValid = errors.isEmpty,
      errors = errors.toList
    )
  }

  // Private helper method
  private def transformUserData(userData: Map[String, Any]): User = {
    /*
     * Data transformation logic.
     * Convert partial user data to complete user object
     * with all required fields populated.
     */
    User(
      id = generateUserId(),    // Generate unique ID
      name = userData("name").toString.trim,  // Clean up name
      email = userData("email").toString.toLowerCase,  // Normalize email
      profile = userData.get("profile").map(_.asInstanceOf[Profile])
        .orElse(Some(Profile("")))  // Default profile
    )
  }

  /**
   * Generate unique user ID.
   * @return Generated user ID
   */
  private def generateUserId(): Long = {
    // Simple ID generation
    (Math.random() * 1000000).toLong
  }

  // TODO: Implement proper persistence layer
  private def saveUser(user: User): User = {
    // Simulate database save
    // In real implementation, this would use a database

    // Log save operation
    logger.foreach(_.info(s"Saving user: ${user.id}"))

    // Simulate async operation
    Thread.sleep(100)

    user  // Return saved user
  }

  private def initialize(): Unit = {
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
def processString(input: String): String = {
  // Input validation
  if (input.isEmpty) {
    return ""  // Return empty string for invalid input
  }

  /* Process the string:
   * 1. Trim whitespace
   * 2. Convert to lowercase
   * 3. Remove special characters
   */
  val trimmed = input.trim
  val lowercase = trimmed.toLowerCase
  val cleaned = lowercase.replaceAll("[^a-z0-9\\s]", "")

  cleaned  // Return processed string
}

// Module-level function without Scaladoc
def undocumentedHelper(): Unit = {
  // This function has no Scaladoc documentation
  // Only regular comments explaining implementation

  // Implementation details...
  val data = "helper data"

  // Process data
  println(data)  // Log the data
}

// Type definitions with comments
case class ValidationResult(
  isValid: Boolean,     // Whether validation passed
  errors: List[String]  // List of validation errors
)

case class ServiceConfig(
  // Configuration options
  timeout: Long,      // Request timeout in milliseconds
  retries: Int,       // Number of retry attempts
  baseUrl: String     // Base URL for API calls
)

// Logger trait
trait Logger {
  def info(message: String, data: Any = null): Unit    // Info level logging
  def error(message: String, data: Any = null): Unit   // Error level logging
  def warn(message: String, data: Any = null): Unit    // Warning level logging
}

// Validation error class
class ValidationException(val errors: List[String]) extends Exception {
  override def getMessage: String = s"Validation failed: ${errors.mkString(", ")}"
}

/*
 * Default configuration object
 * This is used when no custom config is provided
 */
object DefaultConfig {
  val DEFAULT_CONFIG = ServiceConfig(
    timeout = 5000,    // 5 second timeout
    retries = 3,       // 3 retry attempts
    baseUrl = "http://localhost:3000"  // Default base URL
  )
}
