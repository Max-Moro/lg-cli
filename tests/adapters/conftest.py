"""
Shared fixtures and utilities for language adapter tests.
"""

import pytest
from pathlib import Path
from typing import Dict, Any, Optional

from lg.adapters.tree_sitter_support import is_tree_sitter_available
from lg.adapters.code_model import CodeCfg
from lg.adapters.python_tree_sitter import PythonCfg
from lg.adapters.typescript_tree_sitter import TypeScriptCfg


@pytest.fixture
def python_code_sample():
    """Sample Python code for testing."""
    return '''"""Module docstring."""

import os
import sys
from typing import List, Optional

class Calculator:
    """A simple calculator class."""
    
    def __init__(self, name: str = "default"):
        """Initialize calculator."""
        self.name = name
        self.history = []
    
    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        result = a + b
        self.history.append(f"add({a}, {b}) = {result}")
        return result
    
    def multiply(self, a: int, b: int) -> int:
        """Multiply two numbers."""
        result = a * b
        self.history.append(f"multiply({a}, {b}) = {result}")
        return result
    
    def get_history(self) -> List[str]:
        """Get calculation history."""
        return self.history.copy()

def main():
    """Main function."""
    calc = Calculator("test")
    print(calc.add(2, 3))
    print(calc.multiply(4, 5))
    
if __name__ == "__main__":
    main()
'''


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
def python_config_simple() -> PythonCfg:
    """Simple Python configuration."""
    return PythonCfg(
        strip_function_bodies=True,
        comment_policy="keep_doc"
    )


@pytest.fixture
def python_config_advanced() -> PythonCfg:
    """Advanced Python configuration."""
    from lg.adapters.code_model import FunctionBodyConfig, CommentConfig
    
    return PythonCfg(
        strip_function_bodies=FunctionBodyConfig(
            mode="large_only",
            min_lines=3
        ),
        comment_policy=CommentConfig(
            policy="keep_first_sentence",
            max_length=100
        )
    )


@pytest.fixture
def typescript_config_simple() -> TypeScriptCfg:
    """Simple TypeScript configuration."""
    return TypeScriptCfg(
        public_api_only=True,
        strip_function_bodies=True
    )


@pytest.fixture
def skip_if_no_tree_sitter():
    """Skip test if Tree-sitter is not available."""
    if not is_tree_sitter_available():
        pytest.skip("Tree-sitter not available")


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


def create_temp_file(tmp_path: Path, filename: str, content: str) -> Path:
    """Create a temporary file with content."""
    file_path = tmp_path / filename
    file_path.write_text(content, encoding='utf-8')
    return file_path
