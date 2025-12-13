/**
 * JavaScript module for testing literal optimization.
 */

// Short string literal (should be preserved)
const SHORT_MESSAGE = "Hello, World!";

// Long string literal (candidate for trimming)
const LONG_MESSAGE = `This is an extremely long message that conta…`; // literal string (−65 tokens)

// Multi-line template literal with embedded expressions
const TEMPLATE_WITH_DATA = `
User Information:
- Name: ${getUserName()}…`; // literal string (−57 tokens)

export class LiteralDataManager {
    // Class properties with various literal types
    #smallConfig = {
        debug: true,
        version: "1.0.0"
    };

    #largeConfig = {
        database: {
            host: "localhost",
            // … (5 more, −75 tokens)
        },
        // … (3 more, −145 tokens)
    };

    constructor() {
        // Array with many elements (trimming candidate)
        this.supportedLanguages = [
            "english",
            "…",
        ]; // literal array (−89 tokens)

        // Set with many elements
        this.allowedExtensions = new Set([
            ".js",
            "…",
        ]); // literal array (−56 tokens)
    }

    processData() {
        // Function with various literal data
        const smallArray = ["one", "two", "three"];

        const largeArray = [
            "item_001",
            "…",
        ]; // literal array (−145 tokens)

        const nestedData = {
            level1: {
                level2: {
                    level3: {
                        data: [
                            { id: 1, name: "First", active: true },
                            "…",
                        ] // literal array (−61 tokens),
                        // … (1 more, −41 tokens)
                    }
                }
            }
        };

        return {
            tags: smallArray,
            // … (3 more, −22 tokens)
        };
    }

    getLongQuery() {
        // Very long SQL-like query string
        return `
            SELECT
                use…`; // literal string (−182 tokens)
    }
}

// Module-level constants with different sizes
export const SMALL_CONSTANTS = {
    API_VERSION: "v1",
    DEFAULT_LIMIT: 50
};

export const LARGE_CONSTANTS = {
    HTTP_STATUS_CODES: {
        CONTINUE: 100,
        // … (40 more, −241 tokens)
    },
    // … (1 more, −122 tokens)
};

// Helper functions that use literal data
function getUserName() { return "John Doe"; }
function getUserEmail() { return "john.doe@example.com"; }
function getAccountStatus() { return "active"; }
function getPermissions() { return ["read", "write", "admin"]; }
function getLastLogin() { return "2024-01-15T1…"; /* literal string (−7 tokens) */ }
function getProfileCompleteness() { return 85; }
