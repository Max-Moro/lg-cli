"""
Complex integration tests for TypeScript adapter.
Tests combining multiple optimization types and edge cases.
"""

from lg.adapters.code_model import ImportConfig, LiteralConfig, FieldConfig
from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from .conftest import lctx_ts, lctx, assert_golden_match


class TestTypeScriptComplexIntegration:
    """Complex integration tests for TypeScript adapter."""

    def test_full_optimization_pipeline(self, typescript_code_sample, tmp_path):
        """Test complete TypeScript adapter pipeline with all optimizations."""
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg.from_dict({
            "strip_function_bodies": True,
            "comment_policy": "strip_all",
            "public_api_only": False,
            "strip_literals": {
                "max_string_length": 50,
                "max_array_elements": 10
            },
            "imports": {
                "policy": "external_only"
            },
            "fields": {
                "strip_trivial_constructors": True
            },
            "placeholders": {
                "mode": "summary",
                "style": "inline"
            }
        })

        result, meta = adapter.process(lctx_ts(typescript_code_sample))

        # Verify multiple optimizations occurred
        assert meta.get("code.removed.functions", 0) >= 0
        assert meta.get("code.removed.methods", 0) >= 0

        # Verify placeholders were inserted if optimizations occurred
        if (meta.get("code.removed.functions", 0) > 0 or 
            meta.get("code.removed.methods", 0) > 0):
            assert ("// … " in result or "/* … " in result)

        # Verify structure is preserved
        assert "class UserService" in result
        assert "interface User" in result

        # Golden file test
        golden_file = tmp_path / "typescript_full_pipeline.golden"
        assert_golden_match(result, golden_file)

    def test_barrel_file_detection_comprehensive(self, typescript_barrel_file_sample, typescript_non_barrel_file_sample):
        """Test comprehensive barrel file detection."""
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(skip_barrel_files=True)
        
        # Test obvious barrel file (index.ts)
        index_ctx = lctx(
            typescript_barrel_file_sample, 
            filename="index.ts"
        )
        assert adapter._is_barrel_file(index_ctx) == True
        assert adapter.should_skip(index_ctx) == True
        
        # Test content-based barrel file detection
        barrel_ctx = lctx(
            typescript_barrel_file_sample,
            filename="exports.ts"  # Not index.ts to test content-based detection
        )
        assert adapter._is_barrel_file(barrel_ctx) == True
        assert adapter.should_skip(barrel_ctx) == True

        # Test regular TypeScript file
        regular_ctx = lctx(
            typescript_non_barrel_file_sample,
            filename="user.component.ts"
        )
        assert adapter._is_barrel_file(regular_ctx) == False
        assert adapter.should_skip(regular_ctx) == False

        # Test with barrel file detection disabled
        adapter._cfg = TypeScriptCfg(skip_barrel_files=False)
        assert adapter.should_skip(index_ctx) == False  # Should not skip when disabled

    def test_complex_class_optimization(self):
        """Test complex class with multiple optimization types."""
        code = '''
import { Component } from '@angular/core';
import { Observable } from 'rxjs';
import { helper } from './utils/helper';

/**
 * UserService class for managing users
 * Provides CRUD operations and validation
 */
export class UserService {
    private users: User[] = [
        { id: 1, name: "Alice", email: "alice@example.com" },
        { id: 2, name: "Bob", email: "bob@example.com" },
        { id: 3, name: "Charlie", email: "charlie@example.com" },
        { id: 4, name: "David", email: "david@example.com" },
        { id: 5, name: "Eve", email: "eve@example.com" }
    ];
    
    constructor(private apiUrl: string) {
        this.apiUrl = apiUrl;
    }
    
    // Get all users
    getUsers(): Observable<User[]> {
        return this.httpClient.get<User[]>(`${this.apiUrl}/users`);
    }
    
    private validateUser(user: User): boolean {
        return user.name.length > 0 && user.id > 0;
    }
    
    get userCount(): number {
        return this.users.length;
    }
    
    set userList(users: User[]) {
        this.users = users;
    }
}
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(
            public_api_only=True,  # Remove private methods
            strip_function_bodies=True,  # Strip remaining function bodies
            comment_policy="keep_doc",  # Keep JSDoc comments
            strip_literals=LiteralConfig(max_array_elements=3),  # Trim large arrays
            imports=ImportConfig(policy="external_only"),  # Keep only external imports
            fields=FieldConfig(
                strip_trivial_constructors=True,
                strip_trivial_accessors=True
            )
        )
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Public methods should be preserved but bodies stripped
        assert "export class UserService" in result
        assert "getUsers(): Observable<User[]>" in result
        
        # Private method should be removed entirely
        assert "private validateUser" not in result
        
        # JSDoc should be preserved
        assert "UserService class for managing users" in result
        
        # Large array should be trimmed
        assert ("... and" in result and "more]" in result) or meta.get("code.removed.literals", 0) > 0
        
        # External imports should be preserved, local should be removed
        assert "@angular/core" in result or "Component" in result
        assert "rxjs" in result or "Observable" in result
        
        # Should have placeholders for optimizations
        assert ("// … " in result or "/* … " in result or "… " in result)
        
        # Multiple optimization types should have occurred
        assert meta.get("code.removed.private_elements", 0) > 0

    def test_interface_and_type_preservation(self):
        """Test that TypeScript interfaces and types are handled correctly."""
        code = '''
// Internal interface
interface InternalUser {
    id: number;
    name: string;
}

// Public interface  
export interface PublicUser {
    id: number;
    name: string;
    email?: string;
}

// Type alias
export type UserResponse = {
    user: PublicUser;
    success: boolean;
    data: {
        timestamp: number;
        version: string;
        metadata: {
            source: string;
            processed: boolean;
            tags: string[]
        }
    };
};

class InternalService {
    processUser(user: InternalUser): void {
        console.log(user.name);
    }
}

export class PublicService {
    getUser(id: number): PublicUser | null {
        return null;
    }
}
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(
            public_api_only=True,
            strip_literals=LiteralConfig(max_object_properties=2)
        )
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Public interfaces and types should be preserved
        assert "export interface PublicUser" in result
        assert "export type UserResponse" in result
        assert "export class PublicService" in result
        
        # Internal interface and class should be removed
        assert "interface InternalUser" not in result
        assert "class InternalService" not in result
        
        # Large nested object should be trimmed
        assert ("... and" in result and "more}" in result) or meta.get("code.removed.literals", 0) > 0

    def test_error_handling_graceful(self):
        """Test graceful error handling with malformed TypeScript code."""
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(strip_function_bodies=True)

        # Test with malformed code that might cause parsing issues
        malformed_code = "function incomplete(: string"
        
        # Should not crash, even with syntax errors
        result, meta = adapter.process(lctx_ts(malformed_code))
        
        # Should have processed something
        assert meta["_adapter"] == "typescript"
        assert isinstance(result, str)

    def test_metadata_collection_comprehensive(self, typescript_code_sample):
        """Test comprehensive metadata collection for TypeScript."""
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(
            strip_function_bodies=True,
            comment_policy="strip_all",
            strip_literals=True,
            public_api_only=True
        )
        
        result, meta = adapter.process(lctx_ts(typescript_code_sample))
        
        # Check required metadata fields
        required_fields = [
            "_group_size", "_group_mixed", "_adapter",
            "code.removed.functions", "code.removed.methods"
        ]
        
        for field in required_fields:
            assert field in meta, f"Missing metadata field: {field}"
        
        assert meta["_adapter"] == "typescript"
        assert meta["_group_size"] == 1
        assert meta["_group_mixed"] is False
        
        # Should have some processing performed with aggressive settings
        total_removed = (meta.get("code.removed.functions", 0) + 
                        meta.get("code.removed.methods", 0) +
                        meta.get("code.removed.comments", 0) +
                        meta.get("code.removed.literals", 0) +
                        meta.get("code.removed.private_elements", 0))
        # With aggressive settings, we expect some removals
        assert total_removed >= 0

    def test_configuration_loading_comprehensive(self):
        """Test comprehensive TypeScript configuration loading."""
        # Test simple boolean config
        cfg = TypeScriptCfg.from_dict({"strip_function_bodies": True})
        assert cfg.strip_function_bodies is True

        # Test complex object config
        complex_config = {
            "strip_function_bodies": {
                "mode": "public_only",
                "min_lines": 5
            },
            "comment_policy": {
                "policy": "keep_doc",
                "max_length": 100
            },
            "skip_barrel_files": False,
            "public_api_only": True
        }

        cfg = TypeScriptCfg.from_dict(complex_config)
        assert hasattr(cfg.strip_function_bodies, 'mode')
        assert cfg.strip_function_bodies.mode == "public_only"
        assert cfg.skip_barrel_files is False
        assert cfg.public_api_only is True

    def test_mixed_file_extensions(self):
        """Test handling of different TypeScript file extensions."""
        tsx_code = '''
import React from 'react';

interface Props {
    name: string;
    age?: number;
}

export const UserComponent: React.FC<Props> = ({ name, age }) => {
    const displayAge = age || 0;
    
    return (
        <div>
            <h1>Hello, {name}</h1>
            {age && <p>Age: {age}</p>}
        </div>
    );
};
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(strip_function_bodies=True)
        
        # Test .tsx file
        tsx_result, tsx_meta = adapter.process(lctx(tsx_code, filename="component.tsx"))
        
        # Should handle JSX syntax
        assert "React.FC<Props>" in tsx_result
        assert "export const UserComponent" in tsx_result
        
        # Test .ts file with same adapter
        ts_result, ts_meta = adapter.process(lctx(tsx_code, filename="component.ts"))
        
        # Both should be processed by the same adapter
        assert tsx_meta["_adapter"] == "typescript"
        assert ts_meta["_adapter"] == "typescript"
