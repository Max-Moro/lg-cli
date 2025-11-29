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
    private static final String PRIVATE_SECRET = "internal-use-only";
    private static final Map<String, Object> INTERNAL_CONFIG = Map.of("debug", true, "verbose", false);
}

// Public interface (should be preserved)
public interface User {
    long getId();
    String getName();
    String getEmail();
    Instant getCreatedAt();
}

// Package-private interface (should be filtered out)
interface InternalMetrics {
    long getProcessTime();
    long getMemoryUsage();
}

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
    private final Map<String, User> internalCache = new HashMap<>();
    private final InternalMetrics metrics = new InternalMetricsImpl();

    // Protected properties (should be filtered out)
    protected Map<String, Object> config = new HashMap<>();

    private final String apiEndpoint;

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
    private void validateUserData(PartialUser userData) {
        if (userData.getName() == null || userData.getEmail() == null) {
            throw new IllegalArgumentException("Name and email are required");
        }

        if (!isValidEmail(userData.getEmail())) {
            throw new IllegalArgumentException("Invalid email format");
        }
    }

    private long generateId() {
        return (long) (Math.random() * 1000000);
    }

    private boolean isValidEmail(String email) {
        String emailRegex = "^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$";
        return email.matches(emailRegex);
    }

    private User fetchUserFromApi(long id) {
        try {
            // Simulated API call
            return null;
        } catch (Exception error) {
            logError("Failed to fetch user", error);
            return null;
        }
    }

    // Protected methods (should be filtered out)
    protected void initialize() {
        config.putAll(PublicConstants.INTERNAL_CONFIG);
        isInitialized = true;
    }

    protected void logError(String message, Exception error) {
        System.err.println("[UserManager] " + message + ": " + error.getMessage());
    }

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
    private static String formatInternalId(long id) {
        return String.format("internal_%06d", id);
    }

    // Public property with getter
    public int getUserCount() {
        return internalCache.size();
    }

    // Private property with getter (should be filtered out)
    private Map<String, Object> getInternalState() {
        Map<String, Object> state = new HashMap<>();
        state.put("cacheSize", internalCache.size());
        state.put("metrics", metrics);
        return state;
    }
}

// Package-private class (should be filtered out)
class InternalLogger {
    private final List<String> logs = new ArrayList<>();

    public void log(String message) {
        logs.add(Instant.now() + ": " + message);
    }

    public List<String> getLogs() {
        return new ArrayList<>(logs);
    }

    private void clearLogs() {
        logs.clear();
    }
}

// Public abstract class (should be preserved)
public abstract class BaseService {
    protected abstract String getServiceName();

    public abstract void initialize();

    public Map<String, String> getServiceInfo() {
        Map<String, String> info = new HashMap<>();
        info.put("name", getServiceName());
        info.put("version", PublicConstants.PUBLIC_VERSION);
        return info;
    }

    // Protected abstract method (should be filtered out in public API)
    protected abstract boolean validateConfig(Map<String, Object> config);
}

// Private enum (should be filtered out)
enum InternalEventType {
    USER_CREATED,
    USER_UPDATED,
    CACHE_CLEARED
}

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
    private static void logInternalEvent(InternalEventType event, Object data) {
        System.out.println("[Internal] " + event + ": " + data);
    }

    private static void processInternalMetrics(InternalMetrics metrics) {
        // Process internal metrics
        System.out.println("Processing metrics: " + metrics);
    }
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
    private static String internalFormatting(String text) {
        return text.toLowerCase().replace("\\s+", "_");
    }
}

// Package-private utility class (should be filtered out)
class InternalUtils {
    static void debugLog(String message) {
        if ((Boolean) PublicConstants.INTERNAL_CONFIG.get("debug")) {
            System.out.println("[Debug] " + message);
        }
    }

    static <T> T measurePerformance(java.util.function.Supplier<T> fn) {
        long start = System.nanoTime();
        T result = fn.get();
        long end = System.nanoTime();
        System.out.println("Performance: " + ((end - start) / 1_000_000) + "ms");
        return result;
    }
}

// ============= Support classes =============

class UserImpl implements User {
    private final long id;
    private final String name;
    private final String email;
    private final Instant createdAt;

    public UserImpl(long id, String name, String email, Instant createdAt) {
        this.id = id;
        this.name = name;
        this.email = email;
        this.createdAt = createdAt;
    }

    @Override
    public long getId() { return id; }

    @Override
    public String getName() { return name; }

    @Override
    public String getEmail() { return email; }

    @Override
    public Instant getCreatedAt() { return createdAt; }
}

class InternalMetricsImpl implements InternalMetrics {
    private long processTime = 0;
    private long memoryUsage = 0;

    @Override
    public long getProcessTime() { return processTime; }

    @Override
    public long getMemoryUsage() { return memoryUsage; }
}

class PartialUser {
    private String name;
    private String email;

    public String getName() { return name; }
    public String getEmail() { return email; }

    public void setName(String name) { this.name = name; }
    public void setEmail(String email) { this.email = email; }
}

// ============= Examples with Java annotations =============

// Simple annotation examples
@interface Logged {}

@interface Validate {}

@Logged
class PrivateAnnotatedClass {
    /**
     * Private class with annotation - should be removed completely including @Logged.
     */

    private String data = "private";

    @Validate
    private String processData() {
        return data.toUpperCase();
    }
}

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

    @Validate
    private void internalProcess() {
        // Private method with annotation - should remove method and annotation
    }
}

// Class with mixed annotated members
public class MixedAnnotatedClass {
    @Logged
    public void publicAnnotatedMethod() {
        // Public method with annotation - should preserve both
    }

    @Logged
    @Validate
    private void privateAnnotatedMethod() {
        // Private method with annotations - should remove method and both annotations
    }

    @Validate
    protected void protectedAnnotatedMethod() {
        // Protected method with annotation - should remove method and annotation
    }
}

// Multiple stacked annotations on private elements
@Logged
@Validate
class PrivateMultiAnnotatedClass {
    /**
     * Private class with multiple annotations - should remove class and all annotations.
     */

    @Logged
    @Validate
    private void multiAnnotatedMethod() {
        // Multiple annotations on private method
    }
}

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
