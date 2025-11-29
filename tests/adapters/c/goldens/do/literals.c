/**
 * C module for testing literal optimization.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Short string literal (should be preserved)
const char* SHORT_MESSAGE = "Hello, World!";

// Long string literal (candidate for trimming)
const char* LONG_MESSAGE = "This is an extremely long message that contains a substantial amount of text content which might be considered for trimming when optimizing C code for AI context windows. The message continues with detailed explanations and verbose descriptions that may not be essential for understanding the core functionality and structure of the code. This string literal spans multiple conceptual lines even though it's defined as a single string literal.";

// Multi-line string with formatting
const char* TEMPLATE_WITH_DATA =
    "User Information:\n"
    "- Name: %s\n"
    "- Email: %s\n"
    "- Registration Date: %s\n"
    "- Account Status: %s\n"
    "- Permissions: %s\n"
    "- Last Login: %s\n"
    "- Profile Completeness: %d%%\n";

typedef struct {
    // Small array (should be preserved)
    char** tags;
    int tags_count;

    // Large array (candidate for trimming)
    char** items;
    int items_count;

    // Small object (should be preserved)
    void* metadata;

    // Large object (candidate for trimming)
    void* configuration;
} DataContainer;

typedef struct {
    const char** supported_languages;
    int languages_count;
    char** allowed_extensions;
    int extensions_count;
} LiteralDataManager;

static const void* small_config[2] = {
    "debug", (void*)1,
};

static struct {
    const char* key;
    const void* value;
} large_config[] = {
    {"database.host", "localhost"},
    {"database.port", (void*)5432},
    {"database.name", "application_db"},
    {"database.ssl", (void*)0},
    {"database.pool.min", (void*)2},
    {"database.pool.max", (void*)10},
    {"database.pool.idle_timeout", (void*)30000},
    {"database.pool.connection_timeout", (void*)2000},
    {"database.retry.attempts", (void*)3},
    {"database.retry.delay", (void*)1000},
    {"database.retry.backoff", "exponential"},
    {"cache.redis.host", "localhost"},
    {"cache.redis.port", (void*)6379},
    {"cache.redis.db", (void*)0},
    {"cache.redis.ttl", (void*)3600},
    {"cache.memory.max_size", (void*)1000},
    {"cache.memory.ttl", (void*)1800},
    {"api.base_url", "https://api.example.com"},
    {"api.timeout", (void*)30000},
    {"api.retries", (void*)3},
    {"api.rate_limit.requests", (void*)100},
    {"api.rate_limit.window", (void*)60000},
    {"features.authentication", (void*)1},
    {"features.authorization", (void*)1},
    {"features.logging", (void*)1},
    {"features.monitoring", (void*)1},
    {"features.analytics", (void*)0},
    {"features.caching", (void*)1},
    {"features.compression", (void*)1},
};

LiteralDataManager* literal_data_manager_new(void) {
    LiteralDataManager* manager = (LiteralDataManager*)malloc(sizeof(LiteralDataManager));
    if (!manager) return NULL;

    // Array with many elements (trimming candidate)
    static const char* languages[] = {
        "english", "spanish", "french", "german", "italian", "portuguese",
        "russian", "chinese", "japanese", "korean", "arabic", "hindi",
        "dutch", "swedish", "norwegian", "danish", "finnish", "polish",
        "czech", "hungarian", "romanian", "bulgarian", "croatian", "serbian"
    };
    manager->supported_languages = languages;
    manager->languages_count = sizeof(languages) / sizeof(languages[0]);

    // Array with many elements
    static char* extensions[] = {
        ".c", ".h",
        ".py", ".js", ".ts", ".jsx", ".tsx",
        ".java", ".kt", ".scala",
        ".cpp", ".cxx", ".cc", ".hpp", ".hxx",
        ".cs", ".go", ".rs",
        ".php", ".rb", ".swift", ".clj"
    };
    manager->allowed_extensions = extensions;
    manager->extensions_count = sizeof(extensions) / sizeof(extensions[0]);

    return manager;
}

DataContainer* process_data(void) {
    DataContainer* container = (DataContainer*)malloc(sizeof(DataContainer));
    if (!container) return NULL;

    // Small array
    static char* small_array[] = {"one", "two", "three"};
    container->tags = small_array;
    container->tags_count = 3;

    // Large array
    static char* large_array[] = {
        "item_001", "item_002", "item_003", "item_004", "item_005",
        "item_006", "item_007", "item_008", "item_009", "item_010",
        "item_011", "item_012", "item_013", "item_014", "item_015",
        "item_016", "item_017", "item_018", "item_019", "item_020",
        "item_021", "item_022", "item_023", "item_024", "item_025",
        "item_026", "item_027", "item_028", "item_029", "item_030"
    };
    container->items = large_array;
    container->items_count = 30;

    return container;
}

const char* get_long_query(void) {
    // Very long SQL-like query string
    return
        "SELECT "
        "    users.id, users.username, users.email, users.created_at, "
        "    profiles.first_name, profiles.last_name, profiles.bio, profiles.avatar_url, "
        "    addresses.street, addresses.city, addresses.state, addresses.postal_code, addresses.country, "
        "    subscriptions.plan_name, subscriptions.status, subscriptions.expires_at, "
        "    payments.amount, payments.currency, payments.payment_date, payments.method "
        "FROM users "
        "LEFT JOIN profiles ON users.id = profiles.user_id "
        "LEFT JOIN addresses ON users.id = addresses.user_id "
        "LEFT JOIN subscriptions ON users.id = subscriptions.user_id "
        "LEFT JOIN payments ON users.id = payments.user_id "
        "WHERE users.is_active = 1 "
        "    AND users.email_verified = 1 "
        "    AND profiles.is_public = 1 "
        "    AND subscriptions.status IN ('active', 'trial') "
        "ORDER BY users.created_at DESC, subscriptions.expires_at ASC "
        "LIMIT 100 OFFSET 0";
}

// Module-level constants with different sizes
struct {
    const char* API_VERSION;
    int DEFAULT_LIMIT;
} SMALL_CONSTANTS = {
    "v1",
    50
};

struct {
    int CONTINUE;
    int SWITCHING_PROTOCOLS;
    int OK;
    int CREATED;
    int ACCEPTED;
    int NON_AUTHORITATIVE_INFORMATION;
    int NO_CONTENT;
    int RESET_CONTENT;
    int PARTIAL_CONTENT;
    int MULTIPLE_CHOICES;
    int MOVED_PERMANENTLY;
    int FOUND;
    int SEE_OTHER;
    int NOT_MODIFIED;
    int USE_PROXY;
    int TEMPORARY_REDIRECT;
    int PERMANENT_REDIRECT;
    int BAD_REQUEST;
    int UNAUTHORIZED;
    int PAYMENT_REQUIRED;
    int FORBIDDEN;
    int NOT_FOUND;
    int METHOD_NOT_ALLOWED;
    int NOT_ACCEPTABLE;
    int PROXY_AUTHENTICATION_REQUIRED;
    int REQUEST_TIMEOUT;
    int CONFLICT;
    int GONE;
    int LENGTH_REQUIRED;
    int PRECONDITION_FAILED;
    int PAYLOAD_TOO_LARGE;
    int URI_TOO_LONG;
    int UNSUPPORTED_MEDIA_TYPE;
    int RANGE_NOT_SATISFIABLE;
    int EXPECTATION_FAILED;
    int INTERNAL_SERVER_ERROR;
    int NOT_IMPLEMENTED;
    int BAD_GATEWAY;
    int SERVICE_UNAVAILABLE;
    int GATEWAY_TIMEOUT;
    int HTTP_VERSION_NOT_SUPPORTED;
} HTTP_STATUS_CODES = {
    100, 101, 200, 201, 202, 203, 204, 205, 206,
    300, 301, 302, 303, 304, 305, 307, 308,
    400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410,
    411, 412, 413, 414, 415, 416, 417,
    500, 501, 502, 503, 504, 505
};

struct {
    const char* VALIDATION_FAILED;
    const char* AUTHENTICATION_REQUIRED;
    const char* AUTHORIZATION_FAILED;
    const char* RESOURCE_NOT_FOUND;
    const char* INTERNAL_ERROR;
    const char* RATE_LIMIT_EXCEEDED;
    const char* INVALID_REQUEST_FORMAT;
} ERROR_MESSAGES = {
    "Input validation failed. Please check your data and try again.",
    "Authentication is required to access this resource.",
    "You do not have permission to perform this action.",
    "The requested resource could not be found on the server.",
    "An internal server error occurred. Please try again later.",
    "Rate limit exceeded. Please wait before making another request.",
    "The request format is invalid. Please check the documentation."
};
