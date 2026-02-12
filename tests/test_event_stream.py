"""Tests for event stream."""

import pytest
import asyncio

from mini_agent.ai.event_stream import (
    EventStream,
    AssistantMessageEventStream,
    Event,
    EventType,
)
from mini_agent.ai.types import StopReason


class TestEventStream:
    @pytest.mark.asyncio
    async def test_basic_iteration(self):
        stream = EventStream()

        async def producer():
            await asyncio.sleep(0.01)
            stream.push(Event(EventType.TEXT_DELTA, "hello"))
            stream.push(Event(EventType.TEXT_DELTA, " world"))
            stream.end()

        asyncio.create_task(producer())

        events = []
        async for event in stream:
            events.append(event)

        assert len(events) == 2
        assert events[0].data == "hello"
        assert events[1].data == " world"

    @pytest.mark.asyncio
    async def test_result(self):
        stream = EventStream()

        async def producer():
            await asyncio.sleep(0.01)
            from mini_agent.ai.types import AssistantMessage, TextContent
            msg = AssistantMessage(content=[TextContent(text="Hello")])
            stream.end(msg)

        asyncio.create_task(producer())

        result = await stream.result()
        assert result.text == "Hello"

    @pytest.mark.asyncio
    async def test_error(self):
        stream = EventStream()

        async def producer():
            await asyncio.sleep(0.01)
            stream.error(RuntimeError("Test error"))

        asyncio.create_task(producer())

        with pytest.raises(RuntimeError, match="Test error"):
            await stream.result()

    @pytest.mark.asyncio
    async def test_subscribe(self):
        stream = EventStream()
        received = []

        def callback(event):
            received.append(event)

        stream.subscribe(callback)

        stream.push(Event(EventType.TEXT_DELTA, "test"))
        stream.end()

        await asyncio.sleep(0.01)
        assert len(received) == 1
        assert received[0].data == "test"

    @pytest.mark.asyncio
    async def test_collect_text(self):
        stream = EventStream()

        async def producer():
            from mini_agent.ai.event_stream import TextEvent
            stream.push(Event(EventType.TEXT_DELTA, TextEvent(delta="Hello")))
            stream.push(Event(EventType.TEXT_DELTA, TextEvent(delta=" World")))
            stream.end()

        asyncio.create_task(producer())

        # Need to consume the stream
        text = await stream.collect_text()
        assert text == "Hello World"


class TestAssistantMessageEventStream:
    @pytest.mark.asyncio
    async def test_text_streaming(self):
        stream = AssistantMessageEventStream()

        stream.push_text_start(0)
        stream.push_text_delta("Hello", 0)
        stream.push_text_delta(" World", 0)
        stream.push_text_end(0)
        stream.end()

        msg = await stream.result()
        assert msg.text == "Hello World"

    @pytest.mark.asyncio
    async def test_tool_call_streaming(self):
        stream = AssistantMessageEventStream()

        stream.push_toolcall_start(index=0, id="call_123", name="")
        stream.push_toolcall_name_delta("test_tool", index=0)
        stream.push_toolcall_arguments_delta('{"key": ', index=0)
        stream.push_toolcall_arguments_delta('"value"}', index=0)
        stream.push_toolcall_end(index=0)
        stream.end()

        msg = await stream.result()
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].id == "call_123"
        assert msg.tool_calls[0].name == "test_tool"
        assert msg.tool_calls[0].arguments == {"key": "value"}

    @pytest.mark.asyncio
    async def test_multiple_content_blocks(self):
        stream = AssistantMessageEventStream()

        # Text
        stream.push_text_start(0)
        stream.push_text_delta("Hello", 0)
        stream.push_text_end(0)

        # Tool call
        stream.push_toolcall_start(index=0, id="call_1", name="tool")
        stream.push_toolcall_end(index=0)

        # More text
        stream.push_text_start(1)
        stream.push_text_delta("Done", 1)
        stream.push_text_end(1)

        stream.push_stop_reason(StopReason.TOOL_USE)
        stream.end()

        msg = await stream.result()
        assert len(msg.content) == 3
        assert msg.stop_reason == StopReason.TOOL_USE

    @pytest.mark.asyncio
    async def test_usage_tracking(self):
        stream = AssistantMessageEventStream()

        from mini_agent.ai.types import Usage
        stream.push_usage(Usage(input_tokens=100, output_tokens=50))
        stream.end()

        msg = await stream.result()
        assert msg.usage.input_tokens == 100
        assert msg.usage.output_tokens == 50
