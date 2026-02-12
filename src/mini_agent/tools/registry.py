"""Tool registry."""

from typing import Optional, Type

from .base import BaseTool


class ToolRegistry:
    """Registry for tools."""

    _tools: dict[str, Type[BaseTool]] = {}

    @classmethod
    def register(cls, tool_class: Type[BaseTool]) -> Type[BaseTool]:
        """Register a tool class."""
        instance = tool_class()
        cls._tools[instance.name] = tool_class
        return tool_class

    @classmethod
    def get(cls, name: str) -> Optional[BaseTool]:
        """Get a tool instance by name."""
        tool_class = cls._tools.get(name)
        if tool_class:
            return tool_class()
        return None

    @classmethod
    def list_tools(cls) -> list[str]:
        """List all registered tools."""
        return list(cls._tools.keys())

    @classmethod
    def get_all(cls) -> dict[str, BaseTool]:
        """Get all registered tool instances."""
        return {name: tool_class() for name, tool_class in cls._tools.items()}


def register_tool(tool_class: Type[BaseTool]) -> Type[BaseTool]:
    """Decorator to register a tool."""
    return ToolRegistry.register(tool_class)


def get_tool(name: str) -> Optional[BaseTool]:
    """Get a tool instance by name."""
    return ToolRegistry.get(name)


def list_tools() -> list[str]:
    """List all registered tools."""
    return ToolRegistry.list_tools()
