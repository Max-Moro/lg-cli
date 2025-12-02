/**
 * JavaScript module for testing literal optimization.
 */

// Short string literal (should be preserved)
const SHORT_MESSAGE = "Hello, World!";

// Long string literal (candidate for trimming)
const LONG_MESSAGE = `This is an extremely long message that conta…`; // literal string (−62 tokens)

// Multi-line template literal with embedded expressions
const TEMPLATE_WITH_DATA = `
User Information:
- Name: ${g…`; // literal string (−57 tokens)

export class LiteralDataManager {
    // Class properties with various literal types
    #smallConfig = {
        debug: true,
        "…": "…",
    }; // literal object (−3 tokens)

    #largeConfig = {
        "…": "…",
    }; // literal object (−235 tokens)

    constructor() {
        // Array with many elements (trimming candidate)
        this.supportedLanguages = [
            "english",
            "spanish",
            "french",
            "…",
        ]; // literal array (−84 tokens)

        // Set with many elements
        this.allowedExtensions = new Set([
            ".js",
            ".jsx",
            ".ts",
            "…",
        ]) // literal array (−46 tokens);
    }

    processData() {
        // Function with various literal data
        const smallArray = ["one", "two", "three"];

        const largeArray = [
            "item_001",
            "item_002",
            "…",
        ]; // literal array (−140 tokens)

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
                use…`; // literal string (−180 tokens)
    }
}

// Module-level constants with different sizes
export const SMALL_CONSTANTS = {
    API_VERSION: "v1",
    "…": "…",
}; // literal object (−0 tokens)

export const LARGE_CONSTANTS = {
    "…": "…",
}; // literal object (−450 tokens)

// Helper functions that use literal data
function getUserName() { return "John Doe"; }
function getUserEmail() { return "john.doe@example.com"; }
function getAccountStatus() { return "active"; }
function getPermissions() { return ["read", "write", "admin"]; }
function getLastLogin() { return "2024-01-15T1…"; /* literal string (−5 tokens) */ }
function getProfileCompleteness() { return 85; }
