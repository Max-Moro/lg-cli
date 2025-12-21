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
        // … method body truncated (2 lines)
        return result;
    }

    public int multiply(int a, int b) {
        int result = a * b;
        // … method body truncated
        return result;
    }

    public List<String> getHistory() {
        return new ArrayList<>(history);
    }

    private boolean validateInput(int value) {
        if (!String.valueOf(value).matches("^-?\\d+$")) {
        // … method body truncated (5 lines)

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
        // … method body truncated (11 lines)

        return new ProcessingResult(valid, invalid);
    }
}

// Generic function
public class ArrayProcessor {
    public static <T> List<T> processArray(List<T> items, Processor<T> processor) {
        List<T> result = new ArrayList<>();

        // … method body truncated (8 lines)

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
        // … method body truncated (8 lines)
    }
}
