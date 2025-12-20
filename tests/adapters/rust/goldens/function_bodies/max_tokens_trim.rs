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
    fn with_name(name: &str) -> Self // … method body omitted (3 lines)

    fn add(&mut self, a: i32, b: i32) -> i32 {
        let result = a + b;
    fn add(&mut self, a: i32, b: i32) -> i32 // … method body omitted (5 lines)

    fn multiply(&mut self, a: i32, b: i32) -> i32 {
        let result = a * b;
    fn multiply(&mut self, a: i32, b: i32) -> i32 // … method body omitted (4 lines)

    fn get_history(&self) -> Vec<String> {
        self.history.clone()
    }

    fn validate_input(&self, value: i32) -> bool {
        let value_str = value.to_string();

    fn validate_input(&self, value: i32) -> bool // … method body omitted (14 lines)
}

fn process_user_data(users: Vec<User>) -> ProcessingResult {
    let mut result = ProcessingResult {
        valid: Vec::new(),
fn process_user_data(users: Vec<User>) -> ProcessingResult // … function body omitted (13 lines)

fn process_array<T, F>(items: Vec<T>, processor: F) -> Vec<T>
where
    F: Fn(T) -> T,
{
    let mut result = Vec::new();

    for item in items {
// … function body omitted (6 lines)

fn filter_positive(numbers: Vec<i32>) -> Vec<i32> {
    numbers.into_iter().filter(|&n| n > 0).collect()
}

fn main() {
    let mut calc = Calculator::with_name("test");
fn main() // … function body omitted (19 lines)
