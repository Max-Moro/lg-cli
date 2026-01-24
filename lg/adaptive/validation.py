"""
Validation for the adaptive system.

Provides validation rules for AdaptiveModel:
- Single integration mode-set rule
- Mode reference validation
- Provider support validation
"""

from __future__ import annotations

from typing import List, Optional

from .model import AdaptiveModel
from .errors import (
    MultipleIntegrationModeSetsError,
    NoIntegrationModeSetError,
    InvalidModeReferenceError,
    ProviderNotSupportedError,
)


class AdaptiveValidator:
    """
    Validator for AdaptiveModel.

    Ensures business rules are followed:
    - Exactly one integration mode-set per context
    - Mode references point to existing modes
    - Provider is supported by integration mode-set
    """

    def validate_model(self, model: AdaptiveModel, context_name: str = "") -> None:
        """
        Validate that model has exactly one integration mode-set.

        Args:
            model: AdaptiveModel to validate
            context_name: Context name for error messages

        Raises:
            MultipleIntegrationModeSetsError: if > 1 integration mode-set
            NoIntegrationModeSetError: if 0 integration mode-sets
        """
        model.validate_single_integration(context_name)

    def validate_mode_reference(
        self,
        model: AdaptiveModel,
        modeset: str,
        mode: str,
        context_name: str = ""
    ) -> None:
        """
        Validate that {% mode modeset:mode %} reference is valid.

        Args:
            model: AdaptiveModel to check against
            modeset: Mode-set ID from template
            mode: Mode ID from template
            context_name: Context name for error messages

        Raises:
            InvalidModeReferenceError: if mode not found in model
        """
        if not model.has_mode(modeset, mode):
            mode_set = model.get_mode_set(modeset)
            available_modes: List[str] = []
            if mode_set:
                available_modes = list(mode_set.modes.keys())

            raise InvalidModeReferenceError(
                modeset=modeset,
                mode=mode,
                context_name=context_name,
                available_modes=available_modes,
            )

    def validate_provider_support(
        self,
        model: AdaptiveModel,
        provider_id: str,
        context_name: str = ""
    ) -> None:
        """
        Validate that provider is supported by integration mode-set.

        After filtering by provider, the integration mode-set must
        have at least one mode remaining.

        Args:
            model: AdaptiveModel to validate
            provider_id: Provider ID to check
            context_name: Context name for error messages

        Raises:
            NoIntegrationModeSetError: if no integration mode-set
            ProviderNotSupportedError: if provider not supported
        """
        integration_set = model.get_integration_mode_set()
        if integration_set is None:
            # First validate that we have exactly one
            model.validate_single_integration(context_name)
            return  # Should not reach here

        # Check if any mode supports this provider
        supported_providers = integration_set.get_supported_providers()
        if provider_id not in supported_providers:
            raise ProviderNotSupportedError(
                provider_id=provider_id,
                context_name=context_name,
                available_providers=sorted(supported_providers),
            )

        # Check if filtered mode-set has any modes
        filtered = integration_set.filter_by_provider(provider_id)
        if not filtered.modes:
            raise ProviderNotSupportedError(
                provider_id=provider_id,
                context_name=context_name,
                available_providers=sorted(supported_providers),
            )


# Singleton instance for convenience
_validator = AdaptiveValidator()


def validate_model(model: AdaptiveModel, context_name: str = "") -> None:
    """Convenience function for model validation."""
    _validator.validate_model(model, context_name)


def validate_mode_reference(
    model: AdaptiveModel,
    modeset: str,
    mode: str,
    context_name: str = ""
) -> None:
    """Convenience function for mode reference validation."""
    _validator.validate_mode_reference(model, modeset, mode, context_name)


def validate_provider_support(
    model: AdaptiveModel,
    provider_id: str,
    context_name: str = ""
) -> None:
    """Convenience function for provider support validation."""
    _validator.validate_provider_support(model, provider_id, context_name)


__all__ = [
    "AdaptiveValidator",
    "validate_model",
    "validate_mode_reference",
    "validate_provider_support",
]
