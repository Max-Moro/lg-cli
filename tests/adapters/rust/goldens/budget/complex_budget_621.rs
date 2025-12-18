


// Third-party imports





/// Module level long documentation that might be truncated under tight budgets.
/// The text includes several sentences to ensure the comment optimizer has
/// something to work with when switching to keep_first_sentence mode.
const MODULE_TITLE: &str = "Budget System Complex Sample";

const LONG_TEXT: &str = r#"This is an extremely long text that is designed to be trimmed
by the literal optimizer when budgets are small. It repeats a message to…"#;

lazy_static! {
    static ref BIG_ARRAY: Vec<UserData> = {
        let mut users = Vec::new();
        for i in 1..=50 {
            users.push(UserData {
                id: i,
                name: format!("User {}", i),
                active: i % 2 == 0,
            });
        }
        users
    };
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct UserData {
    id: i32,
    name: String,
    active: bool,
}

/// PublicService provides public API operations
pub struct PublicService {
    cache: HashMap<String, User>,
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

    /// normalize is a private helper — should not be visible with public_api_only
    fn normalize(&self, u: &mut User) -> &User {
        u.name = u.name.trim().to_string();
        u.email = u.email.to_lowercase();
        u
    }

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

/// internalOnly is a private struct — should be filtered out in public_api_only
struct InternalOnly {
    data: String,
}

impl InternalOnly {
    fn do_work(&self) {
        // noop
    }
}

/// PublicFunction is an exported function
pub fn public_function(name: String) -> String {
    
    to_title(&name)
}

fn private_function(data: Vec<String>) -> Vec<String> {
    
    data.into_iter()
        .map(|s| s.trim().to_string())
        .collect()
}

fn main() {
    let mut svc = PublicService::new();
    if let Some(user) = svc.get_user(1) {
        println!("{:?}", user);
    }
}
