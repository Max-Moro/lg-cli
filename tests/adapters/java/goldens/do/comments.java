/**
 * Java module for testing comment optimization.
 *
 * This module contains various types of comments to test
 * different comment processing policies and edge cases.
 */

package com.example.comments;

import java.util.List;
import java.util.ArrayList;

// Single-line comment at module level
public class Constants {
    public static final String MODULE_VERSION = "1.0.0"; // TODO: Move to config file
}

/**
 * Data class with Javadoc documentation.
 * This should be preserved when keeping documentation comments.
 */
public class User {
    private final long id;        // User identifier
    private final String name;    // FIXME: Should validate name format
    private final String email;   // User's email address
    // Optional profile data
    private final Profile profile;

    public User(long id, String name, String email, Profile profile) {
        this.id = id;
        this.name = name;
        this.email = email;
        this.profile = profile;
    }

    public long getId() { return id; }
    public String getName() { return name; }
    public String getEmail() { return email; }
    public Profile getProfile() { return profile; }
}

public class Profile {
    private final String bio;
    private final String avatar;

    public Profile(String bio, String avatar) {
        this.bio = bio;
        this.avatar = avatar;
    }

    public String getBio() { return bio; }
    public String getAvatar() { return avatar; }
}

public class CommentedService {
    private final ServiceConfig config;  // Service configuration
    private final Logger logger;         // Optional logger

    /**
     * Class constructor with detailed Javadoc.
     *
     * Initializes the service with the provided configuration
     * and sets up the logging system if logger is provided.
     *
     * @param config Service configuration object
     * @param logger Logger instance (can be null)
     */
    public CommentedService(ServiceConfig config, Logger logger) {
        this.config = config;
        this.logger = logger;

        // Initialize service
        initialize();

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
    public User processUser(PartialUser userData) throws ValidationException {
        // Pre-processing validation
        if (userData == null) {
            throw new IllegalArgumentException("User data is required");
        }

        /*
         * Multi-line comment explaining
         * the validation logic that follows.
         * This is important business logic.
         */
        ValidationResult validationResult = validateUser(userData);
        if (!validationResult.isValid()) {
            // Log validation failure
            if (logger != null) {
                logger.error("Validation failed: " + validationResult.getErrors());
            }
            throw new ValidationException(validationResult.getErrors());
        }

        // Transform data for storage
        User transformedData = transformUserData(userData);

        // Persist to database
        // NOTE: This could be optimized with batch operations
        User savedUser = saveUser(transformedData);

        return savedUser;  // Return the saved user
    }

    private ValidationResult validateUser(PartialUser userData) {
        // Simple validation logic
        List<String> errors = new ArrayList<>();

        // Check required fields
        if (userData.getName() == null || userData.getName().isEmpty()) {
            errors.add("Name is required");  // Error message
        }

        if (userData.getEmail() == null || userData.getEmail().isEmpty()) {
            errors.add("Email is required");
        }

        // Validate email format
        // Regular expression for email validation
        String emailRegex = "^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$";
        if (userData.getEmail() != null && !userData.getEmail().matches(emailRegex)) {
            errors.add("Invalid email format");
        }

        return new ValidationResult(errors.isEmpty(), errors);
    }

    // Private helper method
    private User transformUserData(PartialUser userData) {
        /*
         * Data transformation logic.
         * Convert partial user data to complete user object
         * with all required fields populated.
         */
        return new User(
            generateUserId(),    // Generate unique ID
            userData.getName().trim(),  // Clean up name
            userData.getEmail().toLowerCase(),  // Normalize email
            userData.getProfile() != null ? userData.getProfile() : new Profile("", null)  // Default profile
        );
    }

    /**
     * Generate unique user ID.
     * @return Generated user ID
     */
    private long generateUserId() {
        // Simple ID generation
        return (long) (Math.random() * 1000000);
    }

    // TODO: Implement proper persistence layer
    private User saveUser(User user) {
        // Simulate database save
        // In real implementation, this would use a database

        // Log save operation
        if (logger != null) {
            logger.info("Saving user: " + user.getId());
        }

        // Simulate async operation
        try {
            Thread.sleep(100);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        return user;  // Return saved user
    }

    private void initialize() {
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
public class StringProcessor {
    public static String processString(String input) {
        // Input validation
        if (input == null || input.isEmpty()) {
            return "";  // Return empty string for invalid input
        }

        /* Process the string:
         * 1. Trim whitespace
         * 2. Convert to lowercase
         * 3. Remove special characters
         */
        String trimmed = input.trim();
        String lowercase = trimmed.toLowerCase();
        String cleaned = lowercase.replaceAll("[^a-z0-9\\s]", "");

        return cleaned;  // Return processed string
    }
}

// Module-level function without Javadoc
class UndocumentedHelper {
    static void undocumentedHelper() {
        // This function has no Javadoc documentation
        // Only regular comments explaining implementation

        // Implementation details...
        String data = "helper data";

        // Process data
        System.out.println(data);  // Log the data
    }
}

// Type definitions with comments
class ValidationResult {
    private final boolean isValid;     // Whether validation passed
    private final List<String> errors;  // List of validation errors

    public ValidationResult(boolean isValid, List<String> errors) {
        this.isValid = isValid;
        this.errors = errors;
    }

    public boolean isValid() { return isValid; }
    public List<String> getErrors() { return errors; }
}

class ServiceConfig {
    // Configuration options
    private final long timeout;      // Request timeout in milliseconds
    private final int retries;       // Number of retry attempts
    private final String baseUrl;    // Base URL for API calls

    public ServiceConfig(long timeout, int retries, String baseUrl) {
        this.timeout = timeout;
        this.retries = retries;
        this.baseUrl = baseUrl;
    }

    public long getTimeout() { return timeout; }
    public int getRetries() { return retries; }
    public String getBaseUrl() { return baseUrl; }
}

// Logger interface
interface Logger {
    void info(String message);    // Info level logging
    void error(String message);   // Error level logging
    void warn(String message);    // Warning level logging
}

// Validation error class
class ValidationException extends Exception {
    private final List<String> errors;  // Error details

    public ValidationException(List<String> errors) {
        super("Validation failed: " + String.join(", ", errors));
        this.errors = errors;
    }

    public List<String> getErrors() { return errors; }
}

class PartialUser {
    private String name;
    private String email;
    private Profile profile;

    public String getName() { return name; }
    public String getEmail() { return email; }
    public Profile getProfile() { return profile; }

    public void setName(String name) { this.name = name; }
    public void setEmail(String email) { this.email = email; }
    public void setProfile(Profile profile) { this.profile = profile; }
}

/*
 * Export default configuration
 * This is used when no custom config is provided
 */
class DefaultConfig {
    public static final ServiceConfig DEFAULT_CONFIG = new ServiceConfig(
        5000,    // 5 second timeout
        3,       // 3 retry attempts
        "http://localhost:3000"  // Default base URL
    );
}
