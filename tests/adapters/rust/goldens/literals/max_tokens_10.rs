// Rust module for testing literal optimization.

use std::collections::HashMap;

// Short string literal (should be preserved)
const SHORT_MESSAGE: &str = "Hello, World!";

// Long string literal (candidate for trimming)
const LONG_MESSAGE: &str = "This is an extremely long message that contains a…"; // literal string (−62 tokens)

// Multi-line string with formatting
const TEMPLATE_WITH_DATA: &str = "r#"User Information:
- Name:…"; // literal string (−32 tokens)

#[derive(Debug)]
struct DataContainer {
    // Small vec (should be preserved)
    tags: Vec<String>,

    // Large vec (candidate for trimming)
    items: Vec<String>,

    // Small map (should be preserved)
    metadata: HashMap<String, String>,

    // Large map (candidate for trimming)
    configuration: HashMap<String, HashMap<String, i32>>,
}

struct LiteralDataManager {
    // Small config (should be preserved)
    small_config: HashMap<String, bool>,

    // Large config (candidate for trimming)
    large_config: HashMap<String, HashMap<String, serde_json::Value>>,

    // Supported languages
    supported_languages: Vec<String>,

    // Allowed extensions
    allowed_extensions: Vec<String>,
}

impl LiteralDataManager {
    fn new() -> Self {
        let mut small_config = HashMap::new();
        small_config.insert("debug".to_string(), true);
        small_config.insert("version".to_string(), false);

        let large_config = {
            let mut config = HashMap::new();

            let mut database = HashMap::new();
            database.insert("host".to_string(), json!("localhost"));
            database.insert("port".to_string(), json!(5432));
            database.insert("name".to_string(), json!("application_db"));
            database.insert("ssl".to_string(), json!(false));
            database.insert("pool_min".to_string(), json!(2));
            database.insert("pool_max".to_string(), json!(10));
            database.insert("idle_timeout".to_string(), json!(30000));
            database.insert("connection_timeout".to_string(), json!(2000));
            database.insert("retry_attempts".to_string(), json!(3));
            database.insert("retry_delay".to_string(), json!(1000));
            config.insert("database".to_string(), database);

            let mut cache = HashMap::new();
            cache.insert("redis_port".to_string(), json!(6379));
            cache.insert("redis_db".to_string(), json!(0));
            cache.insert("redis_ttl".to_string(), json!(3600));
            cache.insert("memory_max_size".to_string(), json!(1000));
            cache.insert("memory_ttl".to_string(), json!(1800));
            config.insert("cache".to_string(), cache);

            let mut api = HashMap::new();
            api.insert("timeout".to_string(), json!(30000));
            api.insert("retries".to_string(), json!(3));
            api.insert("rate_limit_requests".to_string(), json!(100));
            api.insert("rate_limit_window".to_string(), json!(60000));
            config.insert("api".to_string(), api);

            let mut features = HashMap::new();
            features.insert("authentication".to_string(), json!(true));
            features.insert("authorization".to_string(), json!(true));
            features.insert("logging".to_string(), json!(true));
            features.insert("monitoring".to_string(), json!(true));
            features.insert("analytics".to_string(), json!(false));
            features.insert("caching".to_string(), json!(true));
            features.insert("compression".to_string(), json!(true));
            config.insert("features".to_string(), features);

            config
        };

        let supported_languages = vec![
            "english",
            "spanish",
            "…",
        ].into_iter().map(String::from).collect(); // literal array (−89 tokens)

        let allowed_extensions = vec![
            ".rs",
            ".py",
            "…",
        ].into_iter().map(String::from).collect(); // literal array (−62 tokens)

        Self {
            small_config,
            large_config,
            supported_languages,
            allowed_extensions,
        }
    }

    fn process_data(&self) -> DataContainer {
        let small_vec = vec!["one".to_string(), "…"]; // literal array (−9 tokens)

        let large_vec = vec![
            "item_001",
            "…",
        ].into_iter().map(String::from).collect(); // literal array (−146 tokens)

        let mut metadata = HashMap::new();
        metadata.insert("type".to_string(), "test".to_string());
        metadata.insert("count".to_string(), "3".to_string());

        DataContainer {
            tags: small_vec,
            items: large_vec,
            metadata,
            configuration: HashMap::new(),
        }
    }

    fn get_long_query(&self) -> &str {
        "r#"
SELECT
    users.id, users.usernam…" // literal string (−167 tokens)
    }
}

// Module-level constants with different sizes
struct SmallConstants;
impl SmallConstants {
    const API_VERSION: &'static str = "v1";
    const DEFAULT_LIMIT: i32 = 50;
}

lazy_static! {
    static ref HTTP_STATUS_CODES: HashMap<&'static str, i32> = {
        let mut m = HashMap::new();
        m.insert("CONTINUE", 100);
        m.insert("SWITCHING_PROTOCOLS", 101);
        m.insert("OK", 200);
        m.insert("CREATED", 201);
        m.insert("ACCEPTED", 202);
        m.insert("NO_CONTENT", 204);
        m.insert("MOVED_PERMANENTLY", 301);
        m.insert("FOUND", 302);
        m.insert("NOT_MODIFIED", 304);
        m.insert("BAD_REQUEST", 400);
        m.insert("UNAUTHORIZED", 401);
        m.insert("FORBIDDEN", 403);
        m.insert("NOT_FOUND", 404);
        m.insert("METHOD_NOT_ALLOWED", 405);
        m.insert("CONFLICT", 409);
        m.insert("INTERNAL_SERVER_ERROR", 500);
        m.insert("NOT_IMPLEMENTED", 501);
        m.insert("BAD_GATEWAY", 502);
        m.insert("SERVICE_UNAVAILABLE", 503);
        m
    };
}

lazy_static! {
    static ref ERROR_MESSAGES: HashMap<&'static str, &'static str> = {
        let mut m = HashMap::new();
        m.insert("VALIDATION_FAILED", "Input validation failed. Please check you…") // literal string (−4 tokens);
        m.insert("AUTHENTICATION_REQUIRED", "Authentication is required to access this resource.");
        m.insert("AUTHORIZATION_FAILED", "You do not have permission to perform this action.");
        m.insert("RESOURCE_NOT_FOUND", "The requested resource could not be foun…") // literal string (−2 tokens);
        m.insert("INTERNAL_ERROR", "An internal server error occurred. Please…") // literal string (−3 tokens);
        m.insert("RATE_LIMIT_EXCEEDED", "Rate limit exceeded. Please wait before makin…") // literal string (−1 tokens);
        m
    };
}

fn main() {
    let manager = LiteralDataManager::new();
    let data = manager.process_data();

    println!("Tags: {:?}", data.tags);
    println!("Items count: {}", data.items.len());
    println!("{}", manager.get_long_query());
}
