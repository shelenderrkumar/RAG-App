"""FastAPI app: chat UI at ``/``, WebSocket protocol at ``/ws/chat``.

Client -> server: ``{"type": "user", "text": "..."}``
Server -> client: ``token`` (streamed text), ``message`` (final assistant message),
``turn_end`` (the bot is waiting for the user), ``error``.
"""

import asyncio
import contextlib
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from ragchat import __version__
from ragchat.config import PROJECT_ROOT, Settings, get_settings
from ragchat.session import ChatSession

logger = logging.getLogger(__name__)
MAX_MESSAGE_CHARS = 2000


def build_default_graph(settings: Settings):
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings

    from ragchat.email_sender import build_email_sender
    from ragchat.graph import build_graph
    from ragchat.knowledge_base import KnowledgeBase

    api_key = settings.openai_api_key
    knowledge_base = KnowledgeBase.build(
        settings.documents_dir,
        OpenAIEmbeddings(model=settings.embedding_model, api_key=api_key),
        settings.index_dir,
        settings.chunk_size,
        settings.chunk_overlap,
        settings.top_k,
    )
    return build_graph(
        llm=ChatOpenAI(model=settings.chat_model, temperature=0, api_key=api_key),
        knowledge_base=knowledge_base,
        email_sender=build_email_sender(settings),
        company=settings.company_name,
        profile_pdf=settings.company_profile_pdf,
    )


def create_app(settings: Settings | None = None, graph=None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="Company RAG Chatbot", version=__version__)
    state = {"graph": graph}
    lock = asyncio.Lock()

    async def get_graph():
        async with lock:  # build the index once, on first use
            if state["graph"] is None:
                state["graph"] = await asyncio.to_thread(build_default_graph, settings)
        return state["graph"]

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(PROJECT_ROOT / "static" / "index.html")

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": __version__}

    @app.websocket("/ws/chat")
    async def chat(websocket: WebSocket):
        await websocket.accept()
        session = ChatSession(await get_graph())
        try:
            await session.start(websocket.send_json)
            while True:
                data = await websocket.receive_json()
                text = str(data.get("text", "")).strip()
                if data.get("type") != "user" or not text:
                    await websocket.send_json({"type": "error", "text": "Empty message."})
                    continue
                if len(text) > MAX_MESSAGE_CHARS:
                    await websocket.send_json({"type": "error", "text": "Message is too long."})
                    continue
                await session.reply(text, websocket.send_json)
        except WebSocketDisconnect:
            logger.info("Client disconnected")
        except Exception:
            logger.exception("Chat session failed")
            with contextlib.suppress(Exception):
                await websocket.send_json(
                    {"type": "error", "text": "Something went wrong. Please refresh and try again."}
                )

    return app
