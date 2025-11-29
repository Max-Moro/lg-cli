/**
 * C module for testing public API filtering.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

// Public module-level constants (should be preserved)
const char* PUBLIC_VERSION = "1.0.0";
const char* API_ENDPOINT = "https://api.example.com";

// Private module-level constants (should be filtered out)
static const char* PRIVATE_SECRET = "internal-use-only";
static struct {
    int debug;
    int verbose;
} INTERNAL_CONFIG = {1, 0};

// Public structure (should be preserved)
typedef struct {
    int id;
    char* name;
    char* email;
    time_t created_at;
} User;

// Private structure (should be filtered out)
typedef struct {
    long process_time;
    long memory_usage;
} InternalMetrics;

// Public enum (should be preserved)
typedef enum {
    ROLE_ADMIN,
    ROLE_USER,
    ROLE_GUEST
} UserRole;

// Private enum (should be filtered out)
typedef enum {
    EVENT_USER_CREATED,
    EVENT_USER_UPDATED,
    EVENT_CACHE_CLEARED
} InternalEventType;

// Public structure with mixed visibility members
typedef struct {
    // Public properties
    const char* version;
    int is_initialized;

    // Private properties (should be filtered out with public_api_only)
    void* internal_cache;
    InternalMetrics* metrics;

    // Private field
    char* api_endpoint;
} UserManager;

// Public functions (should be preserved)
UserManager* user_manager_new(const char* api_endpoint);
User* user_manager_create_user(UserManager* manager, const char* name, const char* email);
User* user_manager_get_user_by_id(UserManager* manager, int id);
User** user_manager_get_all_users(UserManager* manager, int* count);
void user_manager_free(UserManager* manager);

// Private functions (should be filtered out)
static void validate_user_data(const char* name, const char* email);
static int generate_id(void);
static int is_valid_email(const char* email);
static User* fetch_user_from_api(UserManager* manager, int id);
static void initialize(UserManager* manager);
static void log_error(const char* message, const char* error);

// Public static functions (should be preserved)
int user_manager_validate_user_role(const char* role);
User* user_manager_create_default_user(void);

// Private static functions (should be filtered out)
static char* format_internal_id(int id);

UserManager* user_manager_new(const char* api_endpoint) {
    UserManager* manager = (UserManager*)malloc(sizeof(UserManager));
    if (!manager) return NULL;

    manager->version = PUBLIC_VERSION;
    manager->is_initialized = 0;
    manager->internal_cache = NULL;
    manager->metrics = NULL;
    manager->api_endpoint = strdup(api_endpoint ? api_endpoint : API_ENDPOINT);

    initialize(manager);

    return manager;
}

User* user_manager_create_user(UserManager* manager, const char* name, const char* email) {
    if (!manager) return NULL;

    validate_user_data(name, email);

    User* user = (User*)malloc(sizeof(User));
    if (!user) return NULL;

    user->id = generate_id();
    user->name = strdup(name);
    user->email = strdup(email);
    user->created_at = time(NULL);

    return user;
}

User* user_manager_get_user_by_id(UserManager* manager, int id) {
    if (!manager) return NULL;

    // Check internal cache first
    // (would search cache here)

    return fetch_user_from_api(manager, id);
}

User** user_manager_get_all_users(UserManager* manager, int* count) {
    if (!manager || !count) {
        if (count) *count = 0;
        return NULL;
    }

    // Return all cached users
    *count = 0;
    return NULL;
}

void user_manager_free(UserManager* manager) {
    if (!manager) return;
    free(manager->api_endpoint);
    free(manager);
}

// Private function implementations (should be filtered out)
static void validate_user_data(const char* name, const char* email) {
    if (!name || strlen(name) == 0) {
        fprintf(stderr, "Name is required\n");
        exit(1);
    }

    if (!email || !is_valid_email(email)) {
        fprintf(stderr, "Invalid email format\n");
        exit(1);
    }
}

static int generate_id(void) {
    return rand() % 1000000;
}

static int is_valid_email(const char* email) {
    if (!email) return 0;
    const char* at = strchr(email, '@');
    if (!at) return 0;
    const char* dot = strchr(at, '.');
    return dot != NULL;
}

static User* fetch_user_from_api(UserManager* manager, int id) {
    if (!manager) return NULL;

    // Simulated API call
    fprintf(stderr, "Fetching user %d from API\n", id);

    return NULL;
}

static void initialize(UserManager* manager) {
    if (!manager) return;
    manager->is_initialized = 1;
}

static void log_error(const char* message, const char* error) {
    fprintf(stderr, "[UserManager] %s: %s\n", message, error);
}

// Public static function implementations
int user_manager_validate_user_role(const char* role) {
    if (!role) return 0;

    if (strcmp(role, "admin") == 0) return 1;
    if (strcmp(role, "user") == 0) return 1;
    if (strcmp(role, "guest") == 0) return 1;

    return 0;
}

User* user_manager_create_default_user(void) {
    User* user = (User*)malloc(sizeof(User));
    if (!user) return NULL;

    user->id = 0;
    user->name = strdup("Default User");
    user->email = strdup("default@example.com");
    user->created_at = time(NULL);

    return user;
}

// Private static function implementations (should be filtered out)
static char* format_internal_id(int id) {
    char* buffer = (char*)malloc(20);
    if (!buffer) return NULL;
    snprintf(buffer, 20, "internal_%06d", id);
    return buffer;
}

// Private structure (should be filtered out)
typedef struct {
    char** logs;
    int log_count;
    int log_capacity;
} InternalLogger;

static InternalLogger* internal_logger_new(void) {
    InternalLogger* logger = (InternalLogger*)malloc(sizeof(InternalLogger));
    if (!logger) return NULL;

    logger->log_capacity = 10;
    logger->logs = (char**)malloc(logger->log_capacity * sizeof(char*));
    logger->log_count = 0;

    return logger;
}

static void internal_logger_log(InternalLogger* logger, const char* message) {
    if (!logger || !message) return;

    if (logger->log_count >= logger->log_capacity) {
        logger->log_capacity *= 2;
        logger->logs = (char**)realloc(logger->logs,
                                      logger->log_capacity * sizeof(char*));
    }

    logger->logs[logger->log_count++] = strdup(message);
}

static void internal_logger_free(InternalLogger* logger) {
    if (!logger) return;

    for (int i = 0; i < logger->log_count; i++) {
        free(logger->logs[i]);
    }
    free(logger->logs);
    free(logger);
}

// Public utility structure (should be preserved)
typedef struct {
    char* (*format_user_name)(User* user);
    long (*get_user_age)(User* user);
} UserUtils;

char* format_user_name(User* user) {
    if (!user) return NULL;

    size_t len = strlen(user->name) + strlen(user->email) + 10;
    char* result = (char*)malloc(len);
    if (!result) return NULL;

    snprintf(result, len, "%s (%s)", user->name, user->email);
    return result;
}

long get_user_age(User* user) {
    if (!user) return 0;

    time_t now = time(NULL);
    return (now - user->created_at) / (60 * 60 * 24);
}

// Private utility functions (should be filtered out)
static void debug_log(const char* message) {
    if (INTERNAL_CONFIG.debug) {
        fprintf(stderr, "[Debug] %s\n", message);
    }
}

static void measure_performance(void (*fn)(void)) {
    if (!fn) return;

    clock_t start = clock();
    fn();
    clock_t end = clock();

    double elapsed = ((double)(end - start)) / CLOCKS_PER_SEC * 1000;
    printf("Performance: %.2fms\n", elapsed);
}
