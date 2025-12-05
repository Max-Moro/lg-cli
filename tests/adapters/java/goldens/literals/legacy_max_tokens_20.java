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
        // … (7 more, −124 tokens)
    }};

    // Nested map with double-brace (complex case)
    private static final Map<String, Map<String, Object>> DATABASE_CONFIG = new HashMap<String, Map<String, Object>>() {{
        put("database", new HashMap<String, Object>() {{
            put("host", "localhost");
            put("port", 5432);
            // … (8 more, −65 tokens)
        }});
        // … (2 more, −117 tokens)
    }};

    // List with double-brace initialization
    private static final List<String> SUPPORTED_LANGUAGES = new ArrayList<String>() {{
        add("english");
        add("spanish");
        add("french");
        add("german");
        // … (20 more, −103 tokens)
    }};

    public static void main(String[] args) {
        System.out.println("Error messages: " + ERROR_MESSAGES.size());
        System.out.println("Supported languages: " + SUPPORTED_LANGUAGES.size());
        System.out.println("Config sections: " + DATABASE_CONFIG.keySet());
    }
}
