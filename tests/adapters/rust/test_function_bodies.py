"""
Tests for function body optimization in Rust adapter.
"""

from lg.adapters.rust import RustCfg
from lg.adapters.code_model import FunctionBodyConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestRustFunctionBodyOptimization:
    """Test function body stripping for Rust code."""

    def test_basic_function_stripping(self, do_function_bodies):
        """Test basic function body stripping."""
        adapter = make_adapter(RustCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(do_function_bodies))

        assert meta.get("rust.removed.function_body", 0) > 0
        assert "// … function body omitted" in result

        assert_golden_match(result, "function_bodies", "basic_strip", language="rust")

    def test_max_tokens_trimming(self, do_function_bodies):
        """Test trimming function bodies to token budget."""
        adapter = make_adapter(RustCfg(
            strip_function_bodies=FunctionBodyConfig(
                policy="keep_all",
                max_tokens=20
            )
        ))

        result, meta = adapter.process(lctx(do_function_bodies))

        assert_golden_match(result, "function_bodies", "max_tokens_trim", language="rust")

    def test_impl_method_handling(self):
        """Test handling of impl block methods."""
        code = '''impl Calculator {
    pub fn new() -> Self {
        Self {
            value: 0,
            history: Vec::new(),
        }
    }

    pub fn add(&mut self, x: i32) -> i32 {
        self.value += x;
        self.history.push(format!("add({})", x));
        self.value
    }

    fn get(&self) -> i32 {
        self.value
    }
}
'''

        adapter = make_adapter(RustCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "pub fn new() -> Self" in result
        assert "pub fn add(&mut self, x: i32) -> i32" in result
        assert "fn get(&self) -> i32" in result
        assert "// … method body omitted" in result

        assert_golden_match(result, "function_bodies", "impl_methods", language="rust")

    def test_no_stripping_preserves_original(self):
        """Test that disabling stripping preserves original code."""
        code = "fn test() -> i32 { 42 }"

        adapter = make_adapter(RustCfg(strip_function_bodies=False))

        result, meta = adapter.process(lctx(code))

        assert "42" in result
        assert meta.get("rust.removed.function_body", 0) == 0


class TestRustFunctionBodyEdgeCases:
    """Test edge cases for Rust function body optimization."""

    def test_single_expression_functions(self):
        """Test that single-expression functions are handled correctly."""
        code = '''fn simple() -> i32 { 42 }

fn complex() -> i32 {
    let x = 1;
    let y = 2;
    x + y
}
'''

        adapter = make_adapter(RustCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "fn simple() -> i32 { 42 }" in result

        assert "fn complex() -> i32" in result
        assert "// … function body omitted" in result
        assert "let x = 1;" not in result

    def test_generic_functions(self):
        """Test handling of generic functions."""
        code = '''fn max<T: Ord>(a: T, b: T) -> T {
    if a > b { a } else { b }
}

fn process<T, F>(items: Vec<T>, f: F) -> Vec<T>
where
    F: Fn(T) -> T,
{
    items.into_iter().map(f).collect()
}
'''

        adapter = make_adapter(RustCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "fn max<T: Ord>(a: T, b: T) -> T" in result
        assert "fn process<T, F>(items: Vec<T>, f: F) -> Vec<T>" in result

    def test_async_functions(self):
        """Test handling of async functions."""
        code = '''async fn fetch_data(url: &str) -> Result<String, Error> {
    let response = reqwest::get(url).await?;
    let text = response.text().await?;
    Ok(text)
}

impl Service {
    pub async fn process(&self, id: i32) -> Result<Data, Error> {
        let data = self.fetch(id).await?;
        self.validate(data).await
    }
}
'''

        adapter = make_adapter(RustCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "async fn fetch_data(url: &str) -> Result<String, Error>" in result
        assert "pub async fn process(&self, id: i32) -> Result<Data, Error>" in result

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

        adapter = make_adapter(RustCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "impl Display for User" in result
        assert "fn fmt(&self, f: &mut Formatter) -> fmt::Result" in result
        assert "impl From<UserData> for User" in result

    def test_const_fn(self):
        """Test handling of const fn."""
        code = '''const fn factorial(n: u32) -> u32 {
    match n {
        0 | 1 => 1,
        _ => n * factorial(n - 1),
    }
}

impl Constants {
    pub const MAX_SIZE: usize = 100;

    pub const fn compute() -> usize {
        Self::MAX_SIZE * 2
    }
}
'''

        adapter = make_adapter(RustCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "const fn factorial(n: u32) -> u32" in result
        assert "pub const fn compute() -> usize" in result

    def test_closures(self):
        """Test handling of closures."""
        code = '''fn process() {
    let double = |x: i32| x * 2;

    let result: Vec<_> = vec![1, 2, 3]
        .into_iter()
        .map(|x| x * 2)
        .collect();
}
'''

        adapter = make_adapter(RustCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "fn process()" in result
