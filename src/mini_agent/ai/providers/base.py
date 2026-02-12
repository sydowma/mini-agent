"""Provider base class."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from ..types import Context, Tool
from ..event_stream import AssistantMessageEventStream


@dataclass
class StreamOptions:
    """Options for streaming."""
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    stop_sequences: list[str] = None

    def __post_init__(self):
        if self.stop_sequences is None:
            self.stop_sequences = []


class Provider(ABC):
    """Base class for LLM providers."""

    @property
    @abstractmethod
    def api(self) -> str:
        """Return the API identifier (e.g., 'openai', 'anthropic')."""
        pass

    @property
    def default_model(self) -> str:
        """Return the default model for this provider."""
        return ""

    @abstractmethod
    async def stream(
        self,
        model: str,
        context: Context,
        options: Optional[StreamOptions] = None,
    ) -> AssistantMessageEventStream:
        """
        Stream a response from the LLM.

        Args:
            model: The model to use
            context: The conversation context
            options: Streaming options

        Returns:
            An event stream that yields streaming events
        """
        pass

    def validate_context(self, context: Context) -> None:
        """Validate the context before sending to the provider."""
        # Basic validation - can be overridden by subclasses
        if not context.messages:
            raise ValueError("Context must contain at least one message")

    def build_tools_schema(self, tools: list[Tool]) -> list[dict]:
        """Build the tools schema for the API."""
        return [tool.to_dict() for tool in tools]
