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
        // … method body truncated (3 lines)
    }

    fn add(&mut self, a: i32, b: i32) -> i32 {
        let result = a + b;
        // … method body truncated (5 lines)
    }

    fn multiply(&mut self, a: i32, b: i32) -> i32 {
        let result = a * b;
        // … method body truncated (4 lines)
    }

    fn get_history(&self) -> Vec<String> {
        self.history.clone()
    }

    fn validate_input(&self, value: i32) -> bool {
        let value_str = value.to_string();

        // … method body truncated (14 lines)
    }
}

fn process_user_data(users: Vec<User>) -> ProcessingResult {
    let mut result = ProcessingResult {
        valid: Vec::new(),
    // … function body truncated (12 lines)
}

fn process_array<T, F>(items: Vec<T>, processor: F) -> Vec<T>
where
    F: Fn(T) -> T,
{
    let mut result = Vec::new();

    for item in items {
    // … function body truncated (5 lines)
}

fn filter_positive(numbers: Vec<i32>) -> Vec<i32> {
    numbers.into_iter().filter(|&n| n > 0).collect()
}

fn main() {
    let mut calc = Calculator::with_name("test");
    // … function body truncated (18 lines)
}
