/**
 * JavaScript module for testing comment optimization.
 *
 * This module contains various types of comments to test
 * different comment processing policies and edge cases.
 */

// … comment omitted
const MODULE_VERSION = '1.0.0'; // … comment omitted

/**
 * User class with JSDoc documentation.
 * This should be preserved when keeping documentation comments.
 */
class User {
    constructor(id, name, email) {
        this.id = id;           // … comment omitted
        this.name = name;       // … comment omitted
        this.email = email;     // … comment omitted
        // … comment omitted
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
        this.config = config;  // … comment omitted
        this.logger = logger;  // … comment omitted

        // … comment omitted
        this.#initialize();

        // … comment omitted
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
        // … comment omitted
        if (!userData) {
            throw new Error('User data is required');
        }

        // … comment omitted
        const validationResult = this.#validateUser(userData);
        if (!validationResult.isValid) {
            // … comment omitted
            this.logger?.error('Validation failed', validationResult.errors);
            throw new ValidationError(validationResult.errors);
        }

        // … comment omitted
        const transformedData = this.#transformUserData(userData);

        // … comment omitted
        const savedUser = await this.#saveUser(transformedData);

        return savedUser;  // … comment omitted
    }

    #validateUser(userData) {
        // … comment omitted
        const errors = [];

        // … comment omitted
        if (!userData.name) {
            errors.push('Name is required');  // … comment omitted
        }

        if (!userData.email) {
            errors.push('Email is required');
        }

        // … comment omitted
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (userData.email && !emailRegex.test(userData.email)) {
            errors.push('Invalid email format');
        }

        return {
            isValid: errors.length === 0,
            errors
        };
    }

    // … comment omitted
    #transformUserData(userData) {
        // … comment omitted
        return new User(
            this.#generateUserId(),    // … comment omitted
            userData.name.trim(),      // … comment omitted
            userData.email.toLowerCase(),  // … comment omitted
        );
    }

    /**
     * Generate unique user ID.
     * @returns {number} Generated user ID
     */
    #generateUserId() {
        // … comment omitted
        return Math.floor(Math.random() * 1000000);
    }

    // … comment omitted
    async #saveUser(user) {
        // … comment omitted
        this.logger?.info('Saving user', { id: user.id });

        // … comment omitted
        await new Promise(resolve => setTimeout(resolve, 100));

        return user;  // … comment omitted
    }

    #initialize() {
        // … comment omitted
    }
}

/**
 * Utility function with comprehensive documentation.
 *
 * @param {string} input The input string to process
 * @returns {string} Processed string result
 */
export function processString(input) {
    // … comment omitted
    if (!input || typeof input !== 'string') {
        return '';  // … comment omitted
    }

    // … comment omitted
    const trimmed = input.trim();
    const lowercase = trimmed.toLowerCase();
    const cleaned = lowercase.replace(/[^a-z0-9\s]/g, '');

    return cleaned;  // … comment omitted
}

// … comment omitted
function undocumentedHelper() {
    // … comment omitted
    const data = 'helper data';

    // … comment omitted
    console.log(data);  // … comment omitted
}

// … comment omitted
class ValidationError extends Error {
    constructor(errors) {  // … comment omitted
        super(`Validation failed: ${errors.join(', ')}`);
        this.errors = errors;
    }
}

// … comment omitted
export const DEFAULT_CONFIG = {
    timeout: 5000,    // … comment omitted
    retries: 3,       // … comment omitted
    baseUrl: 'http://localhost:3000'  // … comment omitted
};
