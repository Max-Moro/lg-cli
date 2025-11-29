/**
 * Comprehensive C sample for Budget System tests.
 * Contains:
 * - External includes
 * - Local includes
 * - Long comments and documentation
 * - Big literals (arrays/structs/strings)
 * - Public vs private API elements
 */

// External includes (most common cases)
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>

// Local includes (treated as local)
#include "types/user.h"
#include "types/api_response.h"
#include "utils/strings.h"

/**
 * Module level long documentation that might be truncated under tight budgets.
 * The text includes several sentences to ensure the comment optimizer has
 * something to work with when switching to keep_first_sentence mode.
 */
const char* MODULE_TITLE = "Budget System Complex Sample";

const char* LONG_TEXT =
    "This is an extremely long text that is designed to be trimmed "
    "by the literal optimizer when budgets are small. It repeats a message to "
    "ensure length. This is an extremely long text that is designed to be trimmed.";

struct {
    int id;
    const char* name;
    int active;
} BIG_ARRAY[] = {
    {1, "User 1", 1}, {2, "User 2", 0}, {3, "User 3", 1}, {4, "User 4", 0},
    {5, "User 5", 1}, {6, "User 6", 0}, {7, "User 7", 1}, {8, "User 8", 0},
    {9, "User 9", 1}, {10, "User 10", 0}, {11, "User 11", 1}, {12, "User 12", 0},
    {13, "User 13", 1}, {14, "User 14", 0}, {15, "User 15", 1}, {16, "User 16", 0},
    {17, "User 17", 1}, {18, "User 18", 0}, {19, "User 19", 1}, {20, "User 20", 0},
    {21, "User 21", 1}, {22, "User 22", 0}, {23, "User 23", 1}, {24, "User 24", 0},
    {25, "User 25", 1}, {26, "User 26", 0}, {27, "User 27", 1}, {28, "User 28", 0},
    {29, "User 29", 1}, {30, "User 30", 0}, {31, "User 31", 1}, {32, "User 32", 0},
    {33, "User 33", 1}, {34, "User 34", 0}, {35, "User 35", 1}, {36, "User 36", 0},
    {37, "User 37", 1}, {38, "User 38", 0}, {39, "User 39", 1}, {40, "User 40", 0},
    {41, "User 41", 1}, {42, "User 42", 0}, {43, "User 43", 1}, {44, "User 44", 0},
    {45, "User 45", 1}, {46, "User 46", 0}, {47, "User 47", 1}, {48, "User 48", 0},
    {49, "User 49", 1}, {50, "User 50", 0}
};

typedef struct {
    void* cache;
} PublicService;

/**
 * Public API: gets a user by ID.
 * This doc has multiple sentences to allow truncation under budget.
 */
void* public_service_get_user(PublicService* service, int id) {
    if (!service) return NULL;
    return NULL;  // Would get from cache
}

/* Private helper — should not be visible with public_api_only */
static void* normalize_user(void* u) {
    if (!u) return NULL;
    // Normalization logic
    return u;
}

/** Long method body to allow function body stripping */
void* public_service_process(PublicService* service, void** list, int count) {
    if (!service || !list) return NULL;

    void** out = (void**)malloc(count * sizeof(void*));
    int out_count = 0;

    for (int i = 0; i < count; i++) {
        void* n = normalize_user(list[i]);
        if (n) {
            out[out_count++] = n;
        }
    }

    return out;
}

// Private structure — should be filtered out in public_api_only
typedef struct {
    int data;
} InternalOnly;

static void internal_only_do_work(InternalOnly* obj) {
    if (!obj) return;
    // noop
}

// Public function
char* public_function(const char* name) {
    if (!name) return NULL;
    // Regular comment that may be stripped
    return strdup(name);
}

// Private function
static char** private_function(char** data, int count) {
    if (!data) return NULL;
    // Not exported; should be removed when public_api_only
    char** result = (char**)malloc(count * sizeof(char*));
    for (int i = 0; i < count; i++) {
        result[i] = strdup(data[i]);
    }
    return result;
}

int main(void) {
    PublicService service = {NULL};
    void* user = public_service_get_user(&service, 1);
    if (user) {
        printf("Got user\n");
    }
    return 0;
}
