"""
Validation utilities for data processing.

This package provides validators for common data types
used throughout the application.
"""

from .email import EmailValidator
from .phone import PhoneValidator
from .address import AddressValidator

__all__ = ["EmailValidator", "PhoneValidator", "AddressValidator", "validate_all"]


def validate_all(data: dict) -> dict[str, list[str]]:
    """
    Convenience function to run all validators on a data dict.

    Returns a dict of field -> list of error messages.
    Empty dict means validation passed.
    """
    errors = {}

    if "email" in data:
        if err := EmailValidator().validate(data["email"]):
            errors["email"] = err

    if "phone" in data:
        if err := PhoneValidator().validate(data["phone"]):
            errors["phone"] = err

    return errors
