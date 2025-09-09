"""
Tests for public API filtering in TypeScript adapter.
"""
import pytest

from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from .conftest import lctx_ts, do_public_api, assert_golden_match


class TestTypeScriptPublicApiOptimization:
    """Test public API filtering for TypeScript code."""
    
    def test_public_api_only_basic(self, do_public_api):
        """Test basic public API filtering."""
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(public_api_only=True)
        
        result, meta = adapter.process(lctx_ts(do_public_api))
        
        # Private elements should be removed
        assert meta.get("code.removed.functions", 0) == 2
        assert meta.get("code.removed.methods", 0) == 9
        assert meta.get("code.removed.classes", 0) == 1
        assert meta.get("code.removed.interfaces", 0) == 1
        
        # Public exports should remain
        assert "export class" in result
        assert "export function" in result
        assert "export interface" in result
        
        # Private elements should be removed or placeholdered
        assert "_private" not in result or "… private" in result
        
        assert_golden_match(result, "public_api", "basic")


    def test_export_detection(self):
        """Test detection of exported elements."""
        code = '''
// Exported elements (public API)
export class PublicClass {
    public method(): void {}
    private _internal(): void {}
}

export function publicFunction(): void {}

export interface PublicInterface {
    prop: string;
}

export const publicConstant = "value";

export type PublicType = string | number;

// Non-exported elements (private)
class PrivateClass {
    public method(): void {}
}

function privateFunction(): void {}

interface PrivateInterface {
    prop: string;
}

const privateConstant = "value";

type PrivateType = string | number;

// Default export
export default class DefaultClass {}
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(public_api_only=True)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Exported elements should remain
        assert "export class PublicClass" in result
        assert "export function publicFunction" in result
        assert "export interface PublicInterface" in result
        assert "export const publicConstant" in result
        assert "export type PublicType" in result
        assert "export default class DefaultClass" in result
        
        # Private elements should be removed
        assert "class PrivateClass" not in result
        assert "function privateFunction" not in result
        assert "interface PrivateInterface" not in result

    @pytest.mark.skip(reason="Skipping this test for now.")
    def test_namespace_exports(self):
        """Test namespace and module exports."""
        code = '''
// Namespace with exports
export namespace Utils {
    export function helper(): void {}
    export const constant = 42;
    
    // Private within namespace
    function internal(): void {}
    const secret = "hidden";
}

// Module declaration
declare module "external-lib" {
    export interface Config {
        option: boolean;
    }
    
    export function initialize(config: Config): void;
}

// Namespace without export (private)
namespace InternalUtils {
    export function helper(): void {}
    const data = [];
}
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(public_api_only=True)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Exported namespace should remain
        assert "export namespace Utils" in result
        assert "export function helper" in result
        assert "export const constant" in result
        
        # Module declaration should remain (it's public API)
        assert "declare module" in result
        
        # Private namespace should be removed
        assert "namespace InternalUtils" not in result

    @pytest.mark.skip(reason="Skipping this test for now.")
    def test_re_exports(self):
        """Test re-export statements."""
        code = '''
// Re-exports (public API)
export { default as Component } from './Component';
export { Utils, type UtilsConfig } from './utils';
export * from './types';
export * as API from './api';

// Named exports
export { 
    ServiceA, 
    ServiceB as Service2,
    type ConfigType 
} from './services';

// Conditional exports
if (process.env.NODE_ENV === 'development') {
    export { DevTools } from './dev-tools';
}

// Private imports (not re-exported)
import { InternalHelper } from './internal';
import type { InternalType } from './internal-types';

// Local definitions using imports
function useInternal(): InternalType {
    return InternalHelper.process();
}
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(public_api_only=True)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Re-exports should remain
        assert "export { default as Component }" in result
        assert "export { Utils, type UtilsConfig }" in result
        assert "export * from './types'" in result
        assert "export * as API" in result
        
        # Private imports should be removed or summarized
        assert "InternalHelper" not in result or "… import" in result

    @pytest.mark.skip(reason="Skipping this test for now.")
    def test_class_member_visibility(self):
        """Test class member visibility in public API."""
        code = '''
export class PublicClass {
    // Public members
    public publicField: string = "public";
    public publicMethod(): void {}
    
    // Protected members
    protected protectedField: string = "protected";
    protected protectedMethod(): void {}
    
    // Private members
    private _privateField: string = "private";
    private _privateMethod(): void {}
    
    // No explicit modifier (public by default)
    implicitPublicField: number = 42;
    implicitPublicMethod(): void {}
    
    // Getters and setters
    get publicGetter(): string { return this.publicField; }
    set publicSetter(value: string) { this.publicField = value; }
    
    private get _privateGetter(): string { return this._privateField; }
    private set _privateSetter(value: string) { this._privateField = value; }
}

// Private class
class PrivateClass {
    public method(): void {}
}
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(public_api_only=True)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Public class should remain with public members
        assert "export class PublicClass" in result
        assert "public publicField" in result
        assert "public publicMethod" in result
        assert "implicitPublicField" in result
        assert "implicitPublicMethod" in result
        
        # Protected members might be preserved (depends on implementation)
        # Private members should be removed
        assert "_privateField" not in result or "… private" in result
        assert "_privateMethod" not in result or "… private" in result
        
        # Private class should be removed
        assert "class PrivateClass" not in result

    @pytest.mark.skip(reason="Skipping this test for now.")
    def test_interface_and_type_exports(self):
        """Test interface and type definition exports."""
        code = '''
// Exported types (public API)
export interface UserProfile {
    id: number;
    name: string;
    email?: string;
}

export type Status = "active" | "inactive" | "pending";

export type ApiResponse<T> = {
    data: T;
    success: boolean;
    error?: string;
};

// Private types
interface InternalConfig {
    secret: string;
    debug: boolean;
}

type InternalStatus = "init" | "running" | "stopped";

// Type alias for external type (public)
export type { Config } from 'external-package';

// Enum exports
export enum Priority {
    LOW = 1,
    MEDIUM = 2,
    HIGH = 3
}

enum InternalPriority {
    SYSTEM = 0,
    USER = 1
}
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(public_api_only=True)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Exported types should remain
        assert "export interface UserProfile" in result
        assert "export type Status" in result
        assert "export type ApiResponse" in result
        assert "export type { Config }" in result
        assert "export enum Priority" in result
        
        # Private types should be removed
        assert "interface InternalConfig" not in result
        assert "type InternalStatus" not in result
        assert "enum InternalPriority" not in result
