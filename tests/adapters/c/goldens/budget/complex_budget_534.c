/**
 * Comprehensive C sample for Budget System tests.
 * Contains:
 * - External includes
 * - Local includes
 * - Long comments and documentation
 * - Big literals (arrays/structs/strings)
 * - Public vs private API elements
 */

// … 5 imports omitted (6 lines)

// … comment omitted
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
    "by the literal optimizer when budgets are small. It repeats a message to …"; // literal string (−17 tokens)

struct {
    int id;
    const char* name;
    int active;
} BIG_ARRAY[] = {
    {1, "User 1", 1},
    {2, "User 2", 0},
    // … (48 more, −528 tokens)
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
    return NULL;  // … comment omitted
}

// … comment omitted
static void* normalize_user(void* u) {
    if (!u) return NULL;
    // … comment omitted
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

// … comment omitted
typedef struct {
    int data;
} InternalOnly;

static void internal_only_do_work(InternalOnly* obj) {
    if (!obj) return;
    // … comment omitted
}

// … comment omitted
char* public_function(const char* name) {
    if (!name) return NULL;
    // … comment omitted
    return strdup(name);
}

// … comment omitted
static char** private_function(char** data, int count) {
    if (!data) return NULL;
    // … comment omitted
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
