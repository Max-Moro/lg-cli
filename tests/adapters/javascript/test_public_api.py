"""
Tests for public API filtering in JavaScript adapter.
"""

from lg.adapters.javascript import JavaScriptCfg
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestJavaScriptPublicApiOptimization:
    """Test public API filtering for JavaScript code."""

    def test_public_api_only_basic(self, do_public_api):
        """Test basic public API filtering."""
        adapter = make_adapter(JavaScriptCfg(public_api_only=True))

        result, meta = adapter.process(lctx(do_public_api))

        # Private elements should be removed
        assert meta.get("javascript.removed.function", 0) > 0
        assert meta.get("javascript.removed.method", 0) > 0
        assert meta.get("javascript.removed.class", 0) > 0

        # Public exports should remain
        assert "export class UserManager" in result
        assert "export function createUserManager" in result

        # Private elements should be removed or placeholdered
        assert "#private" not in result

        assert_golden_match(result, "public_api", "basic")

    def test_export_detection(self):
        """Test detection of exported elements."""
        code = '''
// Exported elements (public API)
export class PublicClass {
    method() {}
    #internal() {}
}

export function publicFunction() {}

export const publicConstant = "value";

// Non-exported elements (private)
class PrivateClass {
    method() {}
}

function privateFunction() {}

const privateConstant = "value";

// Default export
export default class DefaultClass {}
'''

        adapter = make_adapter(JavaScriptCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        # Exported elements should remain
        assert "export class PublicClass" in result
        assert "export function publicFunction" in result
        assert "export const publicConstant" in result
        assert "export default class DefaultClass" in result

        # Private elements should be removed
        assert "class PrivateClass" not in result
        assert "function privateFunction" not in result

    def test_class_member_visibility(self):
        """Test class member visibility in public API."""
        code = '''
export class PublicClass {
    // Public members
    publicField = "public";
    publicMethod() {}

    // Private members
    #privateField = "private";
    #privateMethod() {}

    // Getters and setters
    get publicGetter() { return this.publicField; }
    set publicSetter(value) { this.publicField = value; }

    get #privateGetter() { return this.#privateField; }
    set #privateSetter(value) { this.#privateField = value; }
}

// Private class
class PrivateClass {
    method() {}
}
'''

        adapter = make_adapter(JavaScriptCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        # Public class should remain with public members
        assert "export class PublicClass" in result
        assert "publicField" in result
        assert "publicMethod" in result

        # Private members should be removed
        assert "#privateField" not in result
        assert "#privateMethod" not in result

        # Private class should be removed
        assert "class PrivateClass" not in result

    def test_re_exports(self):
        """Test re-export statements."""
        code = '''
// Re-exports (public API)
export { default as Component } from './Component.js';
export { Utils } from './utils.js';
export * from './types.js';

// Named exports
export {
    ServiceA,
    ServiceB as Service2
} from './services.js';

// Private imports (not re-exported)
import { InternalHelper } from './internal.js';

// Local definitions using imports
function useInternal() {
    return InternalHelper.process();
}
'''

        adapter = make_adapter(JavaScriptCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        # Re-exports should remain
        assert "export { default as Component }" in result
        assert "export { Utils }" in result
        assert "export * from './types.js'" in result

        # Private imports should be removed or summarized
        assert "InternalHelper" not in result

    def test_namespace_like_exports(self):
        """Test namespace-like object exports."""
        code = '''
export const Utils = {
    formatName(user) {
        return `${user.name}`;
    },

    _internalFormatting(text) {
        return text.toLowerCase();
    }
};

const InternalUtils = {
    debugLog(message) {
        console.log(message);
    }
};
'''

        adapter = make_adapter(JavaScriptCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        # Exported namespace should remain
        assert "export const Utils" in result
        assert "formatName" in result

        # Private namespace should be removed
        assert "InternalUtils" not in result

    def test_default_export_preservation(self):
        """Test that default exports are preserved."""
        code = '''
class UserManager {
    getUser() {}
    #validateUser() {}
}

export default UserManager;
'''

        adapter = make_adapter(JavaScriptCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        # Class and default export should remain
        assert "class UserManager" in result
        assert "export default UserManager" in result

        # Private methods should be filtered
        assert "#validateUser" not in result
