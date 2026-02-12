"""Anthropic Claude provider implementation."""

import asyncio
import json
from typing import Optional

from anthropic import AsyncAnthropic

from ..types import (
    Context, Tool, StopReason, Usage,
    UserMessage, AssistantMessage, TextContent, ToolCall, ThinkingContent
)
from ..event_stream import AssistantMessageEventStream
from .base import Provider, StreamOptions


class AnthropicProvider(Provider):
    """Anthropic Claude API provider."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self._api_key = api_key
        self._base_url = base_url
        self._client: Optional[AsyncAnthropic] = None

    def _get_client(self) -> AsyncAnthropic:
        """Lazy-initialize the Anthropic client."""
        if self._client is None:
            self._client = AsyncAnthropic(
                api_key=self._api_key,
                base_url=self._base_url
            )
        return self._client

    @property
    def api(self) -> str:
        return "anthropic"

    @property
    def default_model(self) -> str:
        return "claude-sonnet-4-20250514"

    async def stream(
        self,
        model: str,
        context: Context,
        options: Optional[StreamOptions] = None,
    ) -> AssistantMessageEventStream:
        """Stream a response from Anthropic."""
        self.validate_context(context)
        options = options or StreamOptions()

        stream = AssistantMessageEventStream()

        # Start streaming task
        asyncio.create_task(self._stream_task(model, context, options, stream))

        return stream

    async def _stream_task(
        self,
        model: str,
        context: Context,
        options: StreamOptions,
        stream: AssistantMessageEventStream,
    ) -> None:
        """Background task for streaming."""
        try:
            client = self._get_client()

            # Build messages in Anthropic format
            messages = self._build_messages(context)
            system = context.system_prompt or None
            tools = self._build_tools(context.tools) if context.tools else None

            # Create streaming response
            kwargs = {
                "model": model,
                "messages": messages,
                "max_tokens": options.max_tokens,
            }

            if system:
                kwargs["system"] = system
            if tools:
                kwargs["tools"] = tools
            if options.stop_sequences:
                kwargs["stop_sequences"] = options.stop_sequences

            async with client.messages.stream(**kwargs) as response:
                await self._process_stream(response, stream)

        except Exception as e:
            stream.error(e)

    def _build_messages(self, context: Context) -> list[dict]:
        """Build Anthropic message format from context.

        Anthropic uses a different format than OpenAI:
        - content is always a list of content blocks
        - tool_result has a specific format
        - No separate system role (uses system parameter)
        """
        messages = []

        for msg in context.messages:
            if isinstance(msg, UserMessage):
                content = []
                for block in msg.content:
                    if isinstance(block, TextContent):
                        content.append({"type": "text", "text": block.text})
                    elif hasattr(block, 'source'):  # ImageContent
                        content.append({
                            "type": "image",
                            "source": {
                                "type": block.source_type,
                                "media_type": block.media_type,
                                "data": block.data,
                            }
                        })

                if content:
                    messages.append({"role": "user", "content": content})

            elif isinstance(msg, AssistantMessage):
                content = []

                for block in msg.content:
                    if isinstance(block, TextContent):
                        content.append({"type": "text", "text": block.text})
                    elif isinstance(block, ThinkingContent):
                        content.append({
                            "type": "thinking",
                            "thinking": block.text,
                        })
                    elif isinstance(block, ToolCall):
                        content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.arguments,
                        })

                if content:
                    messages.append({"role": "assistant", "content": content})

            elif hasattr(msg, 'tool_call_id'):  # ToolResultMessage
                # Anthropic tool_result format
                tool_result_content = msg.content
                if msg.is_error:
                    tool_result_content = {"type": "text", "text": f"Error: {msg.content}"}
                else:
                    tool_result_content = {"type": "text", "text": msg.content}

                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id,
                        "content": [tool_result_content] if isinstance(tool_result_content, dict) else tool_result_content,
                        "is_error": msg.is_error,
                    }]
                })

        return messages

    def _build_tools(self, tools: list[Tool]) -> list[dict]:
        """Build Anthropic tools format."""
        result = []
        for tool in tools:
            result.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            })
        return result

    async def _process_stream(
        self,
        response,
        stream: AssistantMessageEventStream,
    ) -> None:
        """Process the streaming response from Anthropic."""
        current_content = {}  # index -> content block info
        current_text_index = None
        current_thinking_index = None
        total_usage = Usage()

        async for event in response:
            event_type = event.type if hasattr(event, 'type') else None

            # Handle message start - get initial usage
            if event_type == "message_start":
                if hasattr(event, 'message') and hasattr(event.message, 'usage'):
                    usage = event.message.usage
                    total_usage.input_tokens = getattr(usage, 'input_tokens', 0)

            # Handle content block start
            elif event_type == "content_block_start":
                block = event.content_block
                index = event.index

                if hasattr(block, 'type'):
                    if block.type == "text":
                        current_text_index = index
                        current_content[index] = {"type": "text", "text": ""}
                        stream.push_text_start(index)

                    elif block.type == "thinking":
                        current_thinking_index = index
                        current_content[index] = {"type": "thinking", "text": ""}
                        stream.push_thinking_start(index)

                    elif block.type == "tool_use":
                        current_content[index] = {
                            "type": "tool_use",
                            "id": getattr(block, 'id', ''),
                            "name": getattr(block, 'name', ''),
                            "input": "",
                        }
                        stream.push_toolcall_start(
                            index=index,
                            id=getattr(block, 'id', ''),
                            name=getattr(block, 'name', ''),
                        )

            # Handle content block delta
            elif event_type == "content_block_delta":
                index = event.index
                delta = event.delta

                if hasattr(delta, 'type'):
                    if delta.type == "text_delta":
                        text = getattr(delta, 'text', '')
                        if index in current_content:
                            current_content[index]["text"] += text
                        stream.push_text_delta(text, index)

                    elif delta.type == "thinking_delta":
                        text = getattr(delta, 'thinking', '')
                        if index in current_content:
                            current_content[index]["text"] += text
                        stream.push_thinking_delta(text, index)

                    elif delta.type == "input_json_delta":
                        partial_json = getattr(delta, 'partial_json', '')
                        if index in current_content:
                            current_content[index]["input"] += partial_json
                        stream.push_toolcall_arguments_delta(partial_json, index)

            # Handle content block stop
            elif event_type == "content_block_stop":
                index = event.index

                if index in current_content:
                    block_type = current_content[index].get("type")

                    if block_type == "text":
                        stream.push_text_end(index)
                    elif block_type == "thinking":
                        stream.push_thinking_end(index)
                    elif block_type == "tool_use":
                        stream.push_toolcall_end(index)

            # Handle message delta - get output tokens and stop reason
            elif event_type == "message_delta":
                delta = event.delta

                if hasattr(delta, 'stop_reason'):
                    stop_reason = self._map_stop_reason(delta.stop_reason)
                    stream.push_stop_reason(stop_reason)

                if hasattr(delta, 'usage'):
                    usage = delta.usage
                    total_usage.output_tokens = getattr(usage, 'output_tokens', 0)

            # Handle message stop
            elif event_type == "message_stop":
                # Final usage update
                stream.push_usage(total_usage)

        stream.end()

    def _map_stop_reason(self, reason: str) -> StopReason:
        """Map Anthropic stop reason to StopReason."""
        mapping = {
            "end_turn": StopReason.END_TURN,
            "tool_use": StopReason.TOOL_USE,
            "max_tokens": StopReason.MAX_TOKENS,
            "stop_sequence": StopReason.STOP_SEQUENCE,
        }
        return mapping.get(reason, StopReason.END_TURN)
