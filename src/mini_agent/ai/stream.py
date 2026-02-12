"""High-level streaming API."""

from typing import AsyncIterator

from .types import Context, AssistantMessage
from .event_stream import EventStream, AssistantMessageEventStream


async def stream_response(
    stream: AssistantMessageEventStream,
) -> AsyncIterator[AssistantMessageEventStream]:
    """
    Helper to iterate over a stream and get the final message.

    Usage:
        async for event in stream_response(stream):
            if event.type == EventType.TEXT_DELTA:
                print(event.data.delta, end="")

        message = await stream.result()
    """
    async for event in stream:
        yield event
