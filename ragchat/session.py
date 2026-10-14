"""Drives one conversation: runs the graph, streams tokens, returns new assistant messages."""

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk
from langgraph.types import Command

Emit = Callable[[dict[str, Any]], Awaitable[None]]


class ChatSession:
    def __init__(self, graph, thread_id: str | None = None):
        self.graph = graph
        # One checkpointed thread per connection: users never see each other's conversation.
        self.config = {"configurable": {"thread_id": thread_id or uuid.uuid4().hex}}

    async def start(self, emit: Emit) -> None:
        await self._run({"messages": []}, emit)

    async def reply(self, text: str, emit: Emit) -> None:
        await self._run(Command(resume=text), emit)

    async def _run(self, graph_input, emit: Emit) -> None:
        before = len((await self.graph.aget_state(self.config)).values.get("messages", []))

        async for chunk, metadata in self.graph.astream(
            graph_input, self.config, stream_mode="messages"
        ):
            if (
                isinstance(chunk, AIMessageChunk)
                and chunk.content
                and "internal" not in metadata.get("tags", [])
            ):
                await emit({"type": "token", "id": chunk.id, "text": chunk.content})

        snapshot = await self.graph.aget_state(self.config)
        for message in snapshot.values["messages"][before:]:
            if isinstance(message, AIMessage):
                await emit({"type": "message", "id": message.id, "text": message.content})
        waiting_for = snapshot.interrupts[0].value if snapshot.interrupts else None
        await emit({"type": "turn_end", "awaiting": waiting_for})
