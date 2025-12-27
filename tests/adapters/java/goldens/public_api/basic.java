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

    // … 2 fields omitted (3 lines)
}

// Public interface (should be preserved)
public interface User {
    long getId();
    String getName();
    String getEmail();
    Instant getCreatedAt();
}

// … interface omitted (5 lines)

// Public enum (should be preserved)
public enum UserRole {
    ADMIN, USER, GUEST
}

// Public class with mixed visibility members
public class UserManager {
    // Public properties
    public final String version = PublicConstants.PUBLIC_VERSION;
    public boolean isInitialized = false;

    // … 4 fields omitted (6 lines)

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

    // … 6 methods omitted (33 lines)

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

    // … method omitted (4 lines)

    // Public property with getter
    public int getUserCount() {
        return internalCache.size();
    }

    // … method omitted (7 lines)
}

// … class omitted (13 lines)

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

    // … method omitted (2 lines)
}

// … enum omitted (6 lines)

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

    // … 2 methods omitted (8 lines)
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

    // … method omitted (4 lines)
}

// … class omitted (15 lines)

// ============= Support classes =============

// … 3 classes omitted (36 lines)

// ============= Examples with Java annotations =============

// … 2 annotations omitted (3 lines)

// … class omitted (11 lines)

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

    // … method omitted (4 lines)
}

// Class with mixed annotated members
public class MixedAnnotatedClass {
    @Logged
    public void publicAnnotatedMethod() {
        // Public method with annotation - should preserve both
    }

    // … 2 methods omitted (9 lines)
}

// … class omitted (13 lines)

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
