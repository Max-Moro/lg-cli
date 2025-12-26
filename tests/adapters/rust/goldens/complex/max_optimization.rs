// … comment omitted
// … 3 imports omitted

// … comment omitted
// … 3 imports omitted (2 lines)

// … comment omitted
// … 2 imports omitted

/// Module level long documentation that might be truncated under tight budgets.
// … 2 consts omitted (4 lines)

// … macro omitted (13 lines)

// … struct omitted (6 lines)

/// PublicService provides public API operations.
pub struct PublicService {
    // … field omitted
}

impl PublicService {
    /// Creates a new service instance.
    pub fn new() -> Self {
        // … method body omitted (3 lines)
    }

    /// GetUser is a public API method that gets a user by ID.
    pub fn get_user(&self, id: i32) -> Option<&User> {
        // … method body omitted (2 lines)
    }

    /// normalize is a private helper — should not be visible with public_api_only.
    // … method omitted (5 lines)

    /// Process is a long method body to allow function body stripping.
    pub fn process(&mut self, list: Vec<User>) -> Result<Vec<User>> {
        // … method body omitted (9 lines)
    }
}

/// internalOnly is a private struct — should be filtered out in public_api_only.
// … struct omitted (3 lines)

// … impl omitted (5 lines)

/// PublicFunction is an exported function.
pub fn public_function(name: String) -> String {
    // … function body omitted (2 lines)
}

// … 2 functions omitted (12 lines)
