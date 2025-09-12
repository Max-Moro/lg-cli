/**
 * TypeScript module for testing literal optimization.
 */

// Short string literal (should be preserved)
const SHORT_MESSAGE = "Hello, World!";

// Long string literal (candidate for trimming)
const LONG_MESSAGE = `This is an extremely long message that contains a substantial amount of text content which might be considered for trimming when optimizing TypeScript code for AI context windows. The message continues with detailed explanations and verbose descriptions that may not be essential for understanding the core functionality and structure of the code. This template literal spans multiple conceptual lines even though it's defined as a single string literal.`;

// Multi-line template literal with embedded expressions
const TEMPLATE_WITH_DATA = `
User Information:
- Name: ${getUserName()}
- Email: ${getUserEmail()}
- Registration Date: ${new Date().toISOString()}
- Account Status: ${getAccountStatus()}
- Permissions: ${JSON.stringify(getPermissions())}
- Last Login: ${getLastLogin()}
- Profile Completeness: ${getProfileCompleteness()}%
`;

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
            name: "application_db",
            ssl: false,
            pool: {
                min: 2,
                max: 10,
                idleTimeoutMillis: 30000,
                connectionTimeoutMillis: 2000
            },
            retry: {
                attempts: 3,
                delay: 1000,
                backoff: "exponential"
            }
        },
        cache: {
            redis: {
                host: "localhost",
                port: 6379,
                db: 0,
                ttl: 3600
            },
            memory: {
                maxSize: 1000,
                ttl: 1800
            }
        },
        api: {
            baseUrl: "https://api.example.com",
            timeout: 30000,
            retries: 3,
            rateLimit: {
                requests: 100,
                window: 60000
            }
        },
        features: {
            authentication: true,
            authorization: true,
            logging: true,
            monitoring: true,
            analytics: false,
            caching: true,
            compression: true
        }
    };
    
    constructor() {
        // Array with many elements (trimming candidate)
        this.supportedLanguages = [
            "english", "spanish", "french", "german", "italian", "portuguese",
            "russian", "chinese", "japanese", "korean", "arabic", "hindi",
            "dutch", "swedish", "norwegian", "danish", "finnish", "polish",
            "czech", "hungarian", "romanian", "bulgarian", "croatian", "serbian"
        ];
        
        // Set with many elements
        this.allowedExtensions = new Set([
            ".js", ".ts", ".jsx", ".tsx", ".vue", ".svelte",
            ".py", ".java", ".c", ".cpp", ".cs", ".go", ".rs",
            ".php", ".rb", ".swift", ".kt", ".scala", ".clj"
        ]);
    }
    
    public processData(): DataContainer {
        // Function with various literal data
        const smallArray = ["one", "two", "three"];
        
        const largeArray = [
            "item_001", "item_002", "item_003", "item_004", "item_005",
            "item_006", "item_007", "item_008", "item_009", "item_010",
            "item_011", "item_012", "item_013", "item_014", "item_015",
            "item_016", "item_017", "item_018", "item_019", "item_020",
            "item_021", "item_022", "item_023", "item_024", "item_025",
            "item_026", "item_027", "item_028", "item_029", "item_030"
        ];
        
        const nestedData = {
            level1: {
                level2: {
                    level3: {
                        data: [
                            { id: 1, name: "First", active: true },
                            { id: 2, name: "Second", active: false },
                            { id: 3, name: "Third", active: true },
                            { id: 4, name: "Fourth", active: true },
                            { id: 5, name: "Fifth", active: false }
                        ],
                        metadata: {
                            created: "2024-01-01",
                            updated: "2024-01-15",
                            version: 3,
                            checksum: "abcdef123456"
                        }
                    }
                }
            }
        };
        
        return {
            tags: smallArray,
            items: largeArray,
            metadata: { type: "test", count: smallArray.length },
            configuration: nestedData
        };
    }
    
    public getLongQuery(): string {
        // Very long SQL-like query string
        return `
            SELECT 
                users.id, users.username, users.email, users.created_at,
                profiles.first_name, profiles.last_name, profiles.bio, profiles.avatar_url,
                addresses.street, addresses.city, addresses.state, addresses.postal_code, addresses.country,
                subscriptions.plan_name, subscriptions.status, subscriptions.expires_at,
                payments.amount, payments.currency, payments.payment_date, payments.method
            FROM users 
            LEFT JOIN profiles ON users.id = profiles.user_id 
            LEFT JOIN addresses ON users.id = addresses.user_id 
            LEFT JOIN subscriptions ON users.id = subscriptions.user_id 
            LEFT JOIN payments ON users.id = payments.user_id 
            WHERE users.is_active = true 
                AND users.email_verified = true 
                AND profiles.is_public = true 
                AND subscriptions.status IN ('active', 'trial') 
            ORDER BY users.created_at DESC, subscriptions.expires_at ASC 
            LIMIT 100 OFFSET 0
        `;
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
        SWITCHING_PROTOCOLS: 101,
        OK: 200,
        CREATED: 201,
        ACCEPTED: 202,
        NON_AUTHORITATIVE_INFORMATION: 203,
        NO_CONTENT: 204,
        RESET_CONTENT: 205,
        PARTIAL_CONTENT: 206,
        MULTIPLE_CHOICES: 300,
        MOVED_PERMANENTLY: 301,
        FOUND: 302,
        SEE_OTHER: 303,
        NOT_MODIFIED: 304,
        USE_PROXY: 305,
        TEMPORARY_REDIRECT: 307,
        PERMANENT_REDIRECT: 308,
        BAD_REQUEST: 400,
        UNAUTHORIZED: 401,
        PAYMENT_REQUIRED: 402,
        FORBIDDEN: 403,
        NOT_FOUND: 404,
        METHOD_NOT_ALLOWED: 405,
        NOT_ACCEPTABLE: 406,
        PROXY_AUTHENTICATION_REQUIRED: 407,
        REQUEST_TIMEOUT: 408,
        CONFLICT: 409,
        GONE: 410,
        LENGTH_REQUIRED: 411,
        PRECONDITION_FAILED: 412,
        PAYLOAD_TOO_LARGE: 413,
        URI_TOO_LONG: 414,
        UNSUPPORTED_MEDIA_TYPE: 415,
        RANGE_NOT_SATISFIABLE: 416,
        EXPECTATION_FAILED: 417,
        INTERNAL_SERVER_ERROR: 500,
        NOT_IMPLEMENTED: 501,
        BAD_GATEWAY: 502,
        SERVICE_UNAVAILABLE: 503,
        GATEWAY_TIMEOUT: 504,
        HTTP_VERSION_NOT_SUPPORTED: 505
    },
    ERROR_MESSAGES: {
        VALIDATION_FAILED: "Input validation failed. Please check your data and try again.",
        AUTHENTICATION_REQUIRED: "Authentication is required to access this resource.",
        AUTHORIZATION_FAILED: "You do not have permission to perform this action.",
        RESOURCE_NOT_FOUND: "The requested resource could not be found on the server.",
        INTERNAL_ERROR: "An internal server error occurred. Please try again later.",
        RATE_LIMIT_EXCEEDED: "Rate limit exceeded. Please wait before making another request.",
        INVALID_REQUEST_FORMAT: "The request format is invalid. Please check the documentation."
    }
};

// Helper functions that use literal data
function getUserName(): string { return "John Doe"; }
function getUserEmail(): string { return "john.doe@example.com"; }
function getAccountStatus(): string { return "active"; }
function getPermissions(): string[] { return ["read", "write", "admin"]; }
function getLastLogin(): string { date = "2024-01-15T10:30:00Z"; return date; }
function getProfileCompleteness(): number { return 85; }
