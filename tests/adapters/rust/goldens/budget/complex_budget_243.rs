// … comment omitted

// … 8 imports omitted (10 lines)

// … 2 consts omitted (7 lines)

// … macro omitted (13 lines)

// … struct omitted (6 lines)

/// PublicService provides public API operations
pub struct PublicService {
    // … field omitted
}

impl PublicService {
    /// Creates a new service instance
    pub fn new() -> Self {
        Self {
            cache: HashMap::new(),
        }
    }

    /// GetUser is a public API method that gets a user by ID.
    /// This doc has multiple sentences to allow truncation under budget.
    pub fn get_user(&self, id: i32) -> Option<&User> {
        let id_str = id.to_string();
        self.cache.get(&id_str)
    }

    // … method omitted (6 lines)

    /// Process is a long method body to allow function body stripping
    pub fn process(&mut self, list: Vec<User>) -> Result<Vec<User>> {
        if list.is_empty() {
            return Err(anyhow::anyhow!("empty list"));
        }

        let mut out = Vec::new();
        for mut u in list {
            let normalized = self.normalize(&mut u);
            out.push(normalized.clone());
        }

        Ok(out)
    }
}

// … struct omitted (4 lines)

// … impl omitted (5 lines)

/// PublicFunction is an exported function
pub fn public_function(name: String) -> String {
    // … comment omitted
    to_title(&name)
}

// … 2 functions omitted (12 lines)
