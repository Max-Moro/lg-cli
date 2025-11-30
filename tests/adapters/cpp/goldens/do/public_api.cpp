/**
 * C++ module for testing public API filtering.
 */

#include <iostream>
#include <string>
#include <map>
#include <vector>
#include <ctime>

// Public module-level constants (should be preserved)
const char* PUBLIC_VERSION = "1.0.0";
const char* API_ENDPOINT = "https://api.example.com";

// Private module-level constants (should be filtered out)
static const char* PRIVATE_SECRET = "internal-use-only";
static std::map<std::string, bool> INTERNAL_CONFIG = {{"debug", true}, {"verbose", false}};

// Public structure (should be preserved)
struct User {
    int id;
    std::string name;
    std::string email;
    time_t createdAt;
};

// Package-private structure (should be filtered out)
namespace {
    struct InternalMetrics {
        long processTime;
        long memoryUsage;
    };
}

// Public enum (should be preserved)
enum class UserRole {
    ADMIN,
    USER,
    GUEST
};

// Private enum (should be filtered out)
namespace {
    enum class InternalEventType {
        USER_CREATED,
        USER_UPDATED,
        CACHE_CLEARED
    };
}

// Public class with mixed visibility members
class UserManager {
public:
    // Public properties
    const std::string version = PUBLIC_VERSION;
    bool isInitialized = false;

    UserManager() : UserManager(API_ENDPOINT) {}

    UserManager(const std::string& apiEndpoint) : apiEndpoint(apiEndpoint) {
        initialize();
    }

    // Public methods (should be preserved)
    User* createUser(const std::string& name, const std::string& email) {
        validateUserData(name, email);

        User* user = new User();
        user->id = generateId();
        user->name = name;
        user->email = email;
        user->createdAt = time(nullptr);

        internalCache[user->email] = user;
        return user;
    }

    User* getUserById(int id) {
        for (auto& pair : internalCache) {
            if (pair.second->id == id) {
                return pair.second;
            }
        }

        return fetchUserFromApi(id);
    }

    std::vector<User*> getAllUsers() {
        std::vector<User*> result;
        for (auto& pair : internalCache) {
            result.push_back(pair.second);
        }
        return result;
    }

    // Public static methods (should be preserved)
    static bool validateUserRole(const std::string& role) {
        return role == "admin" || role == "user" || role == "guest";
    }

    static User* createDefaultUser() {
        User* user = new User();
        user->id = 0;
        user->name = "Default User";
        user->email = "default@example.com";
        user->createdAt = time(nullptr);
        return user;
    }

protected:
    // Protected methods (should be filtered out)
    void initialize() {
        isInitialized = true;
    }

    void logError(const std::string& message, const std::exception& error) {
        std::cerr << "[UserManager] " << message << ": " << error.what() << std::endl;
    }

private:
    // Private properties (should be filtered out with public_api_only)
    std::map<std::string, User*> internalCache;
    void* metrics;
    std::string apiEndpoint;

    // Private methods (should be filtered out)
    void validateUserData(const std::string& name, const std::string& email) {
        if (name.empty() || email.empty()) {
            throw std::runtime_error("Name and email are required");
        }

        if (!isValidEmail(email)) {
            throw std::runtime_error("Invalid email format");
        }
    }

    int generateId() {
        return rand() % 1000000;
    }

    bool isValidEmail(const std::string& email) {
        return email.find('@') != std::string::npos &&
               email.find('.') != std::string::npos;
    }

    User* fetchUserFromApi(int id) {
        try {
            // Simulated API call
            std::cerr << "Fetching user " << id << " from API" << std::endl;
            return nullptr;
        } catch (const std::exception& error) {
            logError("Failed to fetch user", error);
            return nullptr;
        }
    }

    // Private static methods (should be filtered out)
    static std::string formatInternalId(int id) {
        char buffer[20];
        snprintf(buffer, sizeof(buffer), "internal_%06d", id);
        return std::string(buffer);
    }
};

// Package-private class (should be filtered out)
namespace {
    class InternalLogger {
    private:
        std::vector<std::string> logs;

    public:
        void log(const std::string& message) {
            logs.push_back(message);
        }

        std::vector<std::string> getLogs() const {
            return logs;
        }

    private:
        void clearLogs() {
            logs.clear();
        }
    };
}

// Public abstract class (should be preserved)
class BaseService {
public:
    virtual std::string getServiceName() const = 0;
    virtual void initialize() = 0;

    std::map<std::string, std::string> getServiceInfo() {
        std::map<std::string, std::string> info;
        info["name"] = getServiceName();
        info["version"] = PUBLIC_VERSION;
        return info;
    }

protected:
    virtual bool validateConfig(const std::map<std::string, std::string>& config) = 0;
};

// Public functions (should be preserved)
UserManager* createUserManager() {
    return createUserManager(nullptr);
}

UserManager* createUserManager(const char* endpoint) {
    return new UserManager(endpoint ? endpoint : API_ENDPOINT);
}

bool isValidUserRole(const std::string& role) {
    return UserManager::validateUserRole(role);
}

// Private functions (should be filtered out)
namespace {
    void logInternalEvent(InternalEventType event, void* data) {
        std::cout << "[Internal] Event logged" << std::endl;
    }

    void processInternalMetrics(const InternalMetrics& metrics) {
        std::cout << "Processing metrics" << std::endl;
    }
}

// Public utility class (should be preserved)
class UserUtils {
public:
    static std::string formatUserName(const User& user) {
        return user.name + " (" + user.email + ")";
    }

    static long getUserAge(const User& user) {
        time_t now = time(nullptr);
        return (now - user.createdAt) / (60 * 60 * 24);
    }

private:
    static std::string internalFormatting(const std::string& text) {
        std::string result = text;
        std::transform(result.begin(), result.end(), result.begin(), ::tolower);
        return result;
    }
};

// Package-private utility class (should be filtered out)
namespace {
    class InternalUtils {
    public:
        static void debugLog(const std::string& message) {
            if (INTERNAL_CONFIG["debug"]) {
                std::cout << "[Debug] " << message << std::endl;
            }
        }

        template<typename T>
        static T measurePerformance(std::function<T()> fn) {
            clock_t start = clock();
            T result = fn();
            clock_t end = clock();

            double elapsed = double(end - start) / CLOCKS_PER_SEC * 1000;
            std::cout << "Performance: " << elapsed << "ms" << std::endl;
            return result;
        }
    };
}
