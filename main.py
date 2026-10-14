"""Run the chatbot: `python main.py`, then open http://localhost:8000."""

import logging

import uvicorn

from ragchat.config import get_settings
from ragchat.server import create_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=get_settings().port)
