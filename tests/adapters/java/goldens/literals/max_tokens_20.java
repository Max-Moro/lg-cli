/**
 * Java module for testing literal optimization.
 */

package com.example.literals;

import java.util.*;
import java.time.Instant;

// Short string literal (should be preserved)
class Constants {
    public static final String SHORT_MESSAGE = "Hello, World!";

    // Long string literal (candidate for trimming)
    public static final String LONG_MESSAGE = "This is an extremely long message that contains a substantial amount of text content which might be considered…"; // literal string (−53 tokens)

    // Multi-line string with embedded expressions (Java 15+ text blocks)
    public static final String TEMPLATE_WITH_DATA = String.format("""
        User Information:
        - Name: %s
        - Email:…""", // literal string (−43 tokens)
        getUserName(),
        getUserEmail(),
        Instant.now().toString(),
        getAccountStatus(),
        String.join(", ", getPermissions()),
        getLastLogin(),
        getProfileCompleteness()
    );

    private static String getUserName() { return "John Doe"; }
    private static String getUserEmail() { return "john.doe@example.com"; }
    private static String getAccountStatus() { return "active"; }
    private static List<String> getPermissions() { return List.of("read", "write", "admin"); }
    private static String getLastLogin() { return "2024-01-15T10:30:00Z"; }
    private static int getProfileCompleteness() { return 85; }
}

class DataContainer {
    // Small array (should be preserved)
    private final List<String> tags;

    // Large array (candidate for trimming)
    private final List<String> items;

    // Small object (should be preserved)
    private final Map<String, Object> metadata;

    // Large object (candidate for trimming)
    private final Map<String, Object> configuration;

    public DataContainer(List<String> tags, List<String> items,
                        Map<String, Object> metadata, Map<String, Object> configuration) {
        this.tags = tags;
        this.items = items;
        this.metadata = metadata;
        this.configuration = configuration;
    }

    public List<String> getTags() { return tags; }
    public List<String> getItems() { return items; }
    public Map<String, Object> getMetadata() { return metadata; }
    public Map<String, Object> getConfiguration() { return configuration; }
}

public class LiteralDataManager {
    // Class properties with various literal types
    private final Map<String, Object> smallConfig = Map.of(
        "debug", true,
        "version", "1.0.0"
    );

    private final Map<String, Object> largeConfig = Map.ofEntries(
        Map.entry("database", Map.ofEntries(
            Map.entry("host", "localhost"),
            Map.entry("port", 5432),
            Map.entry("name", "application_db"),
            Map.entry("ssl", false),
            Map.entry("pool", Map.ofEntries(
                Map.entry("min", 2),
                Map.entry("max", 10),
                Map.entry("idleTimeoutMillis", 30000),
                Map.entry("connectionTimeoutMillis", 2000)
            )),
            Map.entry("retry", Map.ofEntries(
                Map.entry("attempts", 3),
                Map.entry("delay", 1000),
                Map.entry("backoff", "exponential")
            ))
        )),
        Map.entry("cache", Map.ofEntries(
            Map.entry("redis", Map.ofEntries(
                Map.entry("host", "localhost"),
                Map.entry("port", 6379),
                Map.entry("db", 0),
                Map.entry("ttl", 3600)
            )),
            Map.entry("memory", Map.ofEntries(
                Map.entry("maxSize", 1000),
                Map.entry("ttl", 1800)
            ))
        )),
        Map.entry("api", Map.ofEntries(
            Map.entry("baseUrl", "https://api.example.com"),
            Map.entry("timeout", 30000),
            Map.entry("retries", 3),
            Map.entry("rateLimit", Map.ofEntries(
                Map.entry("requests", 100),
                Map.entry("window", 60000)
            ))
        )),
        Map.entry("features", Map.ofEntries(
            Map.entry("authentication", true),
            Map.entry("authorization", true),
            Map.entry("logging", true),
            Map.entry("monitoring", true),
            Map.entry("analytics", false),
            Map.entry("caching", true),
            Map.entry("compression", true)
        ))
    );

    private final List<String> supportedLanguages;
    private final Set<String> allowedExtensions;

    public LiteralDataManager() {
        // Array with many elements (trimming candidate)
        this.supportedLanguages = List.of(
            "english", "spanish", "french", "german", "italian", "portuguese",
            "russian", "chinese", "japanese", "korean", "arabic", "hindi",
            "dutch", "swedish", "norwegian", "danish", "finnish", "polish",
            "czech", "hungarian", "romanian", "bulgarian", "croatian", "serbian"
        );

        // Set with many elements
        this.allowedExtensions = Set.of(
            ".java", ".kt", ".scala", ".groovy",
            ".py", ".js", ".ts", ".jsx", ".tsx",
            ".c", ".cpp", ".cs", ".go", ".rs",
            ".php", ".rb", ".swift", ".clj"
        );
    }

    public DataContainer processData() {
        // Function with various literal data
        List<String> smallArray = List.of("one", "two", "three");

        List<String> largeArray = List.of(
            "item_001", "item_002", "item_003", "item_004", "item_005",
            "item_006", "item_007", "item_008", "item_009", "item_010",
            "item_011", "item_012", "item_013", "item_014", "item_015",
            "item_016", "item_017", "item_018", "item_019", "item_020",
            "item_021", "item_022", "item_023", "item_024", "item_025",
            "item_026", "item_027", "item_028", "item_029", "item_030"
        );

        Map<String, Object> nestedData = Map.of(
            "level1", Map.of(
                "level2", Map.of(
                    "level3", Map.ofEntries(
                        Map.entry("data", List.of(
                            Map.of("id", 1, "name", "First", "active", true),
                            Map.of("id", 2, "name", "Second", "active", false),
                            Map.of("id", 3, "name", "Third", "active", true),
                            Map.of("id", 4, "name", "Fourth", "active", true),
                            Map.of("id", 5, "name", "Fifth", "active", false)
                        )),
                        Map.entry("metadata", Map.ofEntries(
                            Map.entry("created", "2024-01-01"),
                            Map.entry("updated", "2024-01-15"),
                            Map.entry("version", 3),
                            Map.entry("checksum", "abcdef123456")
                        ))
                    )
                )
            )
        );

        return new DataContainer(
            smallArray,
            largeArray,
            Map.of("type", "test", "count", smallArray.size()),
            nestedData
        );
    }

    public String getLongQuery() {
        // Very long SQL-like query string
        return """
            SELECT
                users.id, users.username, users.email, users.created_at,…"""; // literal string (−169 tokens)
    }

    public List<String> getSupportedLanguages() { return supportedLanguages; }
    public Set<String> getAllowedExtensions() { return allowedExtensions; }
}

// Module-level constants with different sizes
class SmallConstants {
    public static final Map<String, Object> VALUES = Map.of(
        "API_VERSION", "v1",
        "DEFAULT_LIMIT", 50
    );
}

class LargeConstants {
    public static final Map<String, Object> HTTP_STATUS_CODES = Map.ofEntries(
        Map.entry("CONTINUE", 100),
        Map.entry("SWITCHING_PROTOCOLS", 101),
        Map.entry("OK", 200),
        Map.entry("CREATED", 201),
        Map.entry("ACCEPTED", 202),
        Map.entry("NON_AUTHORITATIVE_INFORMATION", 203),
        Map.entry("NO_CONTENT", 204),
        Map.entry("RESET_CONTENT", 205),
        Map.entry("PARTIAL_CONTENT", 206),
        Map.entry("MULTIPLE_CHOICES", 300),
        Map.entry("MOVED_PERMANENTLY", 301),
        Map.entry("FOUND", 302),
        Map.entry("SEE_OTHER", 303),
        Map.entry("NOT_MODIFIED", 304),
        Map.entry("USE_PROXY", 305),
        Map.entry("TEMPORARY_REDIRECT", 307),
        Map.entry("PERMANENT_REDIRECT", 308),
        Map.entry("BAD_REQUEST", 400),
        Map.entry("UNAUTHORIZED", 401),
        Map.entry("PAYMENT_REQUIRED", 402),
        Map.entry("FORBIDDEN", 403),
        Map.entry("NOT_FOUND", 404),
        Map.entry("METHOD_NOT_ALLOWED", 405),
        Map.entry("NOT_ACCEPTABLE", 406),
        Map.entry("PROXY_AUTHENTICATION_REQUIRED", 407),
        Map.entry("REQUEST_TIMEOUT", 408),
        Map.entry("CONFLICT", 409),
        Map.entry("GONE", 410),
        Map.entry("LENGTH_REQUIRED", 411),
        Map.entry("PRECONDITION_FAILED", 412),
        Map.entry("PAYLOAD_TOO_LARGE", 413),
        Map.entry("URI_TOO_LONG", 414),
        Map.entry("UNSUPPORTED_MEDIA_TYPE", 415),
        Map.entry("RANGE_NOT_SATISFIABLE", 416),
        Map.entry("EXPECTATION_FAILED", 417),
        Map.entry("INTERNAL_SERVER_ERROR", 500),
        Map.entry("NOT_IMPLEMENTED", 501),
        Map.entry("BAD_GATEWAY", 502),
        Map.entry("SERVICE_UNAVAILABLE", 503),
        Map.entry("GATEWAY_TIMEOUT", 504),
        Map.entry("HTTP_VERSION_NOT_SUPPORTED", 505)
    );

    public static final Map<String, String> ERROR_MESSAGES = Map.ofEntries(
        Map.entry("VALIDATION_FAILED", "Input validation failed. Please check your data and try again."),
        Map.entry("AUTHENTICATION_REQUIRED", "Authentication is required to access this resource."),
        Map.entry("AUTHORIZATION_FAILED", "You do not have permission to perform this action."),
        Map.entry("RESOURCE_NOT_FOUND", "The requested resource could not be found on the server."),
        Map.entry("INTERNAL_ERROR", "An internal server error occurred. Please try again later."),
        Map.entry("RATE_LIMIT_EXCEEDED", "Rate limit exceeded. Please wait before making another request."),
        Map.entry("INVALID_REQUEST_FORMAT", "The request format is invalid. Please check the documentation.")
    );
}
