/** … docstring omitted (6 lines) */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// … comment omitted
#define MODULE_VERSION "1.0.0"  // TODO: Move to config file

/** … docstring omitted (4 lines) */
typedef struct {
    int id;           // … comment omitted
    char* name;       // … comment omitted
    char* email;      // … comment omitted
    // … comment omitted
    void* profile;
} User;

typedef struct {
    char* bio;
    char* avatar;
} Profile;

typedef struct {
    void* config;     // … comment omitted
    void* logger;     // … comment omitted
} CommentedService;

/** … docstring omitted (10 lines) */
CommentedService* commented_service_new(void* config, void* logger) {
    CommentedService* service = (CommentedService*)malloc(sizeof(CommentedService));
    if (!service) return NULL;

    service->config = config;
    service->logger = logger;

    // … comment omitted

    return service;
}

/** … docstring omitted (10 lines) */
User* process_user(User* userData) {
    // … comment omitted
    if (!userData) {
        fprintf(stderr, "User data is required\n");
        return NULL;
    }

    // … comment omitted (5 lines)
    int is_valid = 1;
    if (!userData->name || strlen(userData->name) == 0) {
        // … comment omitted
        fprintf(stderr, "Validation failed: name is required\n");
        is_valid = 0;
    }

    if (!userData->email || strlen(userData->email) == 0) {
        fprintf(stderr, "Validation failed: email is required\n");
        is_valid = 0;
    }

    if (!is_valid) {
        return NULL;
    }

    // … comment omitted
    User* transformed = transform_user_data(userData);

    // … comment omitted
    User* saved = save_user(transformed);

    return saved;  // … comment omitted
}

static User* transform_user_data(User* userData) {
    // … comment omitted (5 lines)
    User* user = (User*)malloc(sizeof(User));
    if (!user) return NULL;

    user->id = generate_user_id();      // … comment omitted
    user->name = strdup(userData->name); // … comment omitted
    user->email = strdup(userData->email); // … comment omitted
    user->profile = userData->profile ? userData->profile : NULL;

    return user;
}

/** … docstring omitted (4 lines) */
static int generate_user_id(void) {
    // … comment omitted
    return rand() % 1000000;
}

// … comment omitted
static User* save_user(User* user) {
    // … comment omitted
    if (user) {
        printf("Saving user: %d\n", user->id);
    }

    // … comment omitted

    return user;  // … comment omitted
}

/** … docstring omitted (6 lines) */
char* process_string(const char* input) {
    // … comment omitted
    if (!input || strlen(input) == 0) {
        return strdup("");  // … comment omitted
    }

    // … comment omitted (5 lines)
    size_t len = strlen(input);
    char* result = (char*)malloc(len + 1);
    if (!result) return NULL;

    // … comment omitted
    strcpy(result, input);

    return result;  // … comment omitted
}

// … comment omitted
static void undocumented_helper(void) {
    // … comment omitted
    const char* data = "helper data";

    // … comment omitted
    printf("%s\n", data);  // … comment omitted
}

// … comment omitted
typedef struct {
    int is_valid;      // … comment omitted
    char** errors;     // … comment omitted
    int error_count;   // … comment omitted
} ValidationResult;

typedef struct {
    int timeout;       // … comment omitted
    int retries;       // … comment omitted
    char* base_url;    // … comment omitted
} ServiceConfig;

// … comment omitted (4 lines)
ServiceConfig DEFAULT_CONFIG = {
    5000,              // … comment omitted
    3,                 // … comment omitted
    "http://localhost:3000"  // … comment omitted
};
