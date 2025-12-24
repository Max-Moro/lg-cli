"""
Tests for public API filtering in Rust adapter.
"""

from lg.adapters.langs.rust import RustCfg
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestRustPublicApiOptimization:
    """Test public API filtering for Rust code."""

    def test_public_api_only_basic(self, do_public_api):
        """Test basic public API filtering."""
        adapter = make_adapter(RustCfg(public_api_only=True))

        result, meta = adapter.process(lctx(do_public_api))

        assert meta.get("rust.removed.function", 0) > 0

        assert "pub struct UserManager" in result
        assert "pub fn create_user" in result

        assert "fn validate_user_data" not in result
        assert "fn generate_id" not in result

        assert_golden_match(result, "public_api", "basic", language="rust")

    def test_pub_vs_private(self):
        """Test distinction between pub and private items."""
        code = '''pub fn public_function(x: i32) -> i32 {
    helper(x)
}

fn helper(x: i32) -> i32 {
    x * 2
}

pub struct User {
    pub id: i32,
    pub name: String,
    email: String,
}

struct InternalData {
    secret: String,
}
'''

        adapter = make_adapter(RustCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "pub fn public_function(x: i32) -> i32" in result
        assert "pub struct User" in result
        assert "pub id: i32" in result

        assert "fn helper" not in result
        assert "struct InternalData" not in result

    def test_pub_crate_and_pub_super(self):
        """Test handling of pub(crate) and pub(super)."""
        code = '''pub fn public_function() {}

pub(crate) fn crate_public_function() {}

pub(super) fn super_public_function() {}

fn private_function() {}
'''

        adapter = make_adapter(RustCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "pub fn public_function()" in result
        assert "pub(crate) fn crate_public_function()" in result
        assert "pub(super) fn super_public_function()" in result

        assert "fn private_function()" not in result

    def test_impl_methods_visibility(self):
        """Test filtering of impl block methods by visibility."""
        code = '''pub struct Service {
    cache: HashMap<String, Data>,
}

impl Service {
    pub fn new() -> Self {
        Self {
            cache: HashMap::new(),
        }
    }

    pub fn get_value(&self, key: &str) -> Option<&Data> {
        self.cache.get(key)
    }

    fn invalidate(&mut self) {
        self.cache.clear();
    }
}
'''

        adapter = make_adapter(RustCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "pub fn new() -> Self" in result
        assert "pub fn get_value(&self, key: &str) -> Option<&Data>" in result

        assert "fn invalidate" not in result

    def test_trait_definitions(self):
        """Test that trait definitions are preserved."""
        code = '''pub trait Reader {
    fn read(&mut self, buf: &mut [u8]) -> io::Result<usize>;
    fn close(&mut self) -> io::Result<()>;
}

trait Writer {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize>;
}
'''

        adapter = make_adapter(RustCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "pub trait Reader" in result
        assert "fn read(&mut self, buf: &mut [u8]) -> io::Result<usize>" in result

        assert "trait Writer" not in result

    def test_struct_fields_visibility(self):
        """Test filtering of struct fields by visibility."""
        code = '''pub struct Config {
    pub timeout: i32,
    pub retries: i32,
    debug: bool,
    verbose: bool,
}
'''

        adapter = make_adapter(RustCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "pub timeout: i32" in result
        assert "pub retries: i32" in result

    def test_module_level_items(self):
        """Test filtering of module-level items."""
        code = '''pub const PUBLIC_VERSION: &str = "1.0.0";

const PRIVATE_SECRET: &str = "internal-use-only";

pub static PUBLIC_COUNTER: AtomicI32 = AtomicI32::new(0);

static PRIVATE_CONFIG: Lazy<Config> = Lazy::new(|| Config::default());
'''

        adapter = make_adapter(RustCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert 'pub const PUBLIC_VERSION: &str = "1.0.0";' in result
        assert "pub static PUBLIC_COUNTER: AtomicI32" in result

        assert "const PRIVATE_SECRET" not in result
        assert "static PRIVATE_CONFIG" not in result


class TestRustPublicApiEdgeCases:
    """Test edge cases for Rust public API filtering."""

    def test_type_aliases(self):
        """Test handling of type aliases."""
        code = '''pub type UserId = i32;

type InternalId = String;
'''

        adapter = make_adapter(RustCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "pub type UserId = i32;" in result
        assert "type InternalId" not in result

    def test_enum_visibility(self):
        """Test handling of enum visibility."""
        code = '''pub enum UserRole {
    Admin,
    User,
    Guest,
}

enum InternalEventType {
    UserCreated,
    UserUpdated,
}
'''

        adapter = make_adapter(RustCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "pub enum UserRole" in result
        assert "Admin" in result

        assert "enum InternalEventType" not in result

    def test_trait_implementations(self):
        """Test handling of trait implementations."""
        code = '''impl Display for User {
    fn fmt(&self, f: &mut Formatter) -> fmt::Result {
        write!(f, "{} ({})", self.name, self.email)
    }
}

impl From<UserData> for User {
    fn from(data: UserData) -> Self {
        Self {
            id: data.id,
            name: data.name,
            email: data.email,
        }
    }
}
'''

        adapter = make_adapter(RustCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "impl Display for User" in result
        assert "fn fmt(&self, f: &mut Formatter) -> fmt::Result" in result
        assert "impl From<UserData> for User" in result

    def test_generic_types_visibility(self):
        """Test visibility of generic types."""
        code = '''pub struct Container<T> {
    pub items: Vec<T>,
    capacity: usize,
}

struct InternalContainer<T> {
    data: Vec<T>,
}
'''

        adapter = make_adapter(RustCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "pub struct Container<T>" in result
        assert "pub items: Vec<T>" in result

        assert "struct InternalContainer" not in result
