/**
 * Comprehensive C sample for Budget System tests.
 * Contains:
 * - External includes
 * - Local includes
 * - Long comments and documentation
 * - Big literals (arrays/structs/strings)
 * - Public vs private API elements
 */

// … 8 imports omitted (10 lines)

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
    // … function body omitted (2 lines)
}

// … function omitted (6 lines)

/** Long method body to allow function body stripping */
void* public_service_process(PublicService* service, void** list, int count) {
    // … function body omitted (10 lines)
}

// … typedef omitted (4 lines)

// … function omitted (4 lines)

// … comment omitted
char* public_function(const char* name) {
    // … function body omitted (3 lines)
}

// … function omitted (10 lines)

int main(void) {
    // … function body omitted (6 lines)
}
