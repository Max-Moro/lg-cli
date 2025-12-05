// Rust module for testing literal optimization.

use std::collections::HashMap;

// Short string literal (should be preserved)
const SHORT_MESSAGE: &str = "Hello, World!";

// Long string literal (candidate for trimming)
const LONG_MESSAGE: &str = "This is an extremely long message that contains a substantial amount of text content which might be considered for trimming when optimizing Rust code for AI context windows. The message continues with detailed explanations and verbose descriptions that may not be essential for understanding the core functionality and structure of the code. This string literal spans multiple conceptual lines even though it's defined as a single string literal.";

// Multi-line string with formatting
const TEMPLATE_WITH_DATA: &str = r#"User Information:
- Name: {}
- Email: {}
- Registration Date: {}
- Account Status: {}
- Permissions: {:?}
- Last Login: {}
- Profile Completeness: {}%"#;

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
            "english", "spanish", "french", "german", "italian", "portuguese",
            "russian", "chinese", "japanese", "korean", "arabic", "hindi",
            "dutch", "swedish", "norwegian", "danish", "finnish", "polish",
            "czech", "hungarian", "romanian", "bulgarian", "croatian", "serbian",
        ].into_iter().map(String::from).collect();

        let allowed_extensions = vec![
            ".rs",
            ".py", ".js", ".ts", ".jsx", ".tsx",
            ".java", ".kt", ".scala",
            ".cpp", ".cxx", ".cc", ".c", ".h", ".hpp", ".hxx",
            ".cs", ".go",
            ".php", ".rb", ".swift", ".clj",
        ].into_iter().map(String::from).collect();

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
            "item_001", "item_002", "item_003", "item_004", "item_005",
            "item_006", "item_007", "item_008", "item_009", "item_010",
            "item_011", "item_012", "item_013", "item_014", "item_015",
            "item_016", "item_017", "item_018", "item_019", "item_020",
            "item_021", "item_022", "item_023", "item_024", "item_025",
            "item_026", "item_027", "item_028", "item_029", "item_030",
        ].into_iter().map(String::from).collect();

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
    profiles.first_name, profiles.last_name, profiles.bio, profiles.avatar_url,
    addresses.street, addresses.city, addresses.state, addresses.postal_code, addresses.country,
    subscriptions.plan_name, subscriptions.status, subscriptions.expires_at,
    payments.amount, payments.currency, payments.payment_date, payments.method
FROM users
LEFT JOIN profiles ON users.id = profiles.user_id
LEFT JOIN addresses ON users.id = addresses.user_id
LEFT JOIN subscriptions ON users.id = subscriptions.user_id
LEFT JOIN payments ON users.id = payments.user_id
WHERE users.is_active = true
    AND users.email_verified = true
    AND profiles.is_public = true
    AND subscriptions.status IN ('active', 'trial')
ORDER BY users.created_at DESC, subscriptions.expires_at ASC
LIMIT 100 OFFSET 0
        "#
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
