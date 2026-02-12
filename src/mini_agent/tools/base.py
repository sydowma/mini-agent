"""Base class for tools."""

from abc import ABC, abstractmethod
from typing import Any, Union

from pydantic import BaseModel
from ..agent.types import AgentTool


class BaseTool(ABC):
    """Base class for all tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the tool name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return the tool description."""
        pass

    @property
    def input_schema(self) -> dict:
        """Return the JSON schema for input parameters."""
        return {}

    @abstractmethod
    async def execute(self, arguments: dict) -> str:
        """Execute the tool with given arguments."""
        pass

    def to_agent_tool(self) -> AgentTool:
        """Convert to AgentTool."""
        return AgentTool(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
            execute=self.execute,
        )

    def validate_arguments(self, arguments: dict) -> dict:
        """Validate arguments against the schema."""
        # Subclasses can override for custom validation
        return arguments
