/**
 * Comprehensive Java sample for Budget System tests.
 * Contains:
 * - External imports
 * - Local imports
 * - Long comments and Javadoc
 * - Big literals (arrays/objects/text blocks)
 * - Public vs private API elements
 */

package com.example.budget;







/**
 * Module level long documentation that might be truncated under tight budgets.
 * The text includes several sentences to ensure the comment optimizer has
 * something to work with when switching to keep_first_sentence mode.
 */
public class BudgetSystemSample {
    public static final String MODULE_TITLE = "Budget System Complex Sample";

    public static final String LONG_TEXT = """
        This is an extremely long text block that is designed to be trimmed
        by the literal optimizer when budgets are small. It repeats a m…""";

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
    

    /**
     * Public API: gets a user by ID.
     * This doc has multiple sentences to allow truncation under budget.
     */
    public User getUser(long id) {
        return cache.get(String.valueOf(id));
    }

    
    

    /** Long method body to allow function body stripping */
    public ApiResponse<List<User>> process(List<User> list) {
        List<User> out = new ArrayList<>();
        for (User u : list) {
            User n = normalize(Map.of(
                "id", u.getId(),
                "name", u.getName(),
                "email", u.getEmail()
            ));
            out.add(n);
        }
        return new ApiResponse<>(true, out);
    }
}



public class Functions {
    public static String publicFunction(String name) {
        
        return StringUtils.toTitle(name);
    }

    

    public static void main(String[] args) {
        PublicService svc = new PublicService();
        System.out.println(svc.getUser(1));
    }
}
