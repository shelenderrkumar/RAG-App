import logging
import uuid
from typing import AsyncGenerator
import asyncio
import json
from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from langchain.schema import HumanMessage, AIMessage
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

@app.post("/api/threads", response_model=Thread)
async def create_thread():
    """Create a new chat thread."""
    try:
        thread = Thread(
            id=str(uuid.uuid4()),
            messages=[]
        )
        logger.debug(f"Created new thread with ID: {thread.id}")
        return thread
    
    except Exception as e:
        logger.error(f"Error creating thread: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create thread: {str(e)}"
        )
    

@app.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for streaming chat responses."""
    print("\n\n\n\nYayyy\n\n")
    await websocket.accept()

    try:
        state = {"messages": []}  # Maintain state of conversation
        config = {"configurable": {"thread_id": 123}}

        while True:
            print("\n\tTrue\n\n")
            message = await websocket.receive_text()
            print(f"\n\nMessage: {message}\n\n")

            state["messages"].append(HumanMessage(content=message))

            async for event in chat_graph.astream({"messages": state["messages"]}, config, stream_mode='messages'):
                print(f"\nEvent: {event}\n")
                await websocket.send_text(event[0].content)

            print(f"\nNext node is: {chat_graph.get_state(config)}\n")
            current_state = chat_graph.get_state(config)

            while len(current_state.next) > 0 and current_state.next[0] in ["ask_user_interest", "ask_email_interest", "collect_email"]:
                print(f"\nYes, interrupt node\n {current_state.next[0]}\n")
                message = await websocket.receive_text()
                chat_graph.update_state(config, {"user_feedback": message}, as_node=current_state.next[0])

                # Log the updated state
                print("--State after update--")
                print(chat_graph.get_state(config))

                print(f"\n\n{chat_graph.get_state(config).next}\n")

                async for event in chat_graph.astream(None, config, stream_mode='messages'):
                    print(f"\n\nEvent after breakpoint: {event}\n\n")
                    await websocket.send_text(event[0].content)

                current_state = chat_graph.get_state(config)
                print(f"Next state is: {current_state.next}")

    except WebSocketDisconnect:
        print("WebSocket disconnected")

# @app.websocket("/chat")
# async def websocket_endpoint(websocket: WebSocket):
#     """WebSocket endpoint for streaming chat responses."""
#     print("\n\n\n\nYayyy\n\n")
#     await websocket.accept()

#     try:
#         state = {"messages": []}  # Maintain state of conversation
#         while True:
#             print("\n\tTrue\n\n")
#             message = await websocket.receive_text()
#             print(f"\n\nMessage: {message}\n\n")

#             state["messages"].append(HumanMessage(content=message))
#             config = {"configurable": {"thread_id": 123}}

        
            
#             async for event in chat_graph.astream({"messages": state["messages"]}, config, stream_mode='messages',):
#                 print(f"\nEvent: {event}\n")
                
#                 await websocket.send_text(event[0].content)
                
#             async def streaming(websocket):
#                 print(f"\nNext node is: {chat_graph.get_state(config)}\n")
#                 current_state = chat_graph.get_state(config)


#                 if len(current_state.next) > 0 and current_state.next[0] in ["ask_user_interest", "email_request", "collect_email"]:
#                     print(f"\nYes, interrupt node\n {current_state.next[0]}\n")
#                     message = await websocket.receive_text()
#                     chat_graph.update_state(config, {"user_feedback": message}, as_node=current_state.next[0])

#                     # We can check the state
#                     print("--State after update--")
#                     print(chat_graph.get_state(config))

#                     print(f"\n\n{chat_graph.get_state(config).next}\n")

#                     async for event in chat_graph.astream(None, config, stream_mode='messages',):
#                         print(f"\n\nEvent after breakpoint: {event}\n\n")
#                         print(f"\n\n{chat_graph.get_state(config).next}\n")

#                         # if isinstance(event, dict) and 'messages' in event:
#                         #     messages = event['messages']
#                         #     if messages and isinstance(messages[-1], AIMessage):
#                         #         await websocket.send_text(json.dumps(messages[-1].content))


#                         await websocket.send_text(event[0].content)
            
           
#             # state["messages"].append(HumanMessage(content=message))

#             # Streaming response from chat_graph based on the current state
#             # config = {"configurable": {"thread_id": "1"}}
#             # async for event in chat_graph.astream({"messages": state["messages"]}, config, stream_mode='updates'):
#             #     print(f"\n\nEvent: {event}\n\n")
#             #     # await websocket.send_text(json.dumps(event))
#                 # for value in event.items():
#                 #     print(f"\n\nValue: {value}\n\n")
#                 #     if isinstance(value, dict) and 'messages' in value:
#                 #         assistant_message = value['messages'][-1].content
#                 #         await websocket.send_text(assistant_message)
#                 #     else:
#                 #         await websocket.send_text(str(value))
                        

#     except WebSocketDisconnect:
#         logger.info("Client disconnected")
#     except Exception as e:
#         logger.error(f"WebSocket error: {e}")
#         await websocket.close()



@app.get("/stream_chat")
async def stream_chat(content: str, request: Request):
    """HTTP endpoint for streaming chat responses."""
    try:
        client_ip = request.client.host
        thread_id = client_ip
        print("\n\nYes I am here\n\n")
        config = {"configurable": {"thread_id": "1"}}


        async for event in chat_graph.astream({"messages": [("user", content)]}, config):
            for value in event.values():
                print("\n\n\nAssistant:", value)
                # return f"Assistant: {value}\n\n"
                return f"\n\nAssistant: {value['messages'][-1].content}\n\n"


    except Exception as e:
        logger.error(f"Error in stream_chat endpoint: {e}")
        raise




        # while True:
        #     try:
        #         user_input = input("User: ")
        #         if user_input.lower() in ["quit", "exit", "q"]:
        #             print("Goodbye!")
        #             break

        #         stream_graph_updates(user_input)
        #     except:
        #         # fallback if input() is not available
        #         user_input = "What do you know about LangGraph?"
        #         print("User: " + user_input)
        #         stream_graph_updates(user_input)
        #         break

        # inputs = {
        #     "messages": [
        #         ("user", "How are you doing today?"),
        #     ]
        # }
        # for output in chat_graph.stream(inputs):
        #     print(f"Output: {output}")
                
        # async def event_generator():
        #     messages = [HumanMessage(content=content)]
            
        #     async for event in chat_graph.astream_events(
        #         {"messages": messages},
        #         config = {"configurable": {"thread_id": thread_id}},
        #         version="v1"
        #     ):
        #         print(f"\nEvent: {event['event']}\n")
        #         if event["event"] == "on_chain_stream":
        #             if event["data"].get("chunk"):
        #                 # chunk = event["data"].get("chunk")
        #                 # chunk_content = chunk["messages"][0].content
        #                 yield f"data: {event['data']}\n\n"

        #         elif event["event"] == "on_metadata":
        #             metadata = event["data"]
        #             if metadata:
        #                 yield f"data: {metadata}\n\n"

        # return StreamingResponse(
        #     event_generator(),
        #     media_type="text/event-stream"
        # )
