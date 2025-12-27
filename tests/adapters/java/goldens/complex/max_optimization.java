/**
 * Comprehensive Java sample for Budget System tests.
 */

package com.example.budget;

// … 7 imports omitted (9 lines)

/**
 * Module level long documentation that might be truncated under tight budgets.
 */
public class BudgetSystemSample {
    public static final String MODULE_TITLE = "Budget System Complex Sample";

    public static final String LONG_TEXT = """
        This is an extremely long text block that is designed to be trimmed
        by the literal optimizer when budgets are small. It repeats a m…"""; // literal string (−6 tokens)

    public static final Map<String, Object> BIG_OBJECT = Map.ofEntries(
        Map.entry("users", IntStream.range(1, 51)
            .mapToObj(i -> Map.of(
                "id", i,
                "name", "User " + i,
                "active", i % 2 == 0
            ))
            .collect(Collectors.toList()))
        // … (1 more, −86 tokens)
    );
}

public class PublicService {
    // … field omitted

    /**
     * Public API: gets a user by ID.
     */
    public User getUser(long id) {
        return cache.get(String.valueOf(id));
    }

    // … method omitted (8 lines)

    /** Long method body to allow function body stripping. */
    public ApiResponse<List<User>> process(List<User> list) {
        // … method body omitted (10 lines)
    }
}

// … class omitted (4 lines)

public class Functions {
    public static String publicFunction(String name) {
        // … method body omitted (2 lines)
    }

    // … method omitted (6 lines)

    public static void main(String[] args) {
        // … method body omitted (2 lines)
    }
}

// … 3 classes omitted (32 lines)
