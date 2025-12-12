/**
 * TypeScript module for testing literal optimization.
 */

// Short string literal (should be preserved)
const SHORT_MESSAGE = "Hello, World!";

// Long string literal (candidate for trimming)
const LONG_MESSAGE = `This is an extremely long message that contains a substantial amount of text content which might be conside…`; // literal string (−54 tokens)

// Multi-line template literal with embedded expressions
const TEMPLATE_WITH_DATA = `
User Information:
- Name: ${getUserName()}
- Email: ${getUserEmail()}
- Re…`; // literal string (−48 tokens)

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
        database: {
            host: "localhost",
            port: 5432,
            // … (4 more, −70 tokens)
        },
        // … (3 more, −215 tokens)
    };
    
    constructor() {
        // Array with many elements (trimming candidate)
        this.supportedLanguages = [
            "english",
            "spanish",
            "french",
            "…",
        ]; // literal array (−82 tokens)
        
        // Set with many elements
        this.allowedExtensions = new Set([
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            "…",
        ]); // literal array (−47 tokens)
    }
    
    public processData(): DataContainer {
        // Function with various literal data
        const smallArray = ["one", "two", "three"];
        
        const largeArray = [
            "item_001",
            "item_002",
            "…",
        ]; // literal array (−140 tokens)
        
        const nestedData = {
            level1: {
                level2: {
                    level3: {
                        data: [
                            { id: 1, name: "First", active: true },
                            // … (4 more, −61 tokens)
                        ],
                        // … (1 more, −102 tokens)
                    },
                },
            },
        };
        
        return {
            tags: smallArray,
            items: largeArray,
            // … (2 more, −18 tokens)
        };
    }
    
    public getLongQuery(): string {
        // Very long SQL-like query string
        return `
            SELECT 
                users.id, users.username, users.email, users.created_at,…`; // literal string (−171 tokens)
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
    HTTP_STATUS_CODES: {
        CONTINUE: 100,
        // … (40 more, −241 tokens)
    },
    // … (1 more, −363 tokens)
};

// Helper functions that use literal data
function getUserName(): string { return "John Doe"; }
function getUserEmail(): string { return "john.doe@example.com"; }
function getAccountStatus(): string { return "active"; }
function getPermissions(): string[] { return ["read", "write", "admin"]; }
function getLastLogin(): string { const date = "2024-01-15T10:30:00Z"; return date; }
function getProfileCompleteness(): number { return 85; }
