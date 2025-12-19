/**
 * Comprehensive C sample for Budget System tests.
 */

// … comment omitted
// … 5 imports omitted

// … comment omitted
// … 3 imports omitted

/**
 * Module level long documentation that might be truncated under tight budgets.
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
 */
void* public_service_get_user(PublicService* service, int id) // … function body omitted (4 lines)

// … comment omitted
// … function omitted

/** Long method body to allow function body stripping. */
void* public_service_process(PublicService* service, void** list, int count) // … function body omitted (15 lines)

// … comment omitted
// … typedef omitted (3 lines)

// … function omitted

// … comment omitted
char* public_function(const char* name) // … function body omitted (5 lines)

// … comment omitted
// … function omitted

int main(void) // … function body omitted (8 lines)
