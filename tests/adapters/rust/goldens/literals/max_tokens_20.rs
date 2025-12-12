// Rust module for testing literal optimization.

use std::collections::HashMap;

// Short string literal (should be preserved)
const SHORT_MESSAGE: &str = "Hello, World!";

// Long string literal (candidate for trimming)
const LONG_MESSAGE: &str = "This is an extremely long message that contains a substantial amount of text content which might be considered…"; // literal string (−54 tokens)

// Multi-line string with formatting
const TEMPLATE_WITH_DATA: &str = r#"User Information:
- Name: {}
- Email: {}
- Registration Date:…"#; // literal string (−27 tokens)

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
            // … (9 more, −119 tokens)
            config.insert("database".to_string(), database);

            let mut cache = HashMap::new();
            cache.insert("redis_port".to_string(), json!(6379));
            // … (4 more, −56 tokens)
            config.insert("cache".to_string(), cache);

            let mut api = HashMap::new();
            api.insert("timeout".to_string(), json!(30000));
            // … (3 more, −42 tokens)
            config.insert("api".to_string(), api);

            let mut features = HashMap::new();
            features.insert("authentication".to_string(), json!(true));
            // … (6 more, −74 tokens)
            config.insert("features".to_string(), features);

            config
        };

        let supported_languages = vec![
            "english",
            "spanish",
            "french",
            "…"
        ] /* literal vec (−82 tokens) */.into_iter().map(String::from).collect();

        let allowed_extensions = vec![
            ".rs",
            ".py",
            ".js",
            ".ts",
            "…"
        ] /* literal vec (−56 tokens) */.into_iter().map(String::from).collect();

        Self {
            small_config,
            large_config,
            supported_languages,
            allowed_extensions,
        }
    }

    fn process_data(&self) -> DataContainer {
        let small_vec = vec!["one".to_string(), "two".to_string(), "three".to_string()];

        let large_vec = vec![
            "item_001",
            "item_002",
            "…"
        ] /* literal vec (−140 tokens) */.into_iter().map(String::from).collect();

        let mut metadata = HashMap::new();
        metadata.insert("type".to_string(), "test".to_string());
        // … (1 more, −14 tokens)

        DataContainer {
            tags: small_vec,
            items: large_vec,
            metadata,
            configuration: HashMap::new(),
        }
    }

    fn get_long_query(&self) -> &str {
        r#"
SELECT
    users.id, users.username, users.email, users.created_at,
    prof…"# // literal string (−162 tokens)
    }
}

// Module-level constants with different sizes
struct SmallConstants;
impl SmallConstants {
    const API_VERSION: &'static str = "v1";
    const DEFAULT_LIMIT: i32 = 50;
}

fn main() {
    let manager = LiteralDataManager::new();
    let data = manager.process_data();

    println!("Tags: {:?}", data.tags);
    println!("Items count: {}", data.items.len());
    println!("{}", manager.get_long_query());
}
