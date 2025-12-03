// Rust module for testing literal optimization.

use std::collections::HashMap;

// Short string literal (should be preserved)
const SHORT_MESSAGE: &str = "Hello, World!";

// Long string literal (candidate for trimming)
const LONG_MESSAGE: &str = "This is an extremely long message that contains a substantial amount of text content which might be considered…"; // literal string (−53 tokens)

// Multi-line string with formatting
const TEMPLATE_WITH_DATA: &str = r#"User Information:
- Name: {}
- Email: {}
- Registration Date:…"#; // literal string (−23 tokens)

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
            // …
            config
        }; // literal array (−444 tokens)

        let supported_languages = vec![
            "english",
            "spanish",
            "french",
            "…",
        ].into_iter().map(String::from).collect(); // literal array (−84 tokens)

        let allowed_extensions = vec![
            ".rs",
            ".py",
            ".js",
            "…",
        ].into_iter().map(String::from).collect(); // literal array (−58 tokens)

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
            "…",
        ].into_iter().map(String::from).collect(); // literal array (−140 tokens)

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
        r#"
SELECT
    users.id, users.username, users.email, users.created_at,
    prof…"# // literal string (−158 tokens)
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
        // …
        m
    };
} // literal object (−196 tokens)

lazy_static! {
    static ref ERROR_MESSAGES: HashMap<&'static str, &'static str> = {
        let mut m = HashMap::new();
        // …
        m
    };
} // literal object (−113 tokens)

fn main() {
    let manager = LiteralDataManager::new();
    let data = manager.process_data();

    println!("Tags: {:?}", data.tags);
    println!("Items count: {}", data.items.len());
    println!("{}", manager.get_long_query());
}
