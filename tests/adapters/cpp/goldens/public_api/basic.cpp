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
// … 2 variables omitted

// Public structure (should be preserved)
struct User {
    int id;
    std::string name;
    std::string email;
    time_t createdAt;
};

// Package-private structure (should be filtered out)
namespace {
    // … struct omitted (4 lines);
}

// Public enum (should be preserved)
enum class UserRole {
    ADMIN,
    USER,
    GUEST
};

// Private enum (should be filtered out)
namespace {
    // … enum omitted (5 lines);
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
    // … 2 methods omitted

private:
    // Private properties (should be filtered out with public_api_only)
    // … 3 fields omitted

    // Private methods (should be filtered out)
    // … 4 methods omitted

    // Private static methods (should be filtered out)
    // … method omitted
};

// Package-private class (should be filtered out)
namespace {
    // … class omitted;
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
    // … field omitted
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
    // … 2 functions omitted
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
    // … method omitted
};

// Package-private utility class (should be filtered out)
namespace {
    // … class omitted;
}
