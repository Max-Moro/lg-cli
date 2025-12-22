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
// … 2 variables omitted (5 lines)

// Public structure (should be preserved)
typedef struct {
    int id;
    char* name;
    char* email;
    time_t created_at;
} User;

// Private structure (should be filtered out)
// … typedef omitted (4 lines)

// Public enum (should be preserved)
typedef enum {
    ROLE_ADMIN,
    ROLE_USER,
    ROLE_GUEST
} UserRole;

// Private enum (should be filtered out)
// … typedef omitted (5 lines)

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
// … 6 variables omitted

// Public static functions (should be preserved)
int user_manager_validate_user_role(const char* role);
User* user_manager_create_default_user(void);

// Private static functions (should be filtered out)
// … variable omitted

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
// … 6 functions omitted (33 lines)

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
// … function omitted (6 lines)

// Private structure (should be filtered out)
// … typedef omitted (5 lines)

// … 3 functions omitted (25 lines)

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
// … 2 functions omitted (13 lines)
