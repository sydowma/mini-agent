"""OpenAI provider implementation."""

import asyncio
import json
from typing import Optional

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionChunk

from ..types import (
    Context, Tool, StopReason, Usage,
    UserMessage, AssistantMessage, TextContent, ToolCall
)
from ..event_stream import AssistantMessageEventStream, EventType
from .base import Provider, StreamOptions


class OpenAIProvider(Provider):
    """OpenAI API provider."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self._api_key = api_key
        self._base_url = base_url
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        """Lazy-initialize the OpenAI client."""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    @property
    def api(self) -> str:
        return "openai"

    @property
    def default_model(self) -> str:
        return "gpt-4o"

    async def stream(
        self,
        model: str,
        context: Context,
        options: Optional[StreamOptions] = None,
    ) -> AssistantMessageEventStream:
        """Stream a response from OpenAI."""
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
            messages = self._build_messages(context)
            tools = self._build_tools(context.tools) if context.tools else None

            response = await self._get_client().chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto" if tools else None,
                temperature=options.temperature,
                max_tokens=options.max_tokens,
                top_p=options.top_p,
                stop=options.stop_sequences or None,
                stream=True,
            )

            await self._process_stream(response, stream)

        except Exception as e:
            stream.error(e)

    def _build_messages(self, context: Context) -> list[dict]:
        """Build OpenAI message format from context."""
        messages = []

        # Add system prompt if present
        if context.system_prompt:
            messages.append({"role": "system", "content": context.system_prompt})

        for msg in context.messages:
            if isinstance(msg, UserMessage):
                if len(msg.content) == 1 and isinstance(msg.content[0], TextContent):
                    messages.append({
                        "role": "user",
                        "content": msg.content[0].text,
                    })
                else:
                    # Handle multi-content
                    content = []
                    for block in msg.content:
                        if isinstance(block, TextContent):
                            content.append({"type": "text", "text": block.text})
                        elif hasattr(block, 'source'):  # ImageContent
                            content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{block.media_type};base64,{block.data}"
                                }
                            })
                    messages.append({"role": "user", "content": content})

            elif isinstance(msg, AssistantMessage):
                # Build assistant message with content and tool calls
                content_parts = []
                tool_calls = []

                for block in msg.content:
                    if isinstance(block, TextContent):
                        content_parts.append(block.text)
                    elif isinstance(block, ToolCall):
                        tool_calls.append({
                            "id": block.id,
                            "type": "function",
                            "function": {
                                "name": block.name,
                                "arguments": json.dumps(block.arguments),
                            }
                        })

                msg_dict = {"role": "assistant"}
                if content_parts:
                    msg_dict["content"] = "".join(content_parts)
                if tool_calls:
                    msg_dict["tool_calls"] = tool_calls
                messages.append(msg_dict)

            elif hasattr(msg, 'tool_call_id'):  # ToolResultMessage
                messages.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content,
                })

        return messages

    def _build_tools(self, tools: list[Tool]) -> list[dict]:
        """Build OpenAI tools format."""
        return [tool.to_dict() for tool in tools]

    async def _process_stream(
        self,
        response,
        stream: AssistantMessageEventStream,
    ) -> None:
        """Process the streaming response."""
        current_tool_calls: dict[int, dict] = {}
        current_text_index = None

        async for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            finish_reason = chunk.choices[0].finish_reason if chunk.choices else None

            if delta is None:
                continue

            # Handle text content
            if delta.content:
                if current_text_index is None:
                    current_text_index = 0
                    stream.push_text_start(current_text_index)
                stream.push_text_delta(delta.content, current_text_index)

            # Handle tool calls
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index

                    if idx not in current_tool_calls:
                        current_tool_calls[idx] = {
                            "id": "",
                            "name": "",
                            "arguments": "",
                        }
                        stream.push_toolcall_start(
                            index=idx,
                            id=tc_delta.id or "",
                            name="",
                        )

                    if tc_delta.id:
                        current_tool_calls[idx]["id"] = tc_delta.id

                    if tc_delta.function:
                        if tc_delta.function.name:
                            current_tool_calls[idx]["name"] += tc_delta.function.name
                            stream.push_toolcall_name_delta(tc_delta.function.name, idx)

                        if tc_delta.function.arguments:
                            current_tool_calls[idx]["arguments"] += tc_delta.function.arguments
                            stream.push_toolcall_arguments_delta(tc_delta.function.arguments, idx)

            # Handle usage
            if hasattr(chunk, 'usage') and chunk.usage:
                stream.push_usage(Usage(
                    input_tokens=chunk.usage.prompt_tokens or 0,
                    output_tokens=chunk.usage.completion_tokens or 0,
                ))

            # Handle finish reason
            if finish_reason:
                # Close any open text
                if current_text_index is not None:
                    stream.push_text_end(current_text_index)

                # Close any open tool calls
                for idx in sorted(current_tool_calls.keys()):
                    stream.push_toolcall_end(idx)

                # Map finish reason
                stop_reason = self._map_stop_reason(finish_reason)
                stream.push_stop_reason(stop_reason)

        stream.end()

    def _map_stop_reason(self, reason: str) -> StopReason:
        """Map OpenAI finish reason to StopReason."""
        mapping = {
            "stop": StopReason.END_TURN,
            "tool_calls": StopReason.TOOL_USE,
            "length": StopReason.MAX_TOKENS,
            "content_filter": StopReason.ERROR,
        }
        return mapping.get(reason, StopReason.END_TURN)
