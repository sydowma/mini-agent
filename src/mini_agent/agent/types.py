"""Agent type definitions."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Union

from ..ai.types import Context, Tool, AssistantMessage, ToolCall


class AgentEventType(Enum):
    """Types of agent events."""
    PROMPT_START = "prompt_start"
    STREAM_START = "stream_start"
    STREAM_TEXT = "stream_text"
    STREAM_THINKING = "stream_thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    RESPONSE_COMPLETE = "response_complete"
    ERROR = "error"
    ABORT = "abort"


@dataclass
class AgentEvent:
    """An event from the agent."""
    type: AgentEventType
    data: Any = None

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "data": self.data,
        }


@dataclass
class AgentTool:
    """
    A tool that can be used by the agent.

    Combines the Tool definition with an execution function.
    """
    name: str
    description: str
    input_schema: dict
    execute: Callable[[dict], Union[str, Any]]
    requires_confirmation: bool = False

    def to_tool(self) -> Tool:
        """Convert to LLM Tool definition."""
        return Tool(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
        )


@dataclass
class AgentContext:
    """Context for agent execution."""
    context: Context = field(default_factory=Context)
    tools: dict[str, AgentTool] = field(default_factory=dict)
    system_prompt: str = ""
    working_directory: str = "."

    def add_tool(self, tool: AgentTool) -> None:
        """Add a tool to the context."""
        self.tools[tool.name] = tool
        self.context.tools.append(tool.to_tool())

    def get_tool(self, name: str) -> Optional[AgentTool]:
        """Get a tool by name."""
        return self.tools.get(name)

    def to_dict(self) -> dict:
        return {
            "context": self.context.to_dict(),
            "tools": list(self.tools.keys()),
            "system_prompt": self.system_prompt,
            "working_directory": self.working_directory,
        }


class AgentState(Enum):
    """State of the agent."""
    IDLE = "idle"
    STREAMING = "streaming"
    EXECUTING_TOOLS = "executing_tools"
    ABORTED = "aborted"
    ERROR = "error"


@dataclass
class ToolExecution:
    """Represents a tool execution in progress."""
    tool_call_id: str
    tool_name: str
    arguments: dict
    result: Optional[str] = None
    error: Optional[str] = None
    is_complete: bool = False

    def to_dict(self) -> dict:
        return {
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "error": self.error,
            "is_complete": self.is_complete,
        }
