"""LLM providers."""

from .base import Provider
from .registry import ProviderRegistry, get_provider

__all__ = [
    "Provider",
    "ProviderRegistry",
    "get_provider",
]


def _register_default_providers():
    """Register default providers."""
    try:
        from .openai import OpenAIProvider
        ProviderRegistry.register_class(OpenAIProvider, "openai")
    except ImportError:
        pass

    try:
        from .anthropic import AnthropicProvider
        ProviderRegistry.register_class(AnthropicProvider, "anthropic")
    except ImportError:
        pass


# Register default providers on first access
_register_default_providers()
