from fastapi.testclient import TestClient

from ragchat.config import Settings
from ragchat.server import create_app
from tests.test_graph import OVERVIEW


def test_websocket_conversation(make_graph):
    graph, _ = make_graph(OVERVIEW, "Search query", "Answer [p. 1].")
    client = TestClient(create_app(Settings(_env_file=None), graph=graph))
    assert client.get("/health").json()["status"] == "ok"
    assert "/ws/chat" in client.get("/").text

    def until_turn_end(ws):
        events = []
        while not events or events[-1]["type"] != "turn_end":
            events.append(ws.receive_json())
        return events

    with client.websocket_connect("/ws/chat") as ws:
        greeting = until_turn_end(ws)
        assert any(e["type"] == "message" and e["text"] == OVERVIEW for e in greeting)

        ws.send_json({"type": "user", "text": "   "})
        assert ws.receive_json()["type"] == "error"

        ws.send_json({"type": "user", "text": "no"})
        until_turn_end(ws)
        ws.send_json({"type": "user", "text": "What do you do?"})
        answer = until_turn_end(ws)
        assert any(e.get("text") == "Answer [p. 1]." for e in answer if e["type"] == "message")
