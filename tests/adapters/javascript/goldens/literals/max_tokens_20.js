/**
 * JavaScript module for testing literal optimization.
 */

// Short string literal (should be preserved)
const SHORT_MESSAGE = "Hello, World!";

// Long string literal (candidate for trimming)
const LONG_MESSAGE = `This is an extremely long message that contains a substantial amount of text content which might be conside…`; // literal string (−51 tokens)

// Multi-line template literal with embedded expressions
const TEMPLATE_WITH_DATA = `
User Information:
- Name: ${getUserName()}
- Email: ${getUserEmail()}
- Re…`; // literal string (−46 tokens)

export class LiteralDataManager {
    // Class properties with various literal types
    #smallConfig = {
        debug: true,
        version: "1.0.0"
    };

    #largeConfig = {
        "…": "…",
    }; // literal object (−235 tokens)

    constructor() {
        // Array with many elements (trimming candidate)
        this.supportedLanguages = [
            "english",
            "spanish",
            "french",
            "german",
            "…",
        ]; // literal array (−79 tokens)

        // Set with many elements
        this.allowedExtensions = new Set([
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".vue",
            "…",
        ]) // literal array (−38 tokens);
    }

    processData() {
        // Function with various literal data
        const smallArray = ["one", "two", "three"];

        const largeArray = [
            "item_001",
            "item_002",
            "item_003",
            "…",
        ]; // literal array (−134 tokens)

        const nestedData = {
            "…": "…",
        }; // literal object (−143 tokens)

        return {
            tags: smallArray,
            items: largeArray,
            "…": "…",
        }; // literal object (−14 tokens)
    }

    getLongQuery() {
        // Very long SQL-like query string
        return `
            SELECT
                users.id, users.username, users.email, users.created_at,…`; // literal string (−169 tokens)
    }
}

// Module-level constants with different sizes
export const SMALL_CONSTANTS = {
    API_VERSION: "v1",
    DEFAULT_LIMIT: 50
};

export const LARGE_CONSTANTS = {
    "…": "…",
}; // literal object (−450 tokens)

// Helper functions that use literal data
function getUserName() { return "John Doe"; }
function getUserEmail() { return "john.doe@example.com"; }
function getAccountStatus() { return "active"; }
function getPermissions() { return ["read", "write", "admin"]; }
function getLastLogin() { return "2024-01-15T10:30:00Z"; }
function getProfileCompleteness() { return 85; }
