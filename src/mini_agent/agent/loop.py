"""Agent loop implementation."""

import asyncio
from typing import AsyncIterator, Callable, Optional

from ..ai.types import Context, AssistantMessage, ToolResultMessage
from ..ai.event_stream import EventType
from ..ai.providers.base import StreamOptions
from .types import (
    AgentContext, AgentState, AgentEvent, AgentEventType,
    AgentTool, ToolExecution,
)


class AgentLoop:
    """
    The main agent loop.

    Handles the flow: prompt → stream → execute tools → continue
    """

    def __init__(
        self,
        context: AgentContext,
        provider,
        model: str,
        options: Optional[StreamOptions] = None,
    ):
        self.context = context
        self.provider = provider
        self.model = model
        self.options = options or StreamOptions()
        self.state = AgentState.IDLE
        self._abort_flag = False
        self._event_handlers: list[Callable[[AgentEvent], None]] = []

    def on_event(self, handler: Callable[[AgentEvent], None]) -> None:
        """Register an event handler."""
        self._event_handlers.append(handler)

    def emit(self, event: AgentEvent) -> None:
        """Emit an event to all handlers."""
        with open("/tmp/mini-agent-events.log", "a") as f:
            f.write(f"[DEBUG LOOP] Emitting: {event.type}\n")
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception as e:
                with open("/tmp/mini-agent-events.log", "a") as f:
                    f.write(f"[DEBUG LOOP] Handler error: {e}\n")

    def abort(self) -> None:
        """Abort the current operation."""
        self._abort_flag = True
        self.state = AgentState.ABORTED

    async def run(
        self,
        prompt: str,
        max_iterations: int = 20,
    ) -> AssistantMessage:
        """
        Run the agent loop with a prompt.

        Args:
            prompt: The user prompt
            max_iterations: Maximum number of tool execution iterations

        Returns:
            The final assistant message
        """
        self._abort_flag = False
        self.state = AgentState.IDLE

        # Add user message to context
        self.context.context.add_user_message(prompt)
        self.emit(AgentEvent(AgentEventType.PROMPT_START, {"prompt": prompt}))

        iteration = 0
        while iteration < max_iterations and not self._abort_flag:
            iteration += 1

            # Stream response
            self.state = AgentState.STREAMING
            self.emit(AgentEvent(AgentEventType.STREAM_START))

            message = await self._stream_response()

            if self._abort_flag:
                self.emit(AgentEvent(AgentEventType.ABORT))
                break

            # Add assistant message to context
            self.context.context.add_assistant_message(message)
            self.emit(AgentEvent(AgentEventType.RESPONSE_COMPLETE, message))

            # Check if we need to execute tools
            tool_calls = message.tool_calls
            if not tool_calls:
                break

            # Execute tools
            self.state = AgentState.EXECUTING_TOOLS
            results = await self._execute_tools(tool_calls)

            # Add tool results to context
            for result in results:
                self.context.context.add_tool_result(
                    tool_call_id=result.tool_call_id,
                    content=result.result or result.error or "",
                    is_error=result.error is not None,
                )

            if self._abort_flag:
                self.emit(AgentEvent(AgentEventType.ABORT))
                break

        self.state = AgentState.IDLE

        # Return the last assistant message
        for msg in reversed(self.context.context.messages):
            if isinstance(msg, AssistantMessage):
                return msg

        return AssistantMessage()

    async def _stream_response(self) -> AssistantMessage:
        """Stream a response from the LLM."""
        with open("/tmp/mini-agent-events.log", "a") as f:
            f.write(f"[DEBUG LOOP] Starting stream for model: {self.model}\n")

        stream = await self.provider.stream(
            model=self.model,
            context=self.context.context,
            options=self.options,
        )

        current_text = ""
        current_thinking = ""

        with open("/tmp/mini-agent-events.log", "a") as f:
            f.write("[DEBUG LOOP] Stream created, iterating...\n")

        async for event in stream:
            if self._abort_flag:
                break

            with open("/tmp/mini-agent-events.log", "a") as f:
                f.write(f"[DEBUG LOOP] Stream event: {event.type}\n")

            if event.type == EventType.TEXT_DELTA:
                delta = event.data.delta if hasattr(event.data, 'delta') else str(event.data)
                current_text += delta
                with open("/tmp/mini-agent-events.log", "a") as f:
                    f.write(f"[DEBUG LOOP] Text delta: {delta[:30]}...\n")
                self.emit(AgentEvent(AgentEventType.STREAM_TEXT, {"delta": delta}))

            elif event.type == EventType.THINKING_DELTA:
                delta = event.data.delta if hasattr(event.data, 'delta') else str(event.data)
                current_thinking += delta
                self.emit(AgentEvent(AgentEventType.STREAM_THINKING, {"delta": delta}))

            elif event.type == EventType.TOOLCALL_START:
                self.emit(AgentEvent(AgentEventType.TOOL_CALL, {
                    "index": event.data.index,
                    "id": event.data.id,
                    "name": event.data.name,
                }))

        return await stream.result()

    async def _execute_tools(self, tool_calls: list) -> list[ToolExecution]:
        """Execute a list of tool calls."""
        results = []

        # Execute tools concurrently
        tasks = []
        for tc in tool_calls:
            task = asyncio.create_task(self._execute_single_tool(tc.id, tc.name, tc.arguments))
            tasks.append(task)

        for future in asyncio.as_completed(tasks):
            try:
                result = await future
                results.append(result)
            except Exception as e:
                # This shouldn't happen as errors are caught in _execute_single_tool
                pass

        return results

    async def _execute_single_tool(
        self,
        tool_call_id: str,
        tool_name: str,
        arguments: dict,
    ) -> ToolExecution:
        """Execute a single tool call."""
        execution = ToolExecution(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            arguments=arguments,
        )

        self.emit(AgentEvent(AgentEventType.TOOL_CALL, {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "status": "started",
        }))

        try:
            tool = self.context.get_tool(tool_name)
            if not tool:
                execution.error = f"Unknown tool: {tool_name}"
                execution.is_complete = True
                self.emit(AgentEvent(AgentEventType.TOOL_RESULT, execution.to_dict()))
                return execution

            # Execute the tool
            result = await tool.execute(arguments)
            execution.result = str(result)
            execution.is_complete = True

        except Exception as e:
            execution.error = f"Tool execution error: {e}"
            execution.is_complete = True

        self.emit(AgentEvent(AgentEventType.TOOL_RESULT, execution.to_dict()))
        return execution
