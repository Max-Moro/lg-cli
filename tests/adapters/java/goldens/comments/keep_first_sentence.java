/**
 * Java module for testing comment optimization.
 */

package com.example.comments;

import java.util.List;
import java.util.ArrayList;

// … comment omitted
public class Constants {
    public static final String MODULE_VERSION = "1.0.0"; // … comment omitted
}

/**
 * Data class with Javadoc documentation.
 */
public class User {
    private final long id;        // … comment omitted
    private final String name;    // … comment omitted
    private final String email;   // … comment omitted
    // … comment omitted
    private final Profile profile;

    public User(long id, String name, String email, Profile profile) {
        this.id = id;
        this.name = name;
        this.email = email;
        this.profile = profile;
    }

    public long getId() { return id; }
    public String getName() { return name; }
    public String getEmail() { return email; }
    public Profile getProfile() { return profile; }
}

public class Profile {
    private final String bio;
    private final String avatar;

    public Profile(String bio, String avatar) {
        this.bio = bio;
        this.avatar = avatar;
    }

    public String getBio() { return bio; }
    public String getAvatar() { return avatar; }
}

public class CommentedService {
    private final ServiceConfig config;  // … comment omitted
    private final Logger logger;         // … comment omitted

    /**
     * Class constructor with detailed Javadoc.
     */
    public CommentedService(ServiceConfig config, Logger logger) {
        this.config = config;
        this.logger = logger;

        // … comment omitted
        initialize();

        // … comment omitted
    }

    /**
     * Process user data with validation.
     */
    public User processUser(PartialUser userData) throws ValidationException {
        // … comment omitted
        if (userData == null) {
            throw new IllegalArgumentException("User data is required");
        }

        // … comment omitted (5 lines)
        ValidationResult validationResult = validateUser(userData);
        if (!validationResult.isValid()) {
            // … comment omitted
            if (logger != null) {
                logger.error("Validation failed: " + validationResult.getErrors());
            }
            throw new ValidationException(validationResult.getErrors());
        }

        // … comment omitted
        User transformedData = transformUserData(userData);

        // … comment omitted
        User savedUser = saveUser(transformedData);

        return savedUser;  // … comment omitted
    }

    private ValidationResult validateUser(PartialUser userData) {
        // … comment omitted
        List<String> errors = new ArrayList<>();

        // … comment omitted
        if (userData.getName() == null || userData.getName().isEmpty()) {
            errors.add("Name is required");  // … comment omitted
        }

        if (userData.getEmail() == null || userData.getEmail().isEmpty()) {
            errors.add("Email is required");
        }

        // … comment omitted
        String emailRegex = "^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$";
        if (userData.getEmail() != null && !userData.getEmail().matches(emailRegex)) {
            errors.add("Invalid email format");
        }

        return new ValidationResult(errors.isEmpty(), errors);
    }

    // … comment omitted
    private User transformUserData(PartialUser userData) {
        // … comment omitted (5 lines)
        return new User(
            generateUserId(),    // … comment omitted
            userData.getName().trim(),  // … comment omitted
            userData.getEmail().toLowerCase(),  // … comment omitted
            userData.getProfile() != null ? userData.getProfile() : new Profile("", null)  // … comment omitted
        );
    }

    /**
     * Generate unique user ID.
     */
    private long generateUserId() {
        // … comment omitted
        return (long) (Math.random() * 1000000);
    }

    // … comment omitted
    private User saveUser(User user) {
        // … comment omitted
        if (logger != null) {
            logger.info("Saving user: " + user.getId());
        }

        // … comment omitted
        try {
            Thread.sleep(100);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        return user;  // … comment omitted
    }

    private void initialize() {
        // … comment omitted
    }
}

/**
 * Utility function with comprehensive documentation.
 */
public class StringProcessor {
    public static String processString(String input) {
        // … comment omitted
        if (input == null || input.isEmpty()) {
            return "";  // … comment omitted
        }

        // … comment omitted (5 lines)
        String trimmed = input.trim();
        String lowercase = trimmed.toLowerCase();
        String cleaned = lowercase.replaceAll("[^a-z0-9\\s]", "");

        return cleaned;  // … comment omitted
    }
}

// … comment omitted
class UndocumentedHelper {
    static void undocumentedHelper() {
        // … comment omitted
        String data = "helper data";

        // … comment omitted
        System.out.println(data);  // … comment omitted
    }
}

// … comment omitted
class ValidationResult {
    private final boolean isValid;     // … comment omitted
    private final List<String> errors;  // … comment omitted

    public ValidationResult(boolean isValid, List<String> errors) {
        this.isValid = isValid;
        this.errors = errors;
    }

    public boolean isValid() { return isValid; }
    public List<String> getErrors() { return errors; }
}

class ServiceConfig {
    // … comment omitted
    private final long timeout;      // … comment omitted
    private final int retries;       // … comment omitted
    private final String baseUrl;    // … comment omitted

    public ServiceConfig(long timeout, int retries, String baseUrl) {
        this.timeout = timeout;
        this.retries = retries;
        this.baseUrl = baseUrl;
    }

    public long getTimeout() { return timeout; }
    public int getRetries() { return retries; }
    public String getBaseUrl() { return baseUrl; }
}

// … comment omitted
interface Logger {
    void info(String message);    // … comment omitted
    void error(String message);   // … comment omitted
    void warn(String message);    // … comment omitted
}

// … comment omitted
class ValidationException extends Exception {
    private final List<String> errors;  // … comment omitted

    public ValidationException(List<String> errors) {
        super("Validation failed: " + String.join(", ", errors));
        this.errors = errors;
    }

    public List<String> getErrors() { return errors; }
}

class PartialUser {
    private String name;
    private String email;
    private Profile profile;

    public String getName() { return name; }
    public String getEmail() { return email; }
    public Profile getProfile() { return profile; }

    public void setName(String name) { this.name = name; }
    public void setEmail(String email) { this.email = email; }
    public void setProfile(Profile profile) { this.profile = profile; }
}

// … comment omitted (4 lines)
class DefaultConfig {
    public static final ServiceConfig DEFAULT_CONFIG = new ServiceConfig(
        5000,    // … comment omitted
        3,       // … comment omitted
        "http://localhost:3000"  // … comment omitted
    );
}
