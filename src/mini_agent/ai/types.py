"""Core message types for mini-agent."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union
import json


class StopReason(Enum):
    """Reason for stopping generation."""
    END_TURN = "end_turn"
    TOOL_USE = "tool_use"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"
    ERROR = "error"


@dataclass
class TextContent:
    """Text content in a message."""
    type: str = "text"
    text: str = ""

    def to_dict(self) -> dict:
        return {"type": self.type, "text": self.text}

    @classmethod
    def from_dict(cls, data: dict) -> "TextContent":
        return cls(type=data.get("type", "text"), text=data.get("text", ""))


@dataclass
class ThinkingContent:
    """Thinking/reasoning content in a message."""
    type: str = "thinking"
    text: str = ""
    signature: Optional[str] = None

    def to_dict(self) -> dict:
        result = {"type": self.type, "text": self.text}
        if self.signature:
            result["signature"] = self.signature
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "ThinkingContent":
        return cls(
            type=data.get("type", "thinking"),
            text=data.get("text", ""),
            signature=data.get("signature"),
        )


@dataclass
class ImageContent:
    """Image content in a message."""
    type: str = "image"
    source_type: str = "base64"  # base64, url
    media_type: str = ""  # image/png, image/jpeg, etc.
    data: str = ""  # base64 data or url

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "source": {
                "type": self.source_type,
                "media_type": self.media_type,
                "data": self.data,
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ImageContent":
        source = data.get("source", {})
        return cls(
            type=data.get("type", "image"),
            source_type=source.get("type", "base64"),
            media_type=source.get("media_type", ""),
            data=source.get("data", ""),
        )


@dataclass
class ToolCall:
    """Tool call in a message."""
    id: str
    name: str
    arguments: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": json.dumps(self.arguments) if self.arguments else "{}",
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ToolCall":
        func = data.get("function", {})
        args = func.get("arguments", "{}")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        return cls(
            id=data.get("id", ""),
            name=func.get("name", ""),
            arguments=args,
        )


@dataclass
class Tool:
    """Tool definition for LLM."""
    name: str
    description: str
    input_schema: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Tool":
        func = data.get("function", {})
        return cls(
            name=func.get("name", ""),
            description=func.get("description", ""),
            input_schema=func.get("parameters", {}),
        )


@dataclass
class Usage:
    """Token usage information."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def to_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Usage":
        return cls(
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            cache_read_tokens=data.get("cache_read_tokens", 0),
            cache_write_tokens=data.get("cache_write_tokens", 0),
        )

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
            cache_write_tokens=self.cache_write_tokens + other.cache_write_tokens,
        )


ContentBlock = Union[TextContent, ThinkingContent, ImageContent, ToolCall]


@dataclass
class UserMessage:
    """User message."""
    role: str = "user"
    content: list[ContentBlock] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": [c.to_dict() for c in self.content],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserMessage":
        content = []
        for block in data.get("content", []):
            block_type = block.get("type", "text")
            if block_type == "text":
                content.append(TextContent.from_dict(block))
            elif block_type == "image":
                content.append(ImageContent.from_dict(block))
        return cls(role="user", content=content)

    @classmethod
    def from_text(cls, text: str) -> "UserMessage":
        return cls(role="user", content=[TextContent(text=text)])


@dataclass
class AssistantMessage:
    """Assistant message."""
    role: str = "assistant"
    content: list[Union[ContentBlock, ToolCall]] = field(default_factory=list)
    stop_reason: StopReason = StopReason.END_TURN
    usage: Usage = field(default_factory=Usage)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": [c.to_dict() for c in self.content],
            "stop_reason": self.stop_reason.value,
            "usage": self.usage.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AssistantMessage":
        content = []
        for block in data.get("content", []):
            block_type = block.get("type", "text")
            if block_type == "text":
                content.append(TextContent.from_dict(block))
            elif block_type == "thinking":
                content.append(ThinkingContent.from_dict(block))
            elif block_type == "image":
                content.append(ImageContent.from_dict(block))
            elif block.get("function"):  # tool call
                content.append(ToolCall.from_dict(block))

        stop_reason = StopReason.END_TURN
        if data.get("stop_reason"):
            try:
                stop_reason = StopReason(data["stop_reason"])
            except ValueError:
                pass

        return cls(
            role="assistant",
            content=content,
            stop_reason=stop_reason,
            usage=Usage.from_dict(data.get("usage", {})),
        )

    @property
    def text(self) -> str:
        """Get all text content."""
        texts = []
        for block in self.content:
            if isinstance(block, TextContent):
                texts.append(block.text)
        return "".join(texts)

    @property
    def tool_calls(self) -> list[ToolCall]:
        """Get all tool calls."""
        return [b for b in self.content if isinstance(b, ToolCall)]


@dataclass
class ToolResultMessage:
    """Tool result message."""
    role: str = "user"
    tool_call_id: str = ""
    content: str = ""
    is_error: bool = False

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "tool_call_id": self.tool_call_id,
            "content": self.content,
            "is_error": self.is_error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ToolResultMessage":
        return cls(
            role="user",
            tool_call_id=data.get("tool_call_id", ""),
            content=data.get("content", ""),
            is_error=data.get("is_error", False),
        )


Message = Union[UserMessage, AssistantMessage, ToolResultMessage]


@dataclass
class Context:
    """Context for LLM calls."""
    messages: list[Message] = field(default_factory=list)
    tools: list[Tool] = field(default_factory=list)
    system_prompt: str = ""

    def add_message(self, message: Message) -> None:
        self.messages.append(message)

    def add_user_message(self, text: str) -> None:
        self.messages.append(UserMessage.from_text(text))

    def add_assistant_message(self, message: AssistantMessage) -> None:
        self.messages.append(message)

    def add_tool_result(self, tool_call_id: str, content: str, is_error: bool = False) -> None:
        self.messages.append(ToolResultMessage(
            tool_call_id=tool_call_id,
            content=content,
            is_error=is_error,
        ))

    def to_dict(self) -> dict:
        return {
            "messages": [m.to_dict() for m in self.messages],
            "tools": [t.to_dict() for t in self.tools],
            "system_prompt": self.system_prompt,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Context":
        ctx = cls()
        ctx.system_prompt = data.get("system_prompt", "")

        for msg_data in data.get("messages", []):
            role = msg_data.get("role", "user")
            if role == "user":
                if msg_data.get("tool_call_id"):
                    ctx.messages.append(ToolResultMessage.from_dict(msg_data))
                else:
                    ctx.messages.append(UserMessage.from_dict(msg_data))
            elif role == "assistant":
                ctx.messages.append(AssistantMessage.from_dict(msg_data))

        for tool_data in data.get("tools", []):
            ctx.tools.append(Tool.from_dict(tool_data))

        return ctx

    def copy(self) -> "Context":
        """Create a deep copy of the context."""
        return Context.from_dict(self.to_dict())
