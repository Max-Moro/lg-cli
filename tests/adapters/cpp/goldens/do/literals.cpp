/**
 * C++ module for testing literal optimization.
 */

#include <iostream>
#include <vector>
#include <string>
#include <map>

// Short string literal (should be preserved)
const char* SHORT_MESSAGE = "Hello, World!";

// Long string literal (candidate for trimming)
const char* LONG_MESSAGE = "This is an extremely long message that contains a substantial amount of text content which might be considered for trimming when optimizing C++ code for AI context windows. The message continues with detailed explanations and verbose descriptions that may not be essential for understanding the core functionality and structure of the code. This string literal spans multiple conceptual lines even though it's defined as a single string literal.";

// Multi-line string with formatting (C++11 raw string literal)
const char* TEMPLATE_WITH_DATA = R"(
User Information:
- Name: %s
- Email: %s
- Registration Date: %s
- Account Status: %s
- Permissions: %s
- Last Login: %s
- Profile Completeness: %d%%
)";

struct DataContainer {
    // Small array (should be preserved)
    std::vector<std::string> tags;

    // Large array (candidate for trimming)
    std::vector<std::string> items;

    // Small object (should be preserved)
    std::map<std::string, std::string> metadata;

    // Large object (candidate for trimming)
    std::map<std::string, int> configuration;
};

class LiteralDataManager {
private:
    // Class properties with various literal types
    std::map<std::string, bool> smallConfig = {
        {"debug", true},
        {"verbose", false}
    };

    std::map<std::string, std::map<std::string, int>> largeConfig = {
        {"database", {
            {"port", 5432},
            {"pool_min", 2},
            {"pool_max", 10},
            {"idle_timeout", 30000},
            {"connection_timeout", 2000},
            {"retry_attempts", 3},
            {"retry_delay", 1000}
        }},
        {"cache", {
            {"redis_port", 6379},
            {"redis_db", 0},
            {"redis_ttl", 3600},
            {"memory_max_size", 1000},
            {"memory_ttl", 1800}
        }},
        {"api", {
            {"timeout", 30000},
            {"retries", 3},
            {"rate_limit_requests", 100},
            {"rate_limit_window", 60000}
        }},
        {"features", {
            {"authentication", 1},
            {"authorization", 1},
            {"logging", 1},
            {"monitoring", 1},
            {"analytics", 0},
            {"caching", 1},
            {"compression", 1}
        }}
    };

    std::vector<std::string> supportedLanguages;
    std::vector<std::string> allowedExtensions;

public:
    LiteralDataManager() {
        // Array with many elements (trimming candidate)
        supportedLanguages = {
            "english", "spanish", "french", "german", "italian", "portuguese",
            "russian", "chinese", "japanese", "korean", "arabic", "hindi",
            "dutch", "swedish", "norwegian", "danish", "finnish", "polish",
            "czech", "hungarian", "romanian", "bulgarian", "croatian", "serbian"
        };

        // Array with many elements
        allowedExtensions = {
            ".cpp", ".hpp", ".cxx", ".hxx", ".cc", ".h",
            ".py", ".js", ".ts", ".jsx", ".tsx",
            ".java", ".kt", ".scala",
            ".cs", ".go", ".rs",
            ".php", ".rb", ".swift", ".clj"
        };
    }

    DataContainer processData() {
        // Function with various literal data
        std::vector<std::string> smallArray = {"one", "two", "three"};

        std::vector<std::string> largeArray = {
            "item_001", "item_002", "item_003", "item_004", "item_005",
            "item_006", "item_007", "item_008", "item_009", "item_010",
            "item_011", "item_012", "item_013", "item_014", "item_015",
            "item_016", "item_017", "item_018", "item_019", "item_020",
            "item_021", "item_022", "item_023", "item_024", "item_025",
            "item_026", "item_027", "item_028", "item_029", "item_030"
        };

        std::map<std::string, std::vector<std::map<std::string, std::string>>> nestedData = {
            {"level1", {
                {{"id", "1"}, {"name", "First"}, {"active", "true"}},
                {{"id", "2"}, {"name", "Second"}, {"active", "false"}},
                {{"id", "3"}, {"name", "Third"}, {"active", "true"}},
                {{"id", "4"}, {"name", "Fourth"}, {"active", "true"}},
                {{"id", "5"}, {"name", "Fifth"}, {"active", "false"}}
            }}
        };

        DataContainer container;
        container.tags = smallArray;
        container.items = largeArray;
        container.metadata = {{"type", "test"}, {"count", "3"}};

        return container;
    }

    std::string getLongQuery() {
        // Very long SQL-like query string (C++11 raw string)
        return R"(
SELECT
    users.id, users.username, users.email, users.created_at,
    profiles.first_name, profiles.last_name, profiles.bio, profiles.avatar_url,
    addresses.street, addresses.city, addresses.state, addresses.postal_code, addresses.country,
    subscriptions.plan_name, subscriptions.status, subscriptions.expires_at,
    payments.amount, payments.currency, payments.payment_date, payments.method
FROM users
LEFT JOIN profiles ON users.id = profiles.user_id
LEFT JOIN addresses ON users.id = addresses.user_id
LEFT JOIN subscriptions ON users.id = subscriptions.user_id
LEFT JOIN payments ON users.id = payments.user_id
WHERE users.is_active = true
    AND users.email_verified = true
    AND profiles.is_public = true
    AND subscriptions.status IN ('active', 'trial')
ORDER BY users.created_at DESC, subscriptions.expires_at ASC
LIMIT 100 OFFSET 0
        )";
    }

    const std::vector<std::string>& getSupportedLanguages() const {
        return supportedLanguages;
    }

    const std::vector<std::string>& getAllowedExtensions() const {
        return allowedExtensions;
    }
};

// Module-level constants with different sizes
struct SmallConstants {
    static constexpr const char* API_VERSION = "v1";
    static constexpr int DEFAULT_LIMIT = 50;
};

struct HttpStatusCodes {
    static constexpr int CONTINUE = 100;
    static constexpr int SWITCHING_PROTOCOLS = 101;
    static constexpr int OK = 200;
    static constexpr int CREATED = 201;
    static constexpr int ACCEPTED = 202;
    static constexpr int NO_CONTENT = 204;
    static constexpr int MOVED_PERMANENTLY = 301;
    static constexpr int FOUND = 302;
    static constexpr int NOT_MODIFIED = 304;
    static constexpr int BAD_REQUEST = 400;
    static constexpr int UNAUTHORIZED = 401;
    static constexpr int FORBIDDEN = 403;
    static constexpr int NOT_FOUND = 404;
    static constexpr int METHOD_NOT_ALLOWED = 405;
    static constexpr int CONFLICT = 409;
    static constexpr int INTERNAL_SERVER_ERROR = 500;
    static constexpr int NOT_IMPLEMENTED = 501;
    static constexpr int BAD_GATEWAY = 502;
    static constexpr int SERVICE_UNAVAILABLE = 503;
};

struct ErrorMessages {
    static constexpr const char* VALIDATION_FAILED =
        "Input validation failed. Please check your data and try again.";
    static constexpr const char* AUTHENTICATION_REQUIRED =
        "Authentication is required to access this resource.";
    static constexpr const char* AUTHORIZATION_FAILED =
        "You do not have permission to perform this action.";
    static constexpr const char* RESOURCE_NOT_FOUND =
        "The requested resource could not be found on the server.";
    static constexpr const char* INTERNAL_ERROR =
        "An internal server error occurred. Please try again later.";
    static constexpr const char* RATE_LIMIT_EXCEEDED =
        "Rate limit exceeded. Please wait before making another request.";
};
