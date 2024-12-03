"""Manage document retrieval for company information bot."""

from contextlib import contextmanager
from typing import Generator
import os

from langchain_core.embeddings import Embeddings
from langchain_core.runnables import RunnableConfig
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from ..shared.configuration import BaseConfiguration

def make_text_encoder(model: str) -> Embeddings:
    """Create OpenAI embeddings model."""
    provider, model = model.split("/", maxsplit=1)
    if provider != "openai":
        raise ValueError("Only OpenAI embeddings are supported")
    return OpenAIEmbeddings(model=model)

@contextmanager 
def make_faiss_retriever(
    configuration: BaseConfiguration, embedding_model: Embeddings
) -> Generator[VectorStoreRetriever, None, None]:
    """Configure FAISS vector store retriever."""

    index_path = os.path.join(os.path.dirname(__file__), "index")

    vstore = FAISS.load_local(index_path, embedding_model,  allow_dangerous_deserialization=True)
    yield vstore.as_retriever(search_kwargs=configuration.search_kwargs)

@contextmanager 
def make_retriever(config: RunnableConfig) -> Generator[VectorStoreRetriever, None, None]:
    """Create document retriever based on configuration."""
    configuration = BaseConfiguration.from_runnable_config(config)
    embedding_model = make_text_encoder(configuration.embedding_model)
    with make_faiss_retriever(configuration, embedding_model) as retriever:
        yield retriever