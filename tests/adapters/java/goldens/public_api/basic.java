/**
 * Java module for testing public API filtering.
 */

package com.example.publicapi;

import java.time.Instant;
import java.util.*;

// Public module-level constants (should be preserved)
public class PublicConstants {
    public static final String PUBLIC_VERSION = "1.0.0";
    public static final String API_ENDPOINT = "https://api.example.com";

    // Private constants (should be filtered out)
    // … 2 fields omitted
}

// Public interface (should be preserved)
public interface User {
    long getId();
    String getName();
    String getEmail();
    Instant getCreatedAt();
}

// Package-private interface (should be filtered out)
// … interface omitted

// Public enum (should be preserved)
public enum UserRole {
    ADMIN, USER, GUEST
}

// Public class with mixed visibility members
public class UserManager {
    // Public properties
    public final String version = PublicConstants.PUBLIC_VERSION;
    public boolean isInitialized = false;

    // Private properties (should be filtered out with public_api_only)
    // … 2 fields omitted

    // Protected properties (should be filtered out)
    // … 2 fields omitted

    public UserManager() {
        this(PublicConstants.API_ENDPOINT);
    }

    public UserManager(String apiEndpoint) {
        this.apiEndpoint = apiEndpoint;
        initialize();
    }

    // Public methods (should be preserved)
    public User createUser(PartialUser userData) {
        validateUserData(userData);

        UserImpl user = new UserImpl(
            generateId(),
            userData.getName(),
            userData.getEmail(),
            Instant.now()
        );

        internalCache.put(user.getEmail(), user);
        return user;
    }

    public User getUserById(long id) {
        for (User user : internalCache.values()) {
            if (user.getId() == id) {
                return user;
            }
        }

        return fetchUserFromApi(id);
    }

    public List<User> getAllUsers() {
        return new ArrayList<>(internalCache.values());
    }

    // Private methods (should be filtered out)
    // … 4 methods omitted

    // Protected methods (should be filtered out)
    // … 2 methods omitted

    // Public static methods (should be preserved)
    public static boolean validateUserRole(String role) {
        try {
            UserRole.valueOf(role.toUpperCase());
            return true;
        } catch (IllegalArgumentException e) {
            return false;
        }
    }

    public static User createDefaultUser() {
        return new UserImpl(0, "Default User", "default@example.com", Instant.now());
    }

    // Private static methods (should be filtered out)
    // … method omitted

    // Public property with getter
    public int getUserCount() {
        return internalCache.size();
    }

    // Private property with getter (should be filtered out)
    // … method omitted
}

// Package-private class (should be filtered out)
// … class omitted

// Public abstract class (should be preserved)
public abstract class BaseService {
    // … method omitted

    public abstract void initialize();

    public Map<String, String> getServiceInfo() {
        Map<String, String> info = new HashMap<>();
        info.put("name", getServiceName());
        info.put("version", PublicConstants.PUBLIC_VERSION);
        return info;
    }

    // Protected abstract method (should be filtered out in public API)
    // … method omitted
}

// Private enum (should be filtered out)
// … enum omitted

// Public functions (should be preserved)
public class UserManagerFactory {
    public static UserManager createUserManager() {
        return createUserManager(null);
    }

    public static UserManager createUserManager(String endpoint) {
        return new UserManager(endpoint != null ? endpoint : PublicConstants.API_ENDPOINT);
    }

    public static boolean isValidUserRole(Object role) {
        return UserManager.validateUserRole(role.toString());
    }

    // Private functions (should be filtered out)
    // … 2 methods omitted
}

// Public utility class (should be preserved)
public class UserUtils {
    public static String formatUserName(User user) {
        return user.getName() + " (" + user.getEmail() + ")";
    }

    public static long getUserAge(User user) {
        Instant now = Instant.now();
        Instant created = user.getCreatedAt();
        return (now.toEpochMilli() - created.toEpochMilli()) / (1000 * 60 * 60 * 24);
    }

    // Private utility member (should be filtered out)
    // … method omitted
}

// Package-private utility class (should be filtered out)
// … class omitted

// ============= Support classes =============

// … 3 classes omitted

// ============= Examples with Java annotations =============

// Simple annotation examples
// … 2 annotations omitted

// … class omitted

@Logged
@Validate
public class PublicAnnotatedClass {
    /**
     * Public class with multiple annotations - should be preserved with annotations.
     */

    public String data = "public";

    @Logged
    public String processData() {
        return data.toUpperCase();
    }

    // … method omitted
}

// Class with mixed annotated members
public class MixedAnnotatedClass {
    @Logged
    public void publicAnnotatedMethod() {
        // Public method with annotation - should preserve both
    }

    // … 2 methods omitted
}

// Multiple stacked annotations on private elements
// … class omitted

@Logged
@Validate
public class PublicMultiAnnotatedClass {
    /**
     * Public class with multiple annotations - should preserve class and all annotations.
     */

    @Logged
    @Validate
    public void multiAnnotatedMethod() {
        // Multiple annotations on public method - should preserve all
    }
}
