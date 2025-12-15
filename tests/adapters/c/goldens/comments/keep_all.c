/**
 * C module for testing comment optimization.
 *
 * This module contains various types of comments to test
 * different comment processing policies and edge cases.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Single-line comment at module level
#define MODULE_VERSION "1.0.0"  // TODO: Move to config file

/**
 * Structure with documentation comments.
 * This should be preserved when keeping documentation comments.
 */
typedef struct {
    int id;           // User identifier
    char* name;       // FIXME: Should validate name format
    char* email;      // User's email address
    // Optional profile data
    void* profile;
} User;

typedef struct {
    char* bio;
    char* avatar;
} Profile;

typedef struct {
    void* config;     // Service configuration
    void* logger;     // Optional logger
} CommentedService;

/**
 * Service constructor with detailed documentation.
 *
 * Initializes the service with the provided configuration
 * and sets up the logging system if logger is provided.
 *
 * @param config Service configuration object
 * @param logger Logger instance (can be NULL)
 * @return Pointer to initialized service or NULL on failure
 */
CommentedService* commented_service_new(void* config, void* logger) {
    CommentedService* service = (CommentedService*)malloc(sizeof(CommentedService));
    if (!service) return NULL;

    service->config = config;
    service->logger = logger;

    // Initialize service
    // (implementation details here)

    // TODO: Add configuration validation
    // FIXME: Logger should be required, not optional

    return service;
}

/**
 * Process user data with validation.
 *
 * This function performs comprehensive user data processing including
 * validation, transformation, and persistence operations. It handles
 * various edge cases and provides detailed error reporting.
 *
 * @param userData The user data to process
 * @return The processed user or NULL on error
 */
User* process_user(User* userData) {
    // Pre-processing validation
    if (!userData) {
        fprintf(stderr, "User data is required\n");
        return NULL;
    }

    /*
     * Multi-line comment explaining
     * the validation logic that follows.
     * This is important business logic.
     */
    int is_valid = 1;
    if (!userData->name || strlen(userData->name) == 0) {
        // Log validation failure
        fprintf(stderr, "Validation failed: name is required\n");
        is_valid = 0;
    }

    if (!userData->email || strlen(userData->email) == 0) {
        fprintf(stderr, "Validation failed: email is required\n");
        is_valid = 0;
    }

    if (!is_valid) {
        return NULL;
    }

    // Transform data for storage
    User* transformed = transform_user_data(userData);

    // Persist to database
    // NOTE: This could be optimized with batch operations
    User* saved = save_user(transformed);

    return saved;  // Return the saved user
}

static User* transform_user_data(User* userData) {
    /*
     * Data transformation logic.
     * Convert partial user data to complete user object
     * with all required fields populated.
     */
    User* user = (User*)malloc(sizeof(User));
    if (!user) return NULL;

    user->id = generate_user_id();      // Generate unique ID
    user->name = strdup(userData->name); // Clean up name
    user->email = strdup(userData->email); // Normalize email
    user->profile = userData->profile ? userData->profile : NULL;

    return user;
}

/**
 * Generate unique user ID.
 * @return Generated user ID
 */
static int generate_user_id(void) {
    // Simple ID generation
    return rand() % 1000000;
}

// TODO: Implement proper persistence layer
static User* save_user(User* user) {
    // Simulate database save
    // In real implementation, this would use a database

    // Log save operation
    if (user) {
        printf("Saving user: %d\n", user->id);
    }

    // Simulate async operation
    // (sleep or similar in real code)

    return user;  // Return saved user
}

/**
 * Utility function with comprehensive documentation.
 *
 * @param input The input string to process
 * @return Processed string result (caller must free)
 */
char* process_string(const char* input) {
    // Input validation
    if (!input || strlen(input) == 0) {
        return strdup("");  // Return empty string for invalid input
    }

    /* Process the string:
     * 1. Trim whitespace
     * 2. Convert to lowercase
     * 3. Remove special characters
     */
    size_t len = strlen(input);
    char* result = (char*)malloc(len + 1);
    if (!result) return NULL;

    // Process implementation
    strcpy(result, input);

    return result;  // Return processed string
}

// Module-level function without documentation
static void undocumented_helper(void) {
    // This function has no documentation comments
    // Only regular comments explaining implementation

    // Implementation details...
    const char* data = "helper data";

    // Process data
    printf("%s\n", data);  // Log the data
}

// Type definitions with comments
typedef struct {
    int is_valid;      // Whether validation passed
    char** errors;     // List of validation errors
    int error_count;   // Number of errors
} ValidationResult;

typedef struct {
    int timeout;       // Request timeout in milliseconds
    int retries;       // Number of retry attempts
    char* base_url;    // Base URL for API calls
} ServiceConfig;

/*
 * Export default configuration
 * This is used when no custom config is provided
 */
ServiceConfig DEFAULT_CONFIG = {
    5000,              // 5 second timeout
    3,                 // 3 retry attempts
    "http://localhost:3000"  // Default base URL
};
