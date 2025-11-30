"""
Tests for public API filtering in Scala adapter.
"""

from lg.adapters.scala import ScalaCfg
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestScalaPublicApiOptimization:
    """Test public API filtering for Scala code."""

    def test_public_api_only_basic(self, do_public_api):
        """Test basic public API filtering."""
        adapter = make_adapter(ScalaCfg(public_api_only=True))

        result, meta = adapter.process(lctx(do_public_api))

        assert meta.get("scala.removed.method", 0) > 0
        assert meta.get("scala.removed.function", 0) > 0
        assert meta.get("scala.removed.class", 0) > 0

        assert "class UserManager" in result
        assert "def createUserManager" in result

        assert "private val internalCache" not in result
        assert "private def validateUserData" not in result
        assert "private class InternalLogger" not in result

        assert_golden_match(result, "public_api", "basic")

    def test_visibility_detection(self):
        """Test detection of public/private elements."""
        code = '''
class PublicClass {
  def publicMethod(): Unit = {}
  private def privateMethod(): Unit = {}
}

private class PrivateClass {
  def method(): Unit = {}
}

trait PublicTrait {
  def method(): Unit
}

private trait PrivateTrait {
  def method(): Unit
}

val PUBLIC_CONSTANT = "value"
private val PRIVATE_CONSTANT = "value"
'''

        adapter = make_adapter(ScalaCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "class PublicClass" in result
        assert "def publicMethod" in result
        assert "trait PublicTrait" in result
        assert "PUBLIC_CONSTANT" in result

        assert "private def privateMethod" not in result
        assert "private class PrivateClass" not in result
        assert "PRIVATE_CONSTANT" not in result

    def test_case_class_and_companion_objects(self):
        """Test case classes and companion objects in public API."""
        code = '''
case class User(
  id: Long,
  name: String,
  private val internalData: String
)

object UserCompanion {
  def create(): User = User(0, "", "")
  private def internalCreate(): User = User(0, "", "")
}

private case class InternalData(value: String)
'''

        adapter = make_adapter(ScalaCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "case class User" in result

        assert "object UserCompanion" in result
        assert "def create()" in result

        assert "InternalData" not in result

    def test_annotation_handling(self):
        """Test handling of annotations in public API mode."""
        code = '''
class Logged extends scala.annotation.StaticAnnotation

@Logged
class PublicClass {
  @Logged
  def publicMethod(): Unit = {}

  @Logged
  private def privateMethod(): Unit = {}
}

@Logged
private class PrivateClass {
  def method(): Unit = {}
}
'''

        adapter = make_adapter(ScalaCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "@Logged" in result
        assert "class PublicClass" in result

        assert "PrivateClass" not in result

    def test_class_member_visibility(self):
        """Test class member visibility in public API."""
        code = '''
class PublicClass {
  val publicField = "public"
  def publicMethod(): Unit = {}

  protected val protectedField = "protected"
  protected def protectedMethod(): Unit = {}

  private val privateField = "private"
  private def privateMethod(): Unit = {}
}

private class PrivateClass {
  def method(): Unit = {}
}
'''

        adapter = make_adapter(ScalaCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "class PublicClass" in result
        assert "val publicField" in result
        assert "def publicMethod" in result

        assert "privateField" not in result
        assert "privateMethod" not in result

        assert "private class PrivateClass" not in result
