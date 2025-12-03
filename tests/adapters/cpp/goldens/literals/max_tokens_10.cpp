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
const char* LONG_MESSAGE = "This is an extremely long message that contains…"; // literal string (−64 tokens)

// Multi-line string with formatting (C++11 raw string literal)
const char* TEMPLATE_WITH_DATA = R"(
User Information…)"; // literal string (−47 tokens)

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
    }; // literal array (−6 tokens)

    std::map<std::string, std::map<std::string, int>> largeConfig = {
        {"database", {}},
    }; // literal array (−212 tokens)

    std::vector<std::string> supportedLanguages;
    std::vector<std::string> allowedExtensions;

public:
    LiteralDataManager() {
        // Array with many elements (trimming candidate)
        supportedLanguages = {
            "english",
            "spanish",
            "french",
            "…",
        }; // literal array (−84 tokens)

        // Array with many elements
        allowedExtensions = {
            ".cpp",
            ".hpp",
            ".cxx",
            "…",
        }; // literal array (−54 tokens)
    }

    DataContainer processData() {
        // Function with various literal data
        std::vector<std::string> smallArray = {"one", "two", "three"};

        std::vector<std::string> largeArray = {
            "item_001",
            "item_002",
            "…",
        }; // literal array (−140 tokens)

        std::map<std::string, std::vector<std::map<std::string, std::string>>> nestedData = {{}}; // literal array (−110 tokens)

        DataContainer container;
        container.tags = smallArray;
        container.items = largeArray;
        container.metadata = {{"type", "test"}}; // literal array (−6 tokens)

        return container;
    }

    std::string getLongQuery() {
        // Very long SQL-like query string (C++11 raw string)
        return R"(
SELECT
    users.id, users.u…)"; // literal string (−168 tokens)
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
        "Input validation failed. Please check you…"; // literal string (−4 tokens)
    static constexpr const char* AUTHENTICATION_REQUIRED =
        "Authentication is required to access this resource.";
    static constexpr const char* AUTHORIZATION_FAILED =
        "You do not have permission to perform this action.";
    static constexpr const char* RESOURCE_NOT_FOUND =
        "The requested resource could not be foun…"; // literal string (−2 tokens)
    static constexpr const char* INTERNAL_ERROR =
        "An internal server error occurred. Please…"; // literal string (−3 tokens)
    static constexpr const char* RATE_LIMIT_EXCEEDED =
        "Rate limit exceeded. Please wait before makin…"; // literal string (−1 tokens)
};
