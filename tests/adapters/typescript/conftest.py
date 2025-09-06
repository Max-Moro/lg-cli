"""
Shared fixtures and utilities for TypeScript adapter tests.
"""

import pytest
from pathlib import Path

from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.code_model import FunctionBodyConfig, CommentConfig, ImportConfig, LiteralConfig, FieldConfig
from tests.conftest import lctx_ts, lctx


@pytest.fixture
def typescript_adapter():
    """Basic TypeScript adapter instance."""
    adapter = TypeScriptAdapter()
    adapter._cfg = TypeScriptCfg()
    return adapter


@pytest.fixture
def typescript_code_sample():
    """Sample TypeScript code for testing."""
    return '''// TypeScript module
import { Component } from '@angular/core';
import { Observable } from 'rxjs';

interface User {
    id: number;
    name: string;
    email?: string;
}

class UserService {
    private users: User[] = [];
    
    constructor(private apiUrl: string) {
        this.apiUrl = apiUrl;
    }
    
    getUsers(): Observable<User[]> {
        return fetch(this.apiUrl + '/users')
            .then(response => response.json())
            .then(data => {
                this.users = data;
                return data;
            });
    }
    
    addUser(user: User): Promise<User> {
        return fetch(this.apiUrl + '/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(user)
        }).then(response => response.json());
    }
    
    private validateUser(user: User): boolean {
        return user.name.length > 0 && user.id > 0;
    }
}

const createService = (url: string) => {
    return new UserService(url);
};

export { UserService, User };
'''


@pytest.fixture
def typescript_barrel_file_sample():
    """Sample TypeScript barrel file for testing."""
    return '''// Barrel file example
export { ComponentA } from './components/ComponentA';
export { ComponentB } from './components/ComponentB';
export { ServiceA, ServiceB } from './services';
export * from './utils';
export { default as MainComponent } from './MainComponent';

// Re-export external libraries
export { Observable } from 'rxjs';
export type { User, UserResponse } from './types';
'''


@pytest.fixture
def typescript_non_barrel_file_sample():
    """Sample TypeScript non-barrel file for testing."""
    return '''// Regular TypeScript module
import { Component } from '@angular/core';
import { Observable } from 'rxjs';

@Component({
    selector: 'app-user',
    template: '<div>User Component</div>'
})
export class UserComponent {
    
    constructor(private userService: UserService) {}
    
    loadUsers(): Observable<User[]> {
        return this.userService.getUsers();
    }
    
    private validateUser(user: User): boolean {
        return user.name.length > 0;
    }
}

export default UserComponent;
'''


@pytest.fixture
def typescript_config_simple() -> TypeScriptCfg:
    """Simple TypeScript configuration."""
    return TypeScriptCfg(
        public_api_only=True,
        strip_function_bodies=True
    )


def create_typescript_context(raw_text: str, filename: str = "test.ts", group_size: int = 1, mixed: bool = False):
    """Helper to create TypeScript LightweightContext."""
    return lctx(raw_text=raw_text, filename=filename, group_size=group_size, mixed=mixed)


def assert_golden_match(result: str, golden_file: Path, update_golden: bool = False):
    """
    Assert that result matches golden file content.
    
    Args:
        result: Actual result string
        golden_file: Path to golden file
        update_golden: If True, update golden file with result
    """
    if update_golden or not golden_file.exists():
        golden_file.parent.mkdir(parents=True, exist_ok=True)
        golden_file.write_text(result, encoding='utf-8')
        if update_golden:
            pytest.skip(f"Updated golden file: {golden_file}")
    
    expected = golden_file.read_text(encoding='utf-8')
    assert result == expected, f"Result doesn't match golden file: {golden_file}"
