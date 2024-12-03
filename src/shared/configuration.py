"""Define the configurable parameters for the agent."""

from __future__ import annotations
from dataclasses import dataclass, field, fields
from typing import Annotated, Any, Literal, Optional, Type, TypeVar
from langchain_core.runnables import RunnableConfig, ensure_config

@dataclass(kw_only=True)
class BaseConfiguration:
    """Configuration for company information bot."""

    embedding_model: Annotated[str, {"__template_metadata__": {"kind": "embeddings"}}] = field(
        default="openai/text-embedding-3-small",
        metadata={
            "description": "Embedding model for company document vectorization."
        },
    )

    retriever_provider: Annotated[Literal["faiss"], {"__template_metadata__": {"kind": "retriever"}}] = field(
        default="faiss",
        metadata={
            "description": "Vector store provider (currently only FAISS supported)"
        },
    )

    search_kwargs: dict[str, Any] = field(
        default_factory=lambda: {"k": 3},
        metadata={
            "description": "Search parameters for document retrieval"
        },
    )

    @classmethod
    def from_runnable_config(cls: Type[T], config: Optional[RunnableConfig] = None) -> T:
        """Create configuration from RunnableConfig."""
        config = ensure_config(config)
        configurable = config.get("configurable") or {}
        _fields = {f.name for f in fields(cls) if f.init}
        return cls(**{k: v for k, v in configurable.items() if k in _fields})

T = TypeVar("T", bound=BaseConfiguration)