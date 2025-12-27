/**
 * Comprehensive C++ sample for Budget System tests.
 * Contains:
 * - External includes
 * - Local includes
 * - Long comments and documentation
 * - Big literals (arrays/objects/strings)
 * - Public vs private API elements
 */

// … 11 imports omitted (13 lines)

/**
 * Module level long documentation that might be truncated under tight budgets.
 * The text includes several sentences to ensure the comment optimizer has
 * something to work with when switching to keep_first_sentence mode.
 */
const char* MODULE_TITLE = "Budget System Complex Sample";

const char* LONG_TEXT = R"(
This is an extremely long text that is designed to be trimmed
by the literal optimizer when budgets are small. It repeats a message…)"; // literal string (−17 tokens)

struct UserData {
    int id;
    std::string name;
    bool active;
};

std::vector<UserData> BIG_ARRAY = {
    {1, "User 1", true},
    {2, "User 2", false},
    // … (48 more, −480 tokens)
};

class PublicService {
private:
    // … field omitted

public:
    /**
     * Public API: gets a user by ID.
     * This doc has multiple sentences to allow truncation under budget.
     */
    void* getUser(int id) {
        // … method body omitted (3 lines)
    }

private:
    // … method omitted (5 lines)

public:
    /** Long method body to allow function body stripping */
    std::vector<void*> process(const std::vector<void*>& list) {
        // … method body omitted (8 lines)
    }
};

// … comment omitted
namespace {
    // … class omitted (6 lines);
}

// … comment omitted
std::string publicFunction(const std::string& name) {
    // … function body omitted (2 lines)
}

// … comment omitted
namespace {
    // … function omitted (8 lines)
}

int main() {
    // … function body omitted (6 lines)
}
