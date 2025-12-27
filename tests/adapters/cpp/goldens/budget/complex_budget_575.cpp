/**
 * Comprehensive C++ sample for Budget System tests.
 * Contains:
 * - External includes
 * - Local includes
 * - Long comments and documentation
 * - Big literals (arrays/objects/strings)
 * - Public vs private API elements
 */

// … 8 imports omitted (9 lines)

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
