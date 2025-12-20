/**
 * Comprehensive Java sample for Budget System tests.
 */

package com.example.budget;

// … comment omitted
// … 4 imports omitted

// … comment omitted
// … 3 imports omitted

/**
 * Module level long documentation that might be truncated under tight budgets.
 */
public class BudgetSystemSample {
    public static final String MODULE_TITLE = "Budget System Complex Sample";

    public static final String LONG_TEXT = """
        This is an extremely long text block that is designed to be trimmed
        by the literal optimizer when budgets are small. It repeats a m…"""; // literal string (−8 tokens)

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
    public User getUser(long id) // … method body omitted (3 lines)

    // … comment omitted
    private User normalize(Map<String, Object> u) // … method body omitted (7 lines)

    /** Long method body to allow function body stripping. */
    public ApiResponse<List<User>> process(List<User> list) // … method body omitted (12 lines)
}

// … class omitted

public class Functions {
    public static String publicFunction(String name) // … method body omitted (4 lines)

    private static List<String> privateFunction(List<String> data) // … method body omitted (6 lines)

    public static void main(String[] args) // … method body omitted (4 lines)
}

// … comment omitted
// … 3 classes omitted
