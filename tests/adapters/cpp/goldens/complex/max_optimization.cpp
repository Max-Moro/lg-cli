/**
 * Comprehensive C++ sample for Budget System tests.
 */

// … comment omitted
// … 8 imports omitted

// … comment omitted
// … 3 imports omitted

/**
 * Module level long documentation that might be truncated under tight budgets.
 */
const char* MODULE_TITLE = "Budget System Complex Sample";

const char* LONG_TEXT = R"(
This is an extremely long text that is designed to be trimmed
by the literal optimizer when budgets are small. It repeats a message…)"; // literal string (−21 tokens)

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
     */
    void* getUser(int id) // … method body omitted (5 lines)

private:
    // … comment omitted
    void* normalize(std::map<std::string, std::string> u) // … method body omitted (4 lines)

public:
    /** Long method body to allow function body stripping. */
    std::vector<void*> process(const std::vector<void*>& list) // … method body omitted (12 lines)
};

// … comment omitted
namespace {
    // … class omitted;
}

// … comment omitted
std::string publicFunction(const std::string& name) // … function body omitted (4 lines)

// … comment omitted
namespace {
    std::vector<std::string> privateFunction(const std::vector<std::string>& data) // … function body omitted (8 lines)
}

int main() // … function body omitted (8 lines)
