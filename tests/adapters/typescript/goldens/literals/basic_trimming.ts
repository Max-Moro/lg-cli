/**
 * TypeScript module for testing literal optimization.
 */

// Short string literal (should be preserved)
const SHORT_MESSAGE = "Hello, World!";

// Long string literal (candidate for trimming)
const LONG_MESSAGE = `This is an extremely long message...` // … literal string (−64 tokens);

// Multi-line template literal with embedded expressions
const TEMPLATE_WITH_DATA = `
User Information:
- Name:...` // … literal string (−59 tokens);

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
        debug: true...} // … literal object (−11 tokens);
    
    private readonly largeConfig = {
        database: {...} // … literal object (−239 tokens);
    
    constructor() {
        // Array with many elements (trimming candidate)
        this.supportedLanguages = [
            "english", "spanish...] // … literal array (−96 tokens);
        
        // Set with many elements
        this.allowedExtensions = new Set([
            ".js", ".ts"...] // … literal array (−56 tokens));
    }
    
    public processData(): DataContainer {
        // Function with various literal data
        const smallArray = ["one", "two", "three"];
        
        const largeArray = [
            "item_001", ...] // … literal array (−151 tokens);
        
        const nestedData = {
            level1:...} // … literal object (−146 tokens);
        
        return {
            tags: smallArray...} // … literal object (−28 tokens);
    }
    
    public getLongQuery(): string {
        // Very long SQL-like query string
        return `
            SELECT...` // … literal string (−184 tokens);
    }
    
    // Properties with literal data
    private readonly supportedLanguages: string[];
    private readonly allowedExtensions: Set<string>;
}

// Module-level constants with different sizes
export const SMALL_CONSTANTS = {
    API_VERSION:...} // … literal object (−10 tokens);

export const LARGE_CONSTANTS = {
    HTTP_STATUS_CODES:...} // … literal object (−451 tokens);

// Helper functions that use literal data
function getUserName(): string { return "John Doe"; }
function getUserEmail(): string { return "john.doe@example.com"; }
function getAccountStatus(): string { return "active"; }
function getPermissions(): string[] { return ["read", "write", "admin"]; }
function getLastLogin(): string { return "2024-01-15T10..." // … literal string (−5 tokens); }
function getProfileCompleteness(): number { return 85; }
