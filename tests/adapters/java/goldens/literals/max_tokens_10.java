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
    public static final String LONG_MESSAGE = "This is an extremely long message that contains a…"; // literal string (−63 tokens)

    // Multi-line string with embedded expressions (Java 15+ text blocks)
    public static final String TEMPLATE_WITH_DATA = String.format("""
        User…""", // literal string (−58 tokens)
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
    private static String getLastLogin() { return "2024-01-15T1…"; /* literal string (−7 tokens) */ }
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
        Map.entry(
            "database",
            // … (1 more, −140 tokens)
        )
        // … (3 more, −379 tokens)
    );

    private final List<String> supportedLanguages;
    private final Set<String> allowedExtensions;

    public LiteralDataManager() {
        // Array with many elements (trimming candidate)
        this.supportedLanguages = List.of(
            "english"
            // … (23 more, −89 tokens)
        );

        // Set with many elements
        this.allowedExtensions = Set.of(
            ".java"
            // … (17 more, −53 tokens)
        );
    }

    public DataContainer processData() {
        // Function with various literal data
        List<String> smallArray = List.of("one", "two", "three");

        List<String> largeArray = List.of(
            "item_001"
            // … (29 more, −145 tokens)
        );

        Map<String, Object> nestedData = Map.of(
            "level1", Map.of(
                "level2",
                // … (1 more, −188 tokens)
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
            SELECT…"""; // literal string (−185 tokens)
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
        Map.entry("CONTINUE", 100)
        // … (40 more, −401 tokens)
    );

    public static final Map<String, String> ERROR_MESSAGES = Map.ofEntries(
        Map.entry("VALIDATION_FAILED", "Input validation failed. Please check you…" // literal string (−6 tokens))
        // … (6 more, −110 tokens)
    );
}
