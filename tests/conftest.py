from pathlib import Path

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from ragchat.email_sender import ConsoleEmailSender
from ragchat.graph import build_graph
from ragchat.knowledge_base import KnowledgeBase

DATA = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="session")
def knowledge_base(tmp_path_factory):
    return KnowledgeBase.build(
        DATA, DeterministicFakeEmbedding(size=64), tmp_path_factory.mktemp("index"), top_k=2
    )


def fake_llm(*replies: str) -> GenericFakeChatModel:
    """Chat model that returns the given replies in order (and streams them word by word)."""
    return GenericFakeChatModel(messages=iter(AIMessage(r) for r in replies))


@pytest.fixture
def make_graph(knowledge_base):
    def _make(*replies: str):
        outbox = ConsoleEmailSender()
        graph = build_graph(
            fake_llm(*replies),
            knowledge_base,
            outbox,
            company="Lumora Analytics",
            profile_pdf=DATA / "company_profile.pdf",
        )
        return graph, outbox

    return _make
