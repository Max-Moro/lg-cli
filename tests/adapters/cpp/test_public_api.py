"""
Tests for public API filtering in C++ adapter.
"""

from lg.adapters.langs.cpp import CppCfg
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestCppPublicApiOptimization:
    """Test public API filtering for C++ code."""

    def test_public_api_only_basic(self, do_public_api):
        """Test basic public API filtering."""
        adapter = make_adapter(CppCfg(public_api_only=True))

        result, meta = adapter.process(lctx(do_public_api))

        assert meta.get("cpp.removed.function", 0) > 0

        assert "class UserManager" in result
        assert "User* createUser" in result

        assert "static void validateUserData" not in result
        assert "static int generateId" not in result

        assert_golden_match(result, "public_api", "basic")

    def test_class_visibility_detection(self):
        """Test detection of public/private class members."""
        code = '''class PublicClass {
public:
    void publicMethod();
    int publicField;

private:
    void privateMethod();
    int privateField;

protected:
    void protectedMethod();
    int protectedField;
};

class PrivateClass {
    void method();
};
'''

        adapter = make_adapter(CppCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "class PublicClass" in result
        assert "void publicMethod" in result
        assert "int publicField" in result

        assert "privateMethod" not in result
        assert "privateField" not in result

    def test_namespace_exports(self):
        """Test namespace and enum exports."""
        code = '''namespace public_ns {
    class PublicClass {};
    void publicFunction();
}

namespace {
    class AnonymousClass {};
    void anonymousFunction();
}

enum class Color {
    RED, GREEN, BLUE
};

enum InternalState {
    ACTIVE, INACTIVE
};
'''

        adapter = make_adapter(CppCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "namespace public_ns" in result
        assert "class PublicClass" in result
        assert "enum class Color" in result

    def test_friend_and_static_members(self):
        """Test handling of friend functions and static members."""
        code = '''class PublicClass {
public:
    static void publicStatic();
    friend void friendFunction();

private:
    static void privateStatic();
    friend class PrivateFriend;
};

void friendFunction() {
    // Implementation
}

class PrivateFriend {
    void method();
};
'''

        adapter = make_adapter(CppCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "class PublicClass" in result
        assert "static void publicStatic" in result
        assert "friend void friendFunction" in result

    def test_template_visibility(self):
        """Test visibility of template classes and functions."""
        code = '''template<typename T>
class PublicTemplate {
public:
    void publicMethod();
private:
    void privateMethod();
};

template<typename T>
void publicTemplateFunction(T value) {}

namespace internal {
    template<typename T>
    void internalTemplateFunction(T value) {}
}
'''

        adapter = make_adapter(CppCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "template<typename T>" in result
        assert "class PublicTemplate" in result
        assert "void publicMethod" in result
        assert "void publicTemplateFunction" in result


class TestCppPublicApiEdgeCases:
    """Test edge cases for C++ public API filtering."""

    def test_extern_c_blocks(self):
        """Test handling of extern C blocks."""
        code = '''#ifdef __cplusplus
extern "C" {
#endif

void publicCFunction();

static void privateCFunction();

#ifdef __cplusplus
}
#endif
'''

        adapter = make_adapter(CppCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert '#ifdef __cplusplus' in result
        assert 'extern "C"' in result
        assert "void publicCFunction" in result

        assert "static void privateCFunction" not in result

    def test_virtual_and_override(self):
        """Test handling of virtual and override keywords."""
        code = '''class Base {
public:
    virtual void publicVirtual();
    virtual void pureVirtual() = 0;

protected:
    virtual void protectedVirtual();

private:
    virtual void privateVirtual();
};

class Derived : public Base {
public:
    void publicVirtual() override;
    void pureVirtual() override;

protected:
    void protectedVirtual() override;
};
'''

        adapter = make_adapter(CppCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "class Base" in result
        assert "virtual void publicVirtual" in result
        assert "virtual void pureVirtual() = 0" in result

        assert "protectedVirtual" not in result
        assert "privateVirtual" not in result

    def test_operator_overload_visibility(self):
        """Test visibility of operator overloads."""
        code = '''class Complex {
public:
    Complex operator+(const Complex& other) const;
    friend std::ostream& operator<<(std::ostream& os, const Complex& c);

private:
    Complex operator-(const Complex& other) const;
};
'''

        adapter = make_adapter(CppCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "Complex operator+(const Complex& other)" in result
        assert "friend std::ostream& operator<<" in result

        assert "operator-" not in result

    def test_nested_class_visibility(self):
        """Test visibility of nested classes."""
        code = '''class Outer {
public:
    class PublicNested {
    public:
        void method();
    };

private:
    class PrivateNested {
    public:
        void method();
    };
};
'''

        adapter = make_adapter(CppCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "class Outer" in result
        assert "class PublicNested" in result

        assert "PrivateNested" not in result
