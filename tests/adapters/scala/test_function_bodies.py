"""
Tests for function body optimization in Scala adapter.
"""

from lg.adapters.langs.scala import ScalaCfg
from lg.adapters.code_model import FunctionBodyConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestScalaFunctionBodyOptimization:
    """Test function body stripping for Scala code."""

    def test_basic_function_stripping(self, do_function_bodies):
        """Test basic function body stripping."""
        adapter = make_adapter(ScalaCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(do_function_bodies))

        assert meta.get("scala.removed.function_body", 0) > 0
        assert meta.get("scala.removed.method_body", 0) > 0
        assert "// … method body omitted" in result
        assert "// … function body omitted" in result

        assert_golden_match(result, "function_bodies", "basic_strip")

    def test_max_tokens_trimming(self, do_function_bodies):
        """Test trimming function bodies to token budget."""
        adapter = make_adapter(ScalaCfg(
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
class Calculator(val name: String) {
  private val history = scala.collection.mutable.ListBuffer.empty[String]

  def add(a: Int, b: Int): Int = {
    val result = a + b
    history += s"$a + $b = $result"
    result
  }

  def getHistory: List[String] = history.toList
}
'''

        adapter = make_adapter(ScalaCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(class_code))

        assert "class Calculator" in result
        assert "private val history" in result

        assert "def add(a: Int, b: Int): Int" in result
        assert "def getHistory: List[String]" in result

        assert_golden_match(result, "function_bodies", "class_methods")

    def test_no_stripping_preserves_original(self):
        """Test that disabling stripping preserves original code."""
        code = "def test(): Int = { 42 }"

        adapter = make_adapter(ScalaCfg(strip_function_bodies=False))

        result, meta = adapter.process(lctx(code))

        assert "42" in result
        assert meta.get("scala.removed.function_body", 0) == 0
        assert meta.get("scala.removed.method_bodies", 0) == 0

    def test_keep_public_policy(self):
        """Test keep_public policy - strips private, keeps public."""
        code = '''def publicFunction(): Int = {
    val x = 1
    val y = 2
    x + y
}

private def privateFunction(): Int = {
    val a = 10
    val b = 20
    a * b
}
'''

        adapter = make_adapter(ScalaCfg(
            strip_function_bodies=FunctionBodyConfig(policy="keep_public")
        ))

        result, meta = adapter.process(lctx(code))

        # Public function body should be preserved
        assert "def publicFunction()" in result
        assert "val x = 1" in result

        # Private function body should be stripped
        assert "private def privateFunction()" in result
        assert "// … function body omitted" in result



class TestScalaFunctionBodyEdgeCases:
    """Test edge cases for Scala function body optimization."""

    def test_single_expression_methods(self):
        """Test that single-expression methods are handled correctly."""
        code = '''def simple() = 42

def complex(): Int = {
  val x = 1
  val y = 2
  x + y
}
'''

        adapter = make_adapter(ScalaCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "def simple() = 42" in result

        assert "def complex(): Int" in result
        assert "// … function body omitted" in result
        assert "val x = 1" not in result

    def test_case_class_and_trait_preservation(self):
        """Test that case classes and traits are preserved."""
        code = '''case class User(
  id: Long,
  name: String
)

trait UserRepository {
  def findById(id: Long): Option[User]
  def save(user: User): User
}

def processUser(user: User): User = {
  val updatedName = user.name.toUpperCase
  user.copy(name = updatedName)
}
'''

        adapter = make_adapter(ScalaCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "case class User" in result
        assert "trait UserRepository" in result
        assert "id: Long" in result
        assert "name: String" in result

        assert "def processUser(user: User): User" in result
        assert "// … function body omitted" in result
        assert "val updatedName" not in result

    def test_pattern_matching_preservation(self):
        """Test handling of pattern matching in functions."""
        code = '''def processValue(value: Any): String = value match {
  case s: String => s.toUpperCase
  case i: Int => i.toString
  case _ => "unknown"
}
'''

        adapter = make_adapter(ScalaCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "def processValue(value: Any): String" in result
        assert "// … function body omitted" in result
        assert "case s: String" not in result


class TestScalaDocstringPreservation:
    """Test preservation of Scaladoc when stripping function bodies."""

    def test_method_with_scaladoc_preserved(self):
        """Test that method Scaladoc is preserved when bodies are stripped."""
        code = '''class Calculator {
  /**
   * Multiply two numbers together.
   *
   * This method performs multiplication operation.
   */
  def multiply(a: Int, b: Int): Int = {
    val temp = a * b
    history += s"multiply($a, $b) = $temp"
    temp
  }
}
'''

        adapter = make_adapter(ScalaCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "def multiply(a: Int, b: Int): Int" in result

        assert "/**" in result and "Multiply two numbers together" in result
        assert "This method performs multiplication operation" in result

        assert "val temp = a * b" not in result
        assert "history +=" not in result

        assert "// … method body omitted" in result
