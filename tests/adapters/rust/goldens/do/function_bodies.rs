// Rust module for testing function body optimization.

use std::collections::HashMap;

#[derive(Debug, Clone)]
struct User {
    id: i32,
    name: String,
    email: String,
}

#[derive(Debug)]
struct ProcessingResult {
    valid: Vec<User>,
    invalid: Vec<User>,
}

struct Calculator {
    name: String,
    history: Vec<String>,
}

impl Calculator {
    fn new() -> Self {
        Self::with_name("default")
    }

    fn with_name(name: &str) -> Self {
        Self {
            name: name.to_string(),
            history: Vec::with_capacity(10),
        }
    }

    fn add(&mut self, a: i32, b: i32) -> i32 {
        let result = a + b;
        let entry = format!("add({}, {}) = {}", a, b, result);
        self.history.push(entry);
        println!("Addition result: {}", result);
        result
    }

    fn multiply(&mut self, a: i32, b: i32) -> i32 {
        let result = a * b;
        let entry = format!("multiply({}, {}) = {}", a, b, result);
        self.history.push(entry);
        result
    }

    fn get_history(&self) -> Vec<String> {
        self.history.clone()
    }

    fn validate_input(&self, value: i32) -> bool {
        let value_str = value.to_string();

        for ch in value_str.chars() {
            if ch != '-' && !ch.is_ascii_digit() {
                eprintln!("Input must be a number");
                return false;
            }
        }

        if value == i32::MAX || value == i32::MIN {
            eprintln!("Input must be finite");
            return false;
        }

        true
    }
}

fn process_user_data(users: Vec<User>) -> ProcessingResult {
    let mut result = ProcessingResult {
        valid: Vec::new(),
        invalid: Vec::new(),
    };

    for user in users {
        if user.id > 0 && !user.name.is_empty() && user.email.contains('@') {
            result.valid.push(user);
        } else {
            result.invalid.push(user);
        }
    }

    result
}

fn process_array<T, F>(items: Vec<T>, processor: F) -> Vec<T>
where
    F: Fn(T) -> T,
{
    let mut result = Vec::new();

    for item in items {
        let processed = processor(item);
        result.push(processed);
    }

    result
}

fn filter_positive(numbers: Vec<i32>) -> Vec<i32> {
    numbers.into_iter().filter(|&n| n > 0).collect()
}

fn main() {
    let mut calc = Calculator::with_name("test");
    println!("{}", calc.add(2, 3));
    println!("{}", calc.multiply(4, 5));

    let users = vec![
        User {
            id: 1,
            name: "Alice".to_string(),
            email: "alice@example.com".to_string(),
        },
        User {
            id: 2,
            name: "Bob".to_string(),
            email: "bob@example.com".to_string(),
        },
    ];

    let processed = process_user_data(users);
    println!("Valid users: {}", processed.valid.len());
}
