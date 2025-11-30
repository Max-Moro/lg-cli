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
    fn new() -> Self // … method body omitted (3 lines)

    fn with_name(name: &str) -> Self // … method body omitted (6 lines)

    fn add(&mut self, a: i32, b: i32) -> i32 // … method body omitted (7 lines)

    fn multiply(&mut self, a: i32, b: i32) -> i32 // … method body omitted (6 lines)

    fn get_history(&self) -> Vec<String> // … method body omitted (3 lines)

    fn validate_input(&self, value: i32) -> bool // … method body omitted (17 lines)
}

fn process_user_data(users: Vec<User>) -> ProcessingResult // … function body omitted (16 lines)

fn process_array<T, F>(items: Vec<T>, processor: F) -> Vec<T>
where
    F: Fn(T) -> T,
// … function body omitted (10 lines)

fn filter_positive(numbers: Vec<i32>) -> Vec<i32> // … function body omitted (3 lines)

fn main() // … function body omitted (21 lines)
