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
    private static List<String> getPermissions() { return [L, "…"]; /* literal array (−6 tokens) */ }
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
    private final Map<String, Object> smallConfig = [M, "…"]; // literal array (−17 tokens)

    private final Map<String, Object> largeConfig = [M, "…"]; // literal array (−389 tokens)

    private final List<String> supportedLanguages;
    private final Set<String> allowedExtensions;

    public LiteralDataManager() {
        // Array with many elements (trimming candidate)
        this.supportedLanguages = [L, "…"]; // literal array (−102 tokens)

        // Set with many elements
        this.allowedExtensions = [S, "…"]; // literal array (−60 tokens)
    }

    public DataContainer processData() {
        // Function with various literal data
        List<String> smallArray = [L, "…"]; // literal array (−6 tokens)

        List<String> largeArray = [L, "…"]; // literal array (−156 tokens)

        Map<String, Object> nestedData = [M, "…"]; // literal array (−203 tokens)

        return new DataContainer(
            smallArray,
            largeArray,
            [M, "…"], // literal array (−10 tokens)
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
    public static final Map<String, Object> VALUES = [M, "…"]; // literal array (−17 tokens)
}

class LargeConstants {
    public static final Map<String, Object> HTTP_STATUS_CODES = [M, "…"]; // literal array (−452 tokens)

    public static final Map<String, String> ERROR_MESSAGES = [M, "…"]; // literal array (−138 tokens)
}
