"""Utility functions for company information bot."""

from typing import Optional
from langchain.chat_models import init_chat_model
from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel


def format_docs(docs: Optional[list[Document]]) -> str:
    """Format documents into XML for LLM context."""
    if not docs:
        return "<documents></documents>"
    formatted = "\n".join(_format_doc(doc) for doc in docs)
    return f"<documents>\n{formatted}\n</documents>"


def _format_doc(doc: Document) -> str:
    """Format single document as XML."""
    metadata = doc.metadata or {}
    meta = "".join(f" {k}={v!r}" for k, v in metadata.items())
    return f"<document{meta}>\n{doc.page_content}\n</document>"


def load_chat_model(fully_specified_name: str) -> BaseChatModel:
    """Initialize chat model from provider/name string."""
    provider, model = fully_specified_name.split("/", maxsplit=1) if "/" in fully_specified_name else ("", fully_specified_name)
    return init_chat_model(model, model_provider=provider)

def send_email(email: str, content: str) -> None:
    """Send email with content."""
    # Send email with content
    pass