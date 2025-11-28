/**
 * JavaScript module for testing comment optimization.
 *
 * This module contains various types of comments to test
 * different comment processing policies and edge cases.
 */

// Single-line comment at module level
const MODULE_VERSION = '1.0.0'; // TODO: Move to config file

/**
 * User class with JSDoc documentation.
 * This should be preserved when keeping documentation comments.
 */
class User {
    constructor(id, name, email) {
        this.id = id;           // User identifier
        this.name = name;       // FIXME: Should validate name format
        this.email = email;     // User's email address
        // Optional profile data
        this.profile = null;
    }
}

export class CommentedService {
    /**
     * Class constructor with detailed JSDoc.
     *
     * @param {Object} config Service configuration object
     * @param {Object} logger Optional logger instance
     */
    constructor(config, logger) {
        this.config = config;  // Service configuration
        this.logger = logger;  // Optional logger

        // Initialize service
        this.#initialize();

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
     * @param {Object} userData - The user data to process
     * @returns {Promise<User>} Promise resolving to processed user
     * @throws {ValidationError} when data is invalid
     */
    async processUser(userData) {
        // Pre-processing validation
        if (!userData) {
            throw new Error('User data is required');
        }

        /*
         * Multi-line comment explaining
         * the validation logic that follows.
         * This is important business logic.
         */
        const validationResult = this.#validateUser(userData);
        if (!validationResult.isValid) {
            // Log validation failure
            this.logger?.error('Validation failed', validationResult.errors);
            throw new ValidationError(validationResult.errors);
        }

        // Transform data for storage
        const transformedData = this.#transformUserData(userData);

        // Persist to database
        // NOTE: This could be optimized with batch operations
        const savedUser = await this.#saveUser(transformedData);

        return savedUser;  // Return the saved user
    }

    #validateUser(userData) {
        // Simple validation logic
        const errors = [];

        // Check required fields
        if (!userData.name) {
            errors.push('Name is required');  // Error message
        }

        if (!userData.email) {
            errors.push('Email is required');
        }

        // Validate email format
        // Regular expression for email validation
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (userData.email && !emailRegex.test(userData.email)) {
            errors.push('Invalid email format');
        }

        return {
            isValid: errors.length === 0,
            errors
        };
    }

    // Private helper method
    #transformUserData(userData) {
        /*
         * Data transformation logic.
         * Convert partial user data to complete user object
         * with all required fields populated.
         */
        return new User(
            this.#generateUserId(),    // Generate unique ID
            userData.name.trim(),      // Clean up name
            userData.email.toLowerCase(),  // Normalize email
        );
    }

    /**
     * Generate unique user ID.
     * @returns {number} Generated user ID
     */
    #generateUserId() {
        // Simple ID generation
        return Math.floor(Math.random() * 1000000);
    }

    // TODO: Implement proper persistence layer
    async #saveUser(user) {
        // Simulate database save
        // In real implementation, this would use a database

        // Log save operation
        this.logger?.info('Saving user', { id: user.id });

        // Simulate async operation
        await new Promise(resolve => setTimeout(resolve, 100));

        return user;  // Return saved user
    }

    #initialize() {
        // Service initialization
        // This method sets up the service state

        // TODO: Add proper initialization logic
        // WARNING: This is a placeholder implementation
    }
}

/**
 * Utility function with comprehensive documentation.
 *
 * @param {string} input The input string to process
 * @returns {string} Processed string result
 */
export function processString(input) {
    // Input validation
    if (!input || typeof input !== 'string') {
        return '';  // Return empty string for invalid input
    }

    /* Process the string:
     * 1. Trim whitespace
     * 2. Convert to lowercase
     * 3. Remove special characters
     */
    const trimmed = input.trim();
    const lowercase = trimmed.toLowerCase();
    const cleaned = lowercase.replace(/[^a-z0-9\s]/g, '');

    return cleaned;  // Return processed string
}

// Module-level function without JSDoc
function undocumentedHelper() {
    // This function has no JSDoc documentation
    // Only regular comments explaining implementation

    // Implementation details...
    const data = 'helper data';

    // Process data
    console.log(data);  // Log the data
}

// Validation error class
class ValidationError extends Error {
    constructor(errors) {  // Error details
        super(`Validation failed: ${errors.join(', ')}`);
        this.errors = errors;
    }
}

/*
 * Export default configuration
 * This is used when no custom config is provided
 */
export const DEFAULT_CONFIG = {
    timeout: 5000,    // 5 second timeout
    retries: 3,       // 3 retry attempts
    baseUrl: 'http://localhost:3000'  // Default base URL
};
