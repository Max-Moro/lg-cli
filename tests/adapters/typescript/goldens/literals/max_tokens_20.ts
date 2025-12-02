/**
 * TypeScript module for testing literal optimization.
 */

// Short string literal (should be preserved)
const SHORT_MESSAGE = "Hello, World!";

// Long string literal (candidate for trimming)
const LONG_MESSAGE = `This is an extremely long message that contains a substantial amount of text content which might be considered for trim…`; // literal string (−50 tokens)

// Multi-line template literal with embedded expressions
const TEMPLATE_WITH_DATA = `
User Information:
- Name: ${getUserName()}
- Email: ${getUserEmail()}
- Registrati…`; // literal string (−45 tokens)

interface DataContainer {
    // Small array (should be preserved)
    tags: string[];
    
    // Large array (candidate for trimming)
    items: string[];
    
    // Small object (should be preserved)
    metadata: { [key: string]: any };
    
    // Large object (candidate for trimming)
    configuration: { [key: string]: any };
}

export class LiteralDataManager {
    // Class properties with various literal types
    private readonly smallConfig = {
        debug: true,
        version: "1.0.0"
    };
    
    private readonly largeConfig = {
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
            ".ts",
            ".jsx",
            ".tsx",
            ".vue",
            "…",
        ]) // literal array (−38 tokens);
    }
    
    public processData(): DataContainer {
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
    
    public getLongQuery(): string {
        // Very long SQL-like query string
        return `
            SELECT 
                users.id, users.username, users.email, users.created_at,…`; // literal string (−170 tokens)
    }
    
    // Properties with literal data
    private readonly supportedLanguages: string[];
    private readonly allowedExtensions: Set<string>;
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
function getUserName(): string { return "John Doe"; }
function getUserEmail(): string { return "john.doe@example.com"; }
function getAccountStatus(): string { return "active"; }
function getPermissions(): string[] { return ["read", "write", "admin"]; }
function getLastLogin(): string { const date = "2024-01-15T10:30:00Z"; return date; }
function getProfileCompleteness(): number { return 85; }
