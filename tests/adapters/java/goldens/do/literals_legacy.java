// Java legacy code example with double-brace initialization pattern
// This pattern was common in Java 7-8 but is now considered anti-pattern
// Kept for testing literal optimization on legacy codebases

import java.util.*;

public class LegacyLiterals {
    // Small map (should be preserved)
    private static final Map<String, Integer> SMALL_CONFIG = new HashMap<String, Integer>() {{
        put("timeout", 30);
        put("retries", 3);
    }};

    // Large map with double-brace (candidate for trimming)
    private static final Map<String, String> ERROR_MESSAGES = new HashMap<String, String>() {{
        put("VALIDATION_FAILED", "Input validation failed. Please check your data and try again.");
        put("AUTHENTICATION_REQUIRED", "Authentication is required to access this resource.");
        put("AUTHORIZATION_FAILED", "You do not have permission to perform this action.");
        put("RESOURCE_NOT_FOUND", "The requested resource could not be found on the server.");
        put("INTERNAL_ERROR", "An internal server error occurred. Please try again later.");
        put("RATE_LIMIT_EXCEEDED", "Rate limit exceeded. Please wait before making another request.");
        put("SERVICE_UNAVAILABLE", "The service is temporarily unavailable. Please try again later.");
        put("INVALID_CREDENTIALS", "The provided credentials are invalid. Please check and try again.");
    }};

    // Nested map with double-brace (complex case)
    private static final Map<String, Map<String, Object>> DATABASE_CONFIG = new HashMap<String, Map<String, Object>>() {{
        put("database", new HashMap<String, Object>() {{
            put("host", "localhost");
            put("port", 5432);
            put("name", "application_db");
            put("ssl", false);
            put("pool_min", 2);
            put("pool_max", 10);
            put("idle_timeout", 30000);
            put("connection_timeout", 2000);
            put("retry_attempts", 3);
            put("retry_delay", 1000);
        }});
        put("cache", new HashMap<String, Object>() {{
            put("redis_port", 6379);
            put("redis_db", 0);
            put("redis_ttl", 3600);
            put("memory_max_size", 1000);
            put("memory_ttl", 1800);
        }});
        put("api", new HashMap<String, Object>() {{
            put("timeout", 30000);
            put("retries", 3);
            put("rate_limit_requests", 100);
            put("rate_limit_window", 60000);
        }});
    }};

    // List with double-brace initialization
    private static final List<String> SUPPORTED_LANGUAGES = new ArrayList<String>() {{
        add("english");
        add("spanish");
        add("french");
        add("german");
        add("italian");
        add("portuguese");
        add("russian");
        add("chinese");
        add("japanese");
        add("korean");
        add("arabic");
        add("hindi");
        add("dutch");
        add("swedish");
        add("norwegian");
        add("danish");
        add("finnish");
        add("polish");
        add("czech");
        add("hungarian");
        add("romanian");
        add("bulgarian");
        add("croatian");
        add("serbian");
    }};

    public static void main(String[] args) {
        System.out.println("Error messages: " + ERROR_MESSAGES.size());
        System.out.println("Supported languages: " + SUPPORTED_LANGUAGES.size());
        System.out.println("Config sections: " + DATABASE_CONFIG.keySet());
    }
}
