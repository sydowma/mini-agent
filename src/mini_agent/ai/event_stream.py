"""EventStream implementation for async streaming."""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Callable, Optional

from .types import AssistantMessage, StopReason, Usage


class EventType(Enum):
    """Types of streaming events."""
    START = "start"
    TEXT_START = "text_start"
    TEXT_DELTA = "text_delta"
    TEXT_END = "text_end"
    THINKING_START = "thinking_start"
    THINKING_DELTA = "thinking_delta"
    THINKING_END = "thinking_end"
    TOOLCALL_START = "toolcall_start"
    TOOLCALL_DELTA = "toolcall_delta"
    TOOLCALL_END = "toolcall_end"
    USAGE = "usage"
    DONE = "done"
    ERROR = "error"


@dataclass
class Event:
    """A streaming event."""
    type: EventType
    data: Any = None

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "data": self.data,
        }


@dataclass
class TextEvent:
    """Text streaming event data."""
    index: int = 0
    delta: str = ""


@dataclass
class ThinkingEvent:
    """Thinking streaming event data."""
    index: int = 0
    delta: str = ""


@dataclass
class ToolCallEvent:
    """Tool call streaming event data."""
    index: int = 0
    id: str = ""
    name: str = ""
    arguments_delta: str = ""


class EventStream:
    """
    Async event stream for LLM responses.

    Usage:
        stream = EventStream()

        # Producer
        async def producer():
            stream.push(Event(EventType.TEXT_DELTA, "Hello"))
            stream.end(message)

        # Consumer
        async for event in stream:
            print(event)
    """

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._ended = False
        self._result: Optional[AssistantMessage] = None
        self._error: Optional[Exception] = None
        self._subscribers: list[Callable[[Event], None]] = []

    def push(self, event: Event) -> None:
        """Push an event to the stream."""
        if self._ended:
            return
        self._queue.put_nowait(event)
        # Notify subscribers
        for sub in self._subscribers:
            try:
                sub(event)
            except Exception:
                pass

    def end(self, message: Optional[AssistantMessage] = None) -> None:
        """End the stream with an optional final message."""
        self._result = message
        self._ended = True
        self._queue.put_nowait(Event(EventType.DONE, message))

    def error(self, error: Exception) -> None:
        """End the stream with an error."""
        self._error = error
        self._ended = True
        self._queue.put_nowait(Event(EventType.ERROR, str(error)))

    def subscribe(self, callback: Callable[[Event], None]) -> None:
        """Subscribe to events."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Event], None]) -> None:
        """Unsubscribe from events."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def result(self) -> AssistantMessage:
        """Wait for and return the final result."""
        if self._error:
            raise self._error
        if self._result is not None:
            return self._result

        # Consume remaining events
        async for _ in self:
            pass

        if self._error:
            raise self._error
        if self._result is None:
            raise RuntimeError("Stream ended without result")
        return self._result

    def __aiter__(self) -> "EventStream":
        return self

    async def __anext__(self) -> Event:
        if self._error:
            raise self._error

        try:
            event = await self._queue.get()
            if event.type == EventType.DONE:
                raise StopAsyncIteration
            if event.type == EventType.ERROR:
                raise RuntimeError(event.data) if isinstance(event.data, str) else event.data
            return event
        except asyncio.CancelledError:
            raise StopAsyncIteration

    async def collect_text(self) -> str:
        """Collect all text from the stream."""
        text_parts = []
        async for event in self:
            if event.type == EventType.TEXT_DELTA:
                text_parts.append(event.data.delta if hasattr(event.data, 'delta') else str(event.data))
        return "".join(text_parts)


class AssistantMessageEventStream(EventStream):
    """
    Specialized event stream for assistant messages.

    Provides convenient methods for building assistant messages
    while streaming.
    """

    def __init__(self):
        super().__init__()
        self._text_buffers: dict[int, str] = {}
        self._thinking_buffers: dict[int, str] = {}
        self._tool_call_buffers: dict[int, dict] = {}
        self._usage = Usage()
        self._stop_reason = StopReason.END_TURN

    def push_text_start(self, index: int = 0) -> None:
        """Signal start of text content."""
        self.push(Event(EventType.TEXT_START, TextEvent(index=index)))

    def push_text_delta(self, delta: str, index: int = 0) -> None:
        """Push text delta."""
        self._text_buffers[index] = self._text_buffers.get(index, "") + delta
        self.push(Event(EventType.TEXT_DELTA, TextEvent(index=index, delta=delta)))

    def push_text_end(self, index: int = 0) -> None:
        """Signal end of text content."""
        self.push(Event(EventType.TEXT_END, TextEvent(index=index)))

    def push_thinking_start(self, index: int = 0) -> None:
        """Signal start of thinking content."""
        self.push(Event(EventType.THINKING_START, ThinkingEvent(index=index)))

    def push_thinking_delta(self, delta: str, index: int = 0) -> None:
        """Push thinking delta."""
        self._thinking_buffers[index] = self._thinking_buffers.get(index, "") + delta
        self.push(Event(EventType.THINKING_DELTA, ThinkingEvent(index=index, delta=delta)))

    def push_thinking_end(self, index: int = 0) -> None:
        """Signal end of thinking content."""
        self.push(Event(EventType.THINKING_END, ThinkingEvent(index=index)))

    def push_toolcall_start(self, index: int = 0, id: str = "", name: str = "") -> None:
        """Signal start of tool call."""
        self._tool_call_buffers[index] = {"id": id, "name": name, "arguments": ""}
        self.push(Event(EventType.TOOLCALL_START, ToolCallEvent(
            index=index, id=id, name=name
        )))

    def push_toolcall_name_delta(self, delta: str, index: int = 0) -> None:
        """Push tool name delta."""
        if index in self._tool_call_buffers:
            self._tool_call_buffers[index]["name"] += delta
        self.push(Event(EventType.TOOLCALL_DELTA, ToolCallEvent(
            index=index, name=delta
        )))

    def push_toolcall_arguments_delta(self, delta: str, index: int = 0) -> None:
        """Push tool arguments delta."""
        if index in self._tool_call_buffers:
            self._tool_call_buffers[index]["arguments"] += delta
        self.push(Event(EventType.TOOLCALL_DELTA, ToolCallEvent(
            index=index, arguments_delta=delta
        )))

    def push_toolcall_end(self, index: int = 0) -> None:
        """Signal end of tool call."""
        self.push(Event(EventType.TOOLCALL_END, ToolCallEvent(index=index)))

    def push_usage(self, usage: Usage) -> None:
        """Push usage information."""
        self._usage = usage
        self.push(Event(EventType.USAGE, usage))

    def push_stop_reason(self, reason: StopReason) -> None:
        """Set stop reason."""
        self._stop_reason = reason

    def build_message(self) -> AssistantMessage:
        """Build the final assistant message from collected data."""
        from .types import TextContent, ThinkingContent, ToolCall

        content = []

        # Sort by index and add content
        for idx in sorted(self._text_buffers.keys()):
            content.append(TextContent(text=self._text_buffers[idx]))

        for idx in sorted(self._thinking_buffers.keys()):
            content.append(ThinkingContent(text=self._thinking_buffers[idx]))

        for idx in sorted(self._tool_call_buffers.keys()):
            tc_data = self._tool_call_buffers[idx]
            import json
            try:
                args = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
            except json.JSONDecodeError:
                args = {}
            content.append(ToolCall(
                id=tc_data["id"],
                name=tc_data["name"],
                arguments=args,
            ))

        return AssistantMessage(
            content=content,
            stop_reason=self._stop_reason,
            usage=self._usage,
        )

    def end(self, message: Optional[AssistantMessage] = None) -> None:
        """End the stream, building message if not provided."""
        if message is None:
            message = self.build_message()
        super().end(message)
