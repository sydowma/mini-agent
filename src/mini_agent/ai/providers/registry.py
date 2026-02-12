"""Provider registry."""

from typing import Optional, Type

from .base import Provider


class ProviderRegistry:
    """Registry for LLM providers."""

    _providers: dict[str, Type[Provider]] = {}

    @classmethod
    def register(cls, api_name: str) -> callable:
        """Register a provider class with explicit API name."""
        def decorator(provider_class: Type[Provider]) -> Type[Provider]:
            cls._providers[api_name] = provider_class
            return provider_class
        return decorator

    @classmethod
    def register_class(cls, provider_class: Type[Provider], api_name: str) -> Type[Provider]:
        """Register a provider class directly."""
        cls._providers[api_name] = provider_class
        return provider_class

    @classmethod
    def get(cls, api: str) -> Optional[Provider]:
        """Get a provider instance by API name."""
        provider_class = cls._providers.get(api)
        if provider_class:
            return provider_class()
        return None

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered providers."""
        return list(cls._providers.keys())


def get_provider(api: str) -> Optional[Provider]:
    """Get a provider instance by API name."""
    return ProviderRegistry.get(api)
