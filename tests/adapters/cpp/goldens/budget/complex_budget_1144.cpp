/**
 * Comprehensive C++ sample for Budget System tests.
 * Contains:
 * - External includes
 * - Local includes
 * - Long comments and documentation
 * - Big literals (arrays/objects/strings)
 * - Public vs private API elements
 */

// External includes (most common cases)

// Local includes (treated as local)
#include "types/user.hpp"
#include "types/api_response.hpp"
#include "utils/strings.hpp"

/**
 * Module level long documentation that might be truncated under tight budgets.
 * The text includes several sentences to ensure the comment optimizer has
 * something to work with when switching to keep_first_sentence mode.
 */
const char* MODULE_TITLE = "Budget System Complex Sample";

const char* LONG_TEXT = R"(
This is an extremely long text that is designed to be trimmed
by the literal optimizer when budgets are small. It repeats a message to
ensure length. This is an extremely long text that is designed to be trimmed.
)";

struct UserData {
    int id;
    std::string name;
    bool active;
};

std::vector<UserData> BIG_ARRAY = {
    {1, "User 1", true}, {2, "User 2", false}, {3, "User 3", true}, {4, "User 4", false},
    {5, "User 5", true}, {6, "User 6", false}, {7, "User 7", true}, {8, "User 8", false},
    {9, "User 9", true}, {10, "User 10", false}, {11, "User 11", true}, {12, "User 12", false},
    {13, "User 13", true}, {14, "User 14", false}, {15, "User 15", true}, {16, "User 16", false},
    {17, "User 17", true}, {18, "User 18", false}, {19, "User 19", true}, {20, "User 20", false},
    {21, "User 21", true}, {22, "User 22", false}, {23, "User 23", true}, {24, "User 24", false},
    {25, "User 25", true}, {26, "User 26", false}, {27, "User 27", true}, {28, "User 28", false},
    {29, "User 29", true}, {30, "User 30", false}, {31, "User 31", true}, {32, "User 32", false},
    {33, "User 33", true}, {34, "User 34", false}, {35, "User 35", true}, {36, "User 36", false},
    {37, "User 37", true}, {38, "User 38", false}, {39, "User 39", true}, {40, "User 40", false},
    {41, "User 41", true}, {42, "User 42", false}, {43, "User 43", true}, {44, "User 44", false},
    {45, "User 45", true}, {46, "User 46", false}, {47, "User 47", true}, {48, "User 48", false},
    {49, "User 49", true}, {50, "User 50", false}
};

class PublicService {
private:
    std::map<std::string, void*> cache;

public:
    /**
     * Public API: gets a user by ID.
     * This doc has multiple sentences to allow truncation under budget.
     */
    void* getUser(int id) {
        auto key = std::to_string(id);
        auto it = cache.find(key);
        return (it != cache.end()) ? it->second : nullptr;
    }

private:
    /* Private helper — should not be visible with public_api_only */
    void* normalize(std::map<std::string, std::string> u) {
        // Normalization logic
        return nullptr;
    }

public:
    /** Long method body to allow function body stripping */
    std::vector<void*> process(const std::vector<void*>& list) {
        std::vector<void*> out;

        for (auto item : list) {
            void* n = normalize({});
            if (n) {
                out.push_back(n);
            }
        }

        return out;
    }
};

// Private structure — should be filtered out in public_api_only
namespace {
    class InternalOnly {
    public:
        void doWork() {
            // noop
        }
    };
}

// Public functions
std::string publicFunction(const std::string& name) {
    // Regular comment that may be stripped
    return name;
}

// Private function
namespace {
    std::vector<std::string> privateFunction(const std::vector<std::string>& data) {
        // Not exported; should be removed when public_api_only
        std::vector<std::string> result;
        for (const auto& item : data) {
            result.push_back(item);
        }
        return result;
    }
}

int main() {
    PublicService service;
    void* user = service.getUser(1);
    if (user) {
        std::cout << "Got user" << std::endl;
    }
    return 0;
}
