import logging
import uuid
from typing import AsyncGenerator
import asyncio
import json
from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, AIMessage, HumanMessage, BaseMessage
from src.retrieval_graph.graph import app as chat_graph
from src.retrieval_graph.state import AgentState

from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from typing import List, Dict


class Thread(BaseModel):
    id: str 
    messages: List[Dict]

origins = [
    "http://localhost:3000", 
    "http://127.0.0.1:3000",
    "http://localhost",
    "http://localhost:8000",
]



logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="Company Information Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
    

@app.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for streaming chat responses."""
    await websocket.accept()

    try:
        state = {"messages": []}
        config = {"configurable": {"thread_id": 123}}

        while True:
            
            message = await websocket.receive_text()
            print(f"\n\nMessage: {message}\n\n")

            state["messages"].append(HumanMessage(content=message))
            buffer = ""

            async for event in chat_graph.astream({"messages": state["messages"]}, config, stream_mode='messages'):
                if isinstance(event[0], AIMessageChunk):
                    buffer += event[0].content
                
                else:
                    await websocket.send_text(event[0].content)

                logger.info(f"Event: {event}")
            
            if buffer:
                await websocket.send_text(buffer)
                buffer=""


            print(f"\nNext node is: {chat_graph.get_state(config)}\n")
            current_state = chat_graph.get_state(config)

            while len(current_state.next) > 0 and current_state.next[0] in ["ask_user_interest", "ask_email_interest", "collect_email"]:
                logger.info(f"\n\Interrupt state: {current_state.next[0]}\n\n")
                message = await websocket.receive_text()
                chat_graph.update_state(config, {"user_feedback": message}, as_node=current_state.next[0])

                logger.info("--State after update--")
                logger.info(chat_graph.get_state(config))

                logger.info(f"\n\n{chat_graph.get_state(config).next}\n")

                async for event in chat_graph.astream(None, config, stream_mode='messages'):
                    logger.info(f"\n\nEvent after breakpoint: {event}\n\n")
                    if isinstance(event[0], AIMessageChunk):
                        buffer += event[0].content
                    
                    else:
                        await websocket.send_text(event[0].content)
                
                if buffer:
                    await websocket.send_text(buffer)
                    buffer=""

                current_state = chat_graph.get_state(config)
                logger.info(f"Next state is: {current_state.next}")

    except WebSocketDisconnect:
        print("WebSocket disconnected")




@app.get("/stream_chat")
async def stream_chat(content: str, request: Request):
    """HTTP endpoint for streaming chat responses."""
    try:
        client_ip = request.client.host
        thread_id = client_ip
        config = {"configurable": {"thread_id": "1"}}


        async for event in chat_graph.astream({"messages": [("user", content)]}, config):
            for value in event.values():
                print("\n\n\nAssistant:", value)
                # return f"Assistant: {value}\n\n"
                return f"\n\nAssistant: {value['messages'][-1].content}\n\n"


    except Exception as e:
        logger.error(f"Error in stream_chat endpoint: {e}")
        raise