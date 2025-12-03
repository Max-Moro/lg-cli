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
    public static final String LONG_MESSAGE = "This is an extremely long message that contains a…"; // literal string (−62 tokens)

    // Multi-line string with embedded expressions (Java 15+ text blocks)
    public static final String TEMPLATE_WITH_DATA = String.format("""
        User Information:…""", // literal string (−54 tokens)
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
    private static List<String> getPermissions() { return List.of("read", "write", "…"); /* literal array (−0 tokens) */ }
    private static String getLastLogin() { return "2024-01-15T1…"; /* literal string (−5 tokens) */ }
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
    private final Map<String, Object> smallConfig = Map.of("debug", true, "…"); // literal array (−12 tokens)

    private final Map<String, Object> largeConfig = Map.ofEntries(Map.entry("database",, "…"); // literal array (−382 tokens)

    private final List<String> supportedLanguages;
    private final Set<String> allowedExtensions;

    public LiteralDataManager() {
        // Array with many elements (trimming candidate)
        this.supportedLanguages = List.of("english", "spanish", "…"); // literal array (−95 tokens)

        // Set with many elements
        this.allowedExtensions = Set.of(".java", ".kt", "…"); // literal array (−54 tokens)
    }

    public DataContainer processData() {
        // Function with various literal data
        List<String> smallArray = List.of("one", "two", "…"); // literal array (−0 tokens)

        List<String> largeArray = List.of("item_001", "…"); // literal array (−151 tokens)

        Map<String, Object> nestedData = Map.of("level1", "…"); // literal array (−199 tokens)

        return new DataContainer(
            smallArray,
            largeArray,
            Map.of("type", "test", "…"), // literal array (−4 tokens)
            nestedData
        );
    }

    public String getLongQuery() {
        // Very long SQL-like query string
        return """
            SELECT
                user…"""; // literal string (−180 tokens)
    }

    public List<String> getSupportedLanguages() { return supportedLanguages; }
    public Set<String> getAllowedExtensions() { return allowedExtensions; }
}

// Module-level constants with different sizes
class SmallConstants {
    public static final Map<String, Object> VALUES = Map.of("API_VERSION", "v1", "…"); // literal array (−9 tokens)
}

class LargeConstants {
    public static final Map<String, Object> HTTP_STATUS_CODES = Map.ofEntries(Map.entry("CONTINUE", 100), "…"); // literal array (−442 tokens)

    public static final Map<String, String> ERROR_MESSAGES = Map.ofEntries(Map.entry("VALIDATION_FA, "…"); // literal array (−130 tokens)
}
