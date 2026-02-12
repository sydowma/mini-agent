"""Tests for AI types."""

import pytest
import json

from mini_agent.ai.types import (
    TextContent,
    ThinkingContent,
    ToolCall,
    ImageContent,
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    Context,
    Tool,
    Usage,
    StopReason,
)


class TestTextContent:
    def test_create(self):
        content = TextContent(text="Hello")
        assert content.text == "Hello"
        assert content.type == "text"

    def test_serialize(self):
        content = TextContent(text="Hello")
        data = content.to_dict()
        assert data["text"] == "Hello"
        assert data["type"] == "text"

    def test_deserialize(self):
        content = TextContent.from_dict({"text": "World", "type": "text"})
        assert content.text == "World"

    def test_empty(self):
        content = TextContent()
        assert content.text == ""
        assert content.type == "text"


class TestThinkingContent:
    def test_create(self):
        content = ThinkingContent(text="Thinking...", signature="abc123")
        assert content.text == "Thinking..."
        assert content.signature == "abc123"

    def test_serialize(self):
        content = ThinkingContent(text="Thinking...", signature="abc123")
        data = content.to_dict()
        assert data["text"] == "Thinking..."
        assert data["signature"] == "abc123"

    def test_serialize_no_signature(self):
        content = ThinkingContent(text="Thinking...")
        data = content.to_dict()
        assert "signature" not in data


class TestToolCall:
    def test_create(self):
        tc = ToolCall(id="123", name="test_tool", arguments={"key": "value"})
        assert tc.id == "123"
        assert tc.name == "test_tool"
        assert tc.arguments == {"key": "value"}

    def test_serialize(self):
        tc = ToolCall(id="123", name="test_tool", arguments={"key": "value"})
        data = tc.to_dict()
        assert data["id"] == "123"
        assert data["type"] == "function"
        assert data["function"]["name"] == "test_tool"
        # Arguments should be JSON string
        assert json.loads(data["function"]["arguments"]) == {"key": "value"}

    def test_deserialize(self):
        data = {
            "id": "123",
            "function": {
                "name": "test_tool",
                "arguments": '{"key": "value"}'
            }
        }
        tc = ToolCall.from_dict(data)
        assert tc.id == "123"
        assert tc.name == "test_tool"
        assert tc.arguments == {"key": "value"}

    def test_deserialize_with_dict_args(self):
        data = {
            "id": "123",
            "function": {
                "name": "test_tool",
                "arguments": {"key": "value"}
            }
        }
        tc = ToolCall.from_dict(data)
        assert tc.arguments == {"key": "value"}

    def test_empty_arguments(self):
        tc = ToolCall(id="123", name="test", arguments={})
        data = tc.to_dict()
        assert json.loads(data["function"]["arguments"]) == {}


class TestImageContent:
    def test_create(self):
        img = ImageContent(
            source_type="base64",
            media_type="image/png",
            data="abc123"
        )
        assert img.source_type == "base64"
        assert img.media_type == "image/png"
        assert img.data == "abc123"

    def test_serialize(self):
        img = ImageContent(
            source_type="base64",
            media_type="image/png",
            data="abc123"
        )
        data = img.to_dict()
        assert data["type"] == "image"
        assert data["source"]["type"] == "base64"


class TestUserMessage:
    def test_from_text(self):
        msg = UserMessage.from_text("Hello")
        assert msg.role == "user"
        assert len(msg.content) == 1
        assert msg.content[0].text == "Hello"

    def test_serialize(self):
        msg = UserMessage.from_text("Hello")
        data = msg.to_dict()
        assert data["role"] == "user"
        assert len(data["content"]) == 1

    def test_deserialize(self):
        data = {
            "role": "user",
            "content": [{"type": "text", "text": "Hello"}]
        }
        msg = UserMessage.from_dict(data)
        assert msg.role == "user"
        assert msg.content[0].text == "Hello"


class TestAssistantMessage:
    def test_text_property(self):
        msg = AssistantMessage(content=[
            TextContent(text="Hello "),
            TextContent(text="World"),
        ])
        assert msg.text == "Hello World"

    def test_tool_calls_property(self):
        msg = AssistantMessage(content=[
            TextContent(text="Result"),
            ToolCall(id="1", name="tool1", arguments={}),
            ToolCall(id="2", name="tool2", arguments={}),
        ])
        assert len(msg.tool_calls) == 2

    def test_empty_text(self):
        msg = AssistantMessage(content=[
            ToolCall(id="1", name="tool", arguments={})
        ])
        assert msg.text == ""

    def test_serialize(self):
        msg = AssistantMessage(
            content=[TextContent(text="Hello")],
            stop_reason=StopReason.END_TURN,
            usage=Usage(input_tokens=10, output_tokens=5)
        )
        data = msg.to_dict()
        assert data["role"] == "assistant"
        assert data["stop_reason"] == "end_turn"
        assert data["usage"]["input_tokens"] == 10

    def test_deserialize(self):
        data = {
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello"}],
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 10, "output_tokens": 5}
        }
        msg = AssistantMessage.from_dict(data)
        assert msg.role == "assistant"
        assert msg.stop_reason == StopReason.TOOL_USE
        assert msg.usage.input_tokens == 10


class TestToolResultMessage:
    def test_create(self):
        msg = ToolResultMessage(
            tool_call_id="call_123",
            content="Result text",
            is_error=False
        )
        assert msg.tool_call_id == "call_123"
        assert msg.content == "Result text"
        assert not msg.is_error

    def test_serialize(self):
        msg = ToolResultMessage(tool_call_id="call_123", content="Result")
        data = msg.to_dict()
        assert data["tool_call_id"] == "call_123"
        assert data["content"] == "Result"

    def test_error_result(self):
        msg = ToolResultMessage(
            tool_call_id="call_123",
            content="Error: something failed",
            is_error=True
        )
        assert msg.is_error


class TestContext:
    def test_empty(self):
        ctx = Context()
        assert len(ctx.messages) == 0
        assert len(ctx.tools) == 0

    def test_add_user_message(self):
        ctx = Context()
        ctx.add_user_message("Hello")
        assert len(ctx.messages) == 1
        assert isinstance(ctx.messages[0], UserMessage)

    def test_add_assistant_message(self):
        ctx = Context()
        msg = AssistantMessage(content=[TextContent(text="Hi")])
        ctx.add_assistant_message(msg)
        assert len(ctx.messages) == 1
        assert isinstance(ctx.messages[0], AssistantMessage)

    def test_add_tool_result(self):
        ctx = Context()
        ctx.add_tool_result("call_123", "result text")
        assert len(ctx.messages) == 1
        assert ctx.messages[0].tool_call_id == "call_123"

    def test_copy(self):
        ctx = Context()
        ctx.add_user_message("Hello")
        ctx.system_prompt = "Be helpful"

        ctx_copy = ctx.copy()
        assert len(ctx_copy.messages) == 1
        assert ctx_copy.system_prompt == "Be helpful"

        # Modify original - copy should be independent
        ctx.add_user_message("World")
        assert len(ctx.messages) == 2
        assert len(ctx_copy.messages) == 1

    def test_serialize_deserialize(self):
        ctx = Context()
        ctx.system_prompt = "Be helpful"
        ctx.add_user_message("Hello")
        ctx.add_tool_result("call_123", "result")

        data = ctx.to_dict()
        ctx2 = Context.from_dict(data)

        assert len(ctx2.messages) == 2
        assert ctx2.system_prompt == "Be helpful"


class TestTool:
    def test_create(self):
        tool = Tool(
            name="read",
            description="Read a file",
            input_schema={"type": "object"}
        )
        assert tool.name == "read"

    def test_to_dict(self):
        tool = Tool(
            name="read",
            description="Read a file",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}}
        )
        data = tool.to_dict()
        assert data["type"] == "function"
        assert data["function"]["name"] == "read"
        assert data["function"]["description"] == "Read a file"


class TestUsage:
    def test_create(self):
        usage = Usage(input_tokens=10, output_tokens=5)
        assert usage.input_tokens == 10
        assert usage.output_tokens == 5

    def test_add(self):
        u1 = Usage(input_tokens=10, output_tokens=5)
        u2 = Usage(input_tokens=20, output_tokens=10)
        result = u1 + u2
        assert result.input_tokens == 30
        assert result.output_tokens == 15

    def test_cache_tokens(self):
        usage = Usage(
            input_tokens=10,
            output_tokens=5,
            cache_read_tokens=3,
            cache_write_tokens=2
        )
        assert usage.cache_read_tokens == 3
        assert usage.cache_write_tokens == 2


class TestStopReason:
    def test_values(self):
        assert StopReason.END_TURN.value == "end_turn"
        assert StopReason.TOOL_USE.value == "tool_use"
        assert StopReason.MAX_TOKENS.value == "max_tokens"
        assert StopReason.ERROR.value == "error"
