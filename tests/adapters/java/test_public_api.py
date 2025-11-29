"""
Tests for public API filtering in Java adapter.
"""

from lg.adapters.java import JavaCfg
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestJavaPublicApiOptimization:
    """Test public API filtering for Java code."""

    def test_public_api_only_basic(self, do_public_api):
        """Test basic public API filtering."""
        adapter = make_adapter(JavaCfg(public_api_only=True))

        result, meta = adapter.process(lctx(do_public_api))

        assert meta.get("java.removed.method", 0) > 0
        assert meta.get("java.removed.function", 0) > 0
        assert meta.get("java.removed.class", 0) > 0

        assert "public class UserManager" in result
        assert "public static UserManager createUserManager" in result

        assert "private final Map<String, User> internalCache" not in result
        assert "private void validateUserData" not in result
        assert "class InternalLogger" not in result

        assert_golden_match(result, "public_api", "basic")

    def test_visibility_detection(self):
        """Test detection of public/private elements."""
        code = '''
public class PublicClass {
    public void publicMethod() {}
    private void privateMethod() {}
}

class PackagePrivateClass {
    public void method() {}
}

public interface PublicInterface {
    void method();
}

interface PackagePrivateInterface {
    void method();
}

public static final String PUBLIC_CONSTANT = "value";
private static final String PRIVATE_CONSTANT = "value";
'''

        adapter = make_adapter(JavaCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "public class PublicClass" in result
        assert "public void publicMethod" in result
        assert "public interface PublicInterface" in result
        assert "PUBLIC_CONSTANT" in result

        assert "private void privateMethod" not in result
        assert "class PackagePrivateClass" not in result
        assert "PRIVATE_CONSTANT" not in result

    def test_enum_and_annotation_exports(self):
        """Test enum and annotation exports."""
        code = '''
public enum UserRole {
    ADMIN, USER, GUEST
}

enum InternalStatus {
    ACTIVE, INACTIVE
}

public @interface Validated {
    String message() default "";
}

@interface InternalAnnotation {
    int value();
}
'''

        adapter = make_adapter(JavaCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "public enum UserRole" in result
        assert "public @interface Validated" in result

        assert "enum InternalStatus" not in result
        assert "@interface InternalAnnotation" not in result

    def test_class_member_visibility(self):
        """Test class member visibility in public API."""
        code = '''
public class PublicClass {
    public String publicField = "public";
    public void publicMethod() {}

    protected String protectedField = "protected";
    protected void protectedMethod() {}

    private String privateField = "private";
    private void privateMethod() {}

    String packagePrivateField = "package";
    void packagePrivateMethod() {}
}

class PrivateClass {
    public void method() {}
}
'''

        adapter = make_adapter(JavaCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "public class PublicClass" in result
        assert "public String publicField" in result
        assert "public void publicMethod" in result

        assert "privateField" not in result
        assert "privateMethod" not in result

        assert "class PrivateClass" not in result

    def test_annotation_handling(self):
        """Test handling of annotations in public API mode."""
        code = '''
@Logged
public class PublicClass {
    @Logged
    public void publicMethod() {}

    @Logged
    private void privateMethod() {}
}

@Logged
class PrivateClass {
    public void method() {}
}
'''

        adapter = make_adapter(JavaCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "@Logged" in result
        assert "public class PublicClass" in result

        assert "PrivateClass" not in result
