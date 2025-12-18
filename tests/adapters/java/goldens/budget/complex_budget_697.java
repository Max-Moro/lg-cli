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
    private final Map<String, User> cache = new HashMap<>();

    /**
     * Public API: gets a user by ID.
     * This doc has multiple sentences to allow truncation under budget.
     */
    public User getUser(long id) {
        return cache.get(String.valueOf(id));
    }

    
    private User normalize(Map<String, Object> u) 

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

class InternalOnly {
    
    public void doWork() { /* noop */ }
}

public class Functions {
    public static String publicFunction(String name) {
        
        return StringUtils.toTitle(name);
    }

    private static List<String> privateFunction(List<String> data) 

    public static void main(String[] args) {
        PublicService svc = new PublicService();
        System.out.println(svc.getUser(1));
    }
}


class User {
    private final long id;
    private final String name;
    private final String email;

    public User(long id, String name, String email) {
        this.id = id;
        this.name = name;
        this.email = email;
    }

    public long getId() { return id; }
    public String getName() { return name; }
    public String getEmail() { return email; }
}

class ApiResponse<T> {
    private final boolean success;
    private final T data;

    public ApiResponse(boolean success, T data) {
        this.success = success;
        this.data = data;
    }

    public boolean isSuccess() { return success; }
    public T getData() { return data; }
}

class StringUtils {
    public static String toTitle(String text) {
        if (text == null || text.isEmpty()) {
            return text;
        }
        return text.substring(0, 1).toUpperCase() + text.substring(1).toLowerCase();
    }
}
