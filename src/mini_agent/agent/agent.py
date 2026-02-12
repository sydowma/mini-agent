"""Agent class implementation."""

import asyncio
from typing import Callable, Optional

from ..ai.types import AssistantMessage, Context
from ..ai.providers.base import StreamOptions
from ..ai.providers import get_provider
from .types import AgentContext, AgentState, AgentEvent, AgentEventType, AgentTool
from .loop import AgentLoop


class Agent:
    """
    Main Agent class.

    Provides a high-level interface for interacting with the coding agent.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        provider_name: str = "openai",
        system_prompt: Optional[str] = None,
        working_directory: str = ".",
    ):
        self.model = model
        self.provider_name = provider_name
        self.working_directory = working_directory

        # Initialize provider
        self.provider = get_provider(provider_name)
        if not self.provider:
            raise ValueError(f"Unknown provider: {provider_name}")

        # Initialize context
        self.context = AgentContext(
            context=Context(),
            tools={},
            system_prompt=system_prompt or self._default_system_prompt(),
            working_directory=working_directory,
        )

        # State
        self.state = AgentState.IDLE
        self._loop: Optional[AgentLoop] = None
        self._event_handlers: list[Callable[[AgentEvent], None]] = []

    def _default_system_prompt(self) -> str:
        """Return the default system prompt."""
        return """You are a helpful coding assistant with access to tools for reading, writing, and modifying files, as well as executing commands.

Guidelines:
- Always read files before modifying them
- Use the edit tool for targeted changes rather than rewriting entire files
- Be careful with file paths - use absolute paths
- Test your changes when appropriate
- Explain what you're doing as you work

Available tools:
- read: Read file contents
- write: Write content to a file
- edit: Make targeted edits to a file
- bash: Execute shell commands
- grep: Search file contents
- find: Find files by name
- ls: List directory contents"""

    def add_tool(self, tool) -> None:
        """Add a tool to the agent."""
        agent_tool = tool.to_agent_tool() if hasattr(tool, 'to_agent_tool') else tool
        self.context.add_tool(agent_tool)

    def add_tools(self, tools: list) -> None:
        """Add multiple tools to the agent."""
        for tool in tools:
            self.add_tool(tool)

    def on_event(self, handler: Callable[[AgentEvent], None]) -> None:
        """Register an event handler."""
        self._event_handlers.append(handler)

    def off_event(self, handler: Callable[[AgentEvent], None]) -> None:
        """Unregister an event handler."""
        if handler in self._event_handlers:
            self._event_handlers.remove(handler)

    async def prompt(
        self,
        text: str,
        max_iterations: int = 20,
    ) -> AssistantMessage:
        """
        Send a prompt to the agent and get a response.

        Args:
            text: The prompt text
            max_iterations: Maximum tool execution iterations

        Returns:
            The final assistant message
        """
        self.state = AgentState.IDLE
        self._loop = AgentLoop(
            context=self.context,
            provider=self.provider,
            model=self.model,
        )

        # Forward events
        def forward_event(event: AgentEvent):
            self.state = self._loop.state
            for handler in self._event_handlers:
                try:
                    handler(event)
                except Exception:
                    pass

        self._loop.on_event(forward_event)

        return await self._loop.run(text, max_iterations)

    def steer(self, text: str) -> None:
        """
        Send a steering message to modify ongoing behavior.

        This is for mid-stream intervention.
        """
        # For now, this is a placeholder
        # In a full implementation, this would inject a message
        # into the ongoing conversation
        pass

    async def follow_up(self, text: str) -> AssistantMessage:
        """
        Send a follow-up message in the same conversation.

        Args:
            text: The follow-up prompt text

        Returns:
            The assistant's response
        """
        return await self.prompt(text)

    def abort(self) -> None:
        """Abort the current operation."""
        if self._loop:
            self._loop.abort()
        self.state = AgentState.ABORTED

    def get_messages(self) -> list:
        """Get all messages in the conversation."""
        return list(self.context.context.messages)

    def clear_messages(self) -> None:
        """Clear the conversation history."""
        self.context.context.messages = []

    def save_session(self) -> dict:
        """Save the current session state."""
        return {
            "model": self.model,
            "provider": self.provider_name,
            "working_directory": self.working_directory,
            "context": self.context.context.to_dict(),
            "tools": list(self.context.tools.keys()),
        }

    def load_session(self, data: dict) -> None:
        """Load a session state."""
        self.model = data.get("model", self.model)
        self.working_directory = data.get("working_directory", self.working_directory)

        # Restore context
        if "context" in data:
            self.context.context = Context.from_dict(data["context"])


# Debug: patch prompt method
_original_prompt = Agent.prompt
async def _debug_prompt(self, text, max_iterations=20):
    with open("/tmp/mini-agent-events.log", "a") as f:
        f.write(f"[DEBUG AGENT] prompt called, handlers: {len(self._event_handlers)}\n")
    return await _original_prompt(self, text, max_iterations)
Agent.prompt = _debug_prompt
