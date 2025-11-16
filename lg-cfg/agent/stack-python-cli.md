# Recommendations Within the Technology Stack

This project is a CLI tool and is developed in Python.

## Typed Code

We always write strictly typed code. Therefore, we don't use `TYPE_CHECKING`, don't use `from typing import Any`, and don't wrap types in quotes.

Circular import problems should be solved without lowering the level of typing strictness. For example, use internal imports or restructure modules (create additional ones).