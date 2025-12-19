"""
Tests for function body optimization in Java adapter.
"""

from lg.adapters.java import JavaCfg
from lg.adapters.code_model import FunctionBodyConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestJavaFunctionBodyOptimization:
    """Test function body stripping for Java code."""

    def test_basic_function_stripping(self, do_function_bodies):
        """Test basic function body stripping."""
        adapter = make_adapter(JavaCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(do_function_bodies))

        assert meta.get("java.removed.method_body", 0) > 0
        assert "// … method body omitted" in result

        assert_golden_match(result, "function_bodies", "basic_strip")

    def test_max_tokens_trimming(self, do_function_bodies):
        """Test trimming method bodies to token budget."""
        adapter = make_adapter(JavaCfg(
            strip_function_bodies=FunctionBodyConfig(
                policy="keep_all",
                max_tokens=20
            )
        ))

        result, meta = adapter.process(lctx(do_function_bodies))

        assert_golden_match(result, "function_bodies", "max_tokens_trim")

    def test_class_method_preservation(self):
        """Test that class structure is preserved while stripping method bodies."""
        class_code = '''
public class Calculator {
    private List<String> history = new ArrayList<>();

    public Calculator(String name) {
        this.name = name;
        this.history = new ArrayList<>();
    }

    public int add(int a, int b) {
        int result = a + b;
        history.add(String.format("%d + %d = %d", a, b, result));
        return result;
    }

    public List<String> getHistory() {
        return new ArrayList<>(history);
    }
}
'''

        adapter = make_adapter(JavaCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(class_code))

        assert "public class Calculator {" in result
        assert "private List<String> history = new ArrayList<>();" in result
        assert "public int add(int a, int b)" in result
        assert "public List<String> getHistory()" in result

        assert_golden_match(result, "function_bodies", "class_methods")

    def test_no_stripping_preserves_original(self):
        """Test that disabling stripping preserves original code."""
        code = "public static int test() { return 42; }"

        adapter = make_adapter(JavaCfg(strip_function_bodies=False))

        result, meta = adapter.process(lctx(code))

        assert "return 42;" in result
        assert meta.get("java.removed.method_body", 0) == 0

    def test_keep_public_policy(self):
        """Test keep_public policy - strips private, keeps public."""
        code = '''public class Calculator {
    public int add(int a, int b) {
        int result = a + b;
        System.out.println("Adding " + a + ", " + b);
        return result;
    }

    private int multiply(int a, int b) {
        int result = a * b;
        System.out.println("Multiplying " + a + ", " + b);
        return result;
    }
}
'''

        adapter = make_adapter(JavaCfg(
            strip_function_bodies=FunctionBodyConfig(policy="keep_public")
        ))

        result, meta = adapter.process(lctx(code))

        # Public method body should be preserved
        assert "public int add(int a, int b)" in result
        assert "int result = a + b;" in result

        # Private method body should be stripped
        assert "private int multiply(int a, int b)" in result
        assert "// … method body omitted" in result



class TestJavaFunctionBodyEdgeCases:
    """Test edge cases for Java function body optimization."""

    def test_single_line_methods(self):
        """Test that single-line methods are handled correctly."""
        code = '''public int simple() { return 42; }

public int complex() {
    int x = 1;
    int y = 2;
    return x + y;
}
'''

        adapter = make_adapter(JavaCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "public int simple() { return 42; }" in result

        assert "public int complex()" in result
        assert "// … method body omitted" in result
        assert "int x = 1;" not in result

    def test_interface_and_abstract_preservation(self):
        """Test that interfaces and abstract classes are preserved."""
        code = '''public interface UserRepository {
    User findById(long id);
    User save(User user);
}

public abstract class BaseService {
    protected abstract String getServiceName();
    public abstract void initialize();
}

public class UserService {
    public User processUser(User user) {
        return user;
    }
}
'''

        adapter = make_adapter(JavaCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "public interface UserRepository" in result
        assert "User findById(long id);" in result
        assert "public abstract class BaseService" in result

        assert "public User processUser(User user)" in result
        assert "// … method body omitted" in result


class TestJavaDocPreservation:
    """Test preservation of Javadoc when stripping function bodies."""

    def test_method_with_javadoc_preserved(self):
        """Test that method Javadoc is preserved when bodies are stripped."""
        code = '''public class Calculator {
    /**
     * Multiply two numbers together.
     *
     * This method performs multiplication operation.
     *
     * @param a First number
     * @param b Second number
     * @return Product of a and b
     */
    public int multiply(int a, int b) {
        int temp = a * b;
        history.add(String.format("multiply(%d, %d) = %d", a, b, temp));
        return temp;
    }
}
'''

        adapter = make_adapter(JavaCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "public int multiply(int a, int b)" in result

        assert "/**" in result and "Multiply two numbers together" in result
        assert "@param a First number" in result
        assert "@return Product of a and b" in result

        assert "int temp = a * b;" not in result
        assert "history.add" not in result

        assert "// … method body omitted" in result
