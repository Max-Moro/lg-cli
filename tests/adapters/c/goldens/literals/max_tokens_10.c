/**
 * C module for testing literal optimization.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Short string literal (should be preserved)
const char* SHORT_MESSAGE = "Hello, World!";

// Long string literal (candidate for trimming)
const char* LONG_MESSAGE = "This is an extremely long message that contains a…"; // literal string (−62 tokens)

// Multi-line string with formatting
const char* TEMPLATE_WITH_DATA =
    "User Information:\n"…"; // literal string (−62 tokens)

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
    "debug",
    (void*)1,
    "…",
}; // literal array (−-5 tokens)

static struct {
    const char* key;
    const void* value;
} large_config[] = {
    {"database.host", "localhost"},
}; // literal array (−318 tokens)

LiteralDataManager* literal_data_manager_new(void) {
    LiteralDataManager* manager = (LiteralDataManager*)malloc(sizeof(LiteralDataManager));
    if (!manager) return NULL;

    // Array with many elements (trimming candidate)
    static const char* languages[] = {
        "english",
        "spanish",
        "french",
        "…",
    }; // literal array (−84 tokens)
    manager->supported_languages = languages;
    manager->languages_count = sizeof(languages) / sizeof(languages[0]);

    // Array with many elements
    static char* extensions[] = {
        ".c",
        ".h",
        ".py",
        "…",
    }; // literal array (−58 tokens)
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
        "item_001",
        "item_002",
        "…",
    }; // literal array (−140 tokens)
    container->items = large_array;
    container->items_count = 30;

    return container;
}

const char* get_long_query(void) {
    // Very long SQL-like query string
    return
        "SELECT "
        "    users.id, users…"; // literal string (−206 tokens)
}

// Module-level constants with different sizes
struct {
    const char* API_VERSION;
    int DEFAULT_LIMIT;
} SMALL_CONSTANTS = {
    "v1",
    50,
    "…",
}; // literal array (−-4 tokens)

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
    100,
    101,
    200,
    201,
    202,
    "…",
}; // literal array (−104 tokens)

struct {
    const char* VALIDATION_FAILED;
    const char* AUTHENTICATION_REQUIRED;
    const char* AUTHORIZATION_FAILED;
    const char* RESOURCE_NOT_FOUND;
    const char* INTERNAL_ERROR;
    const char* RATE_LIMIT_EXCEEDED;
    const char* INVALID_REQUEST_FORMAT;
} ERROR_MESSAGES = {", "…"}; // literal array (−85 tokens)
