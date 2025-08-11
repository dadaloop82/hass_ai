"""Exceptions for HASS AI integration."""

from homeassistant.exceptions import HomeAssistantError


class HassAiError(HomeAssistantError):
    """Base exception for HASS AI."""


class AIProviderError(HassAiError):
    """Error with AI provider communication."""


class ConfigurationError(HassAiError):
    """Error with configuration."""


class EntityAnalysisError(HassAiError):
    """Error during entity analysis."""
