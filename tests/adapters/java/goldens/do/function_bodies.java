/**
 * Java module for testing function body optimization.
 */

package com.example.test;

import java.util.List;
import java.util.ArrayList;

public interface UserRepository {
    User findById(long id);
    User save(User user);
}

public class User {
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

public class Calculator {
    private final List<String> history;
    private final String name;

    public Calculator() {
        this("default");
    }

    public Calculator(String name) {
        this.name = name;
        this.history = new ArrayList<>();
    }

    public int add(int a, int b) {
        int result = a + b;
        history.add(String.format("add(%d, %d) = %d", a, b, result));
        System.out.println("Addition result: " + result);
        return result;
    }

    public int multiply(int a, int b) {
        int result = a * b;
        history.add(String.format("multiply(%d, %d) = %d", a, b, result));
        return result;
    }

    public List<String> getHistory() {
        return new ArrayList<>(history);
    }

    private boolean validateInput(int value) {
        if (!String.valueOf(value).matches("^-?\\d+$")) {
            throw new IllegalArgumentException("Input must be a number");
        }

        if (value == Integer.MAX_VALUE || value == Integer.MIN_VALUE) {
            throw new IllegalArgumentException("Input must be finite");
        }

        return true;
    }
}

public class ProcessingResult {
    private final List<User> valid;
    private final List<User> invalid;

    public ProcessingResult(List<User> valid, List<User> invalid) {
        this.valid = valid;
        this.invalid = invalid;
    }

    public List<User> getValid() { return valid; }
    public List<User> getInvalid() { return invalid; }
}

public class UserProcessor {
    public static ProcessingResult processUserData(List<User> users) {
        List<User> valid = new ArrayList<>();
        List<User> invalid = new ArrayList<>();

        for (User user : users) {
            if (user.getId() > 0 &&
                user.getName() != null && !user.getName().isEmpty() &&
                user.getEmail() != null && user.getEmail().contains("@")) {
                valid.add(user);
            } else {
                invalid.add(user);
            }
        }

        return new ProcessingResult(valid, invalid);
    }
}

// Generic function
public class ArrayProcessor {
    public static <T> List<T> processArray(List<T> items, Processor<T> processor) {
        List<T> result = new ArrayList<>();

        for (T item : items) {
            try {
                T processed = processor.process(item);
                result.add(processed);
            } catch (Exception error) {
                System.err.println("Processing failed for item: " + item);
            }
        }

        return result;
    }
}

@FunctionalInterface
interface Processor<T> {
    T process(T item) throws Exception;
}

// Default export function equivalent
public class Main {
    public static void main(String[] args) {
        Calculator calc = new Calculator("test");
        System.out.println(calc.add(2, 3));
        System.out.println(calc.multiply(4, 5));

        List<User> users = List.of(
            new User(1, "Alice", "alice@example.com"),
            new User(2, "Bob", "bob@example.com")
        );

        ProcessingResult processed = UserProcessor.processUserData(users);
        System.out.println("Valid: " + processed.getValid());
    }
}
