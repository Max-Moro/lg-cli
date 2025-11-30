// Rust module for testing public API filtering.

use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

// Public module-level constants (should be preserved)
pub const PUBLIC_VERSION: &str = "1.0.0";
pub const API_ENDPOINT: &str = "https://api.example.com";

// Private module-level constants (should be filtered out)
const PRIVATE_SECRET: &str = "internal-use-only";

lazy_static! {
    static ref INTERNAL_CONFIG: HashMap<&'static str, bool> = {
        let mut m = HashMap::new();
        m.insert("debug", true);
        m.insert("verbose", false);
        m
    };
}

// Public structure (should be preserved)
#[derive(Debug, Clone)]
pub struct User {
    pub id: i32,
    pub name: String,
    pub email: String,
    pub created_at: SystemTime,
}

// Private structure (should be filtered out)
struct InternalMetrics {
    process_time: i64,
    memory_usage: i64,
}

// Public enum (should be preserved)
#[derive(Debug, Clone, Copy)]
pub enum UserRole {
    Admin,
    User,
    Guest,
}

// Private enum (should be filtered out)
enum InternalEventType {
    UserCreated,
    UserUpdated,
    CacheCleared,
}

// Public struct with mixed visibility members
pub struct UserManager {
    // Public field
    pub version: String,
    pub is_initialized: bool,

    // Private fields (should be filtered out with public_api_only)
    internal_cache: HashMap<String, User>,
    metrics: InternalMetrics,
    api_endpoint: String,
}

impl UserManager {
    // Public constructor (should be preserved)
    pub fn new(api_endpoint: Option<&str>) -> Self {
        let api_endpoint = api_endpoint.unwrap_or(API_ENDPOINT).to_string();

        let mut manager = Self {
            version: PUBLIC_VERSION.to_string(),
            is_initialized: false,
            internal_cache: HashMap::new(),
            metrics: InternalMetrics {
                process_time: 0,
                memory_usage: 0,
            },
            api_endpoint,
        };

        manager.initialize();
        manager
    }

    // Public methods (should be preserved)
    pub fn create_user(&mut self, name: String, email: String) -> Result<User, String> {
        self.validate_user_data(&name, &email)?;

        let user = User {
            id: self.generate_id(),
            name,
            email: email.clone(),
            created_at: SystemTime::now(),
        };

        self.internal_cache.insert(email, user.clone());
        Ok(user)
    }

    pub fn get_user_by_id(&self, id: i32) -> Option<User> {
        for user in self.internal_cache.values() {
            if user.id == id {
                return Some(user.clone());
            }
        }

        self.fetch_user_from_api(id)
    }

    pub fn get_all_users(&self) -> Vec<User> {
        self.internal_cache.values().cloned().collect()
    }

    // Public static methods (should be preserved)
    pub fn validate_user_role(role: &str) -> bool {
        matches!(role, "admin" | "user" | "guest")
    }

    pub fn create_default_user() -> User {
        User {
            id: 0,
            name: "Default User".to_string(),
            email: "default@example.com".to_string(),
            created_at: SystemTime::now(),
        }
    }

    // Private methods (should be filtered out)
    fn validate_user_data(&self, name: &str, email: &str) -> Result<(), String> {
        if name.is_empty() || email.is_empty() {
            return Err("Name and email are required".to_string());
        }

        if !self.is_valid_email(email) {
            return Err("Invalid email format".to_string());
        }

        Ok(())
    }

    fn generate_id(&self) -> i32 {
        let duration = SystemTime::now().duration_since(UNIX_EPOCH).unwrap();
        (duration.as_secs() % 1_000_000) as i32
    }

    fn is_valid_email(&self, email: &str) -> bool {
        email.contains('@') && email.contains('.')
    }

    fn fetch_user_from_api(&self, id: i32) -> Option<User> {
        eprintln!("Fetching user {} from API", id);
        None
    }

    fn initialize(&mut self) {
        self.is_initialized = true;
    }

    fn log_error(&self, message: &str, error: &str) {
        eprintln!("[UserManager] {}: {}", message, error);
    }

    // Private static methods (should be filtered out)
    fn format_internal_id(id: i32) -> String {
        format!("internal_{:06}", id)
    }
}

// Private struct (should be filtered out)
struct InternalLogger {
    logs: Vec<String>,
}

impl InternalLogger {
    fn new() -> Self {
        Self { logs: Vec::new() }
    }

    fn log(&mut self, message: String) {
        self.logs.push(message);
    }

    fn get_logs(&self) -> &[String] {
        &self.logs
    }

    fn clear_logs(&mut self) {
        self.logs.clear();
    }
}

// Public trait (should be preserved)
pub trait BaseService {
    fn get_service_name(&self) -> &str;
    fn initialize(&mut self);

    fn get_service_info(&self) -> HashMap<String, String> {
        let mut info = HashMap::new();
        info.insert("name".to_string(), self.get_service_name().to_string());
        info.insert("version".to_string(), PUBLIC_VERSION.to_string());
        info
    }

    fn validate_config(&self, config: &HashMap<String, String>) -> bool;
}

// Public functions (should be preserved)
pub fn create_user_manager() -> UserManager {
    create_user_manager_with_endpoint(None)
}

pub fn create_user_manager_with_endpoint(endpoint: Option<&str>) -> UserManager {
    UserManager::new(endpoint)
}

pub fn is_valid_user_role(role: &str) -> bool {
    UserManager::validate_user_role(role)
}

// Private functions (should be filtered out)
fn log_internal_event(event: InternalEventType, data: Option<String>) {
    println!("[Internal] Event logged");
}

fn process_internal_metrics(metrics: &InternalMetrics) {
    println!("Processing metrics");
}

// Public utility struct (should be preserved)
pub struct UserUtils;

impl UserUtils {
    pub fn format_user_name(user: &User) -> String {
        format!("{} ({})", user.name, user.email)
    }

    pub fn get_user_age(user: &User) -> u64 {
        let now = SystemTime::now();
        let duration = now.duration_since(user.created_at).unwrap();
        duration.as_secs() / (60 * 60 * 24)
    }

    fn internal_formatting(text: &str) -> String {
        text.to_lowercase().replace(' ', "_")
    }
}

// Private utility struct (should be filtered out)
struct InternalUtils;

impl InternalUtils {
    fn debug_log(message: &str) {
        if *INTERNAL_CONFIG.get("debug").unwrap_or(&false) {
            println!("[Debug] {}", message);
        }
    }

    fn measure_performance<F, R>(f: F) -> R
    where
        F: FnOnce() -> R,
    {
        let start = SystemTime::now();
        let result = f();
        let elapsed = SystemTime::now().duration_since(start).unwrap();
        println!("Performance: {:?}", elapsed);
        result
    }
}

fn main() {
    let mut manager = UserManager::new(None);
    let user = manager.create_user("Test User".to_string(), "test@example.com".to_string()).unwrap();
    println!("Created user: {:?}", user);

    let formatted = UserUtils::format_user_name(&user);
    println!("{}", formatted);
}
