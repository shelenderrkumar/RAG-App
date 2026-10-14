"""Build the FAISS index ahead of time (otherwise it is built on the first chat).

python scripts/build_index.py
"""

from langchain_openai import OpenAIEmbeddings

from ragchat.config import get_settings
from ragchat.knowledge_base import KnowledgeBase

if __name__ == "__main__":
    s = get_settings()
    embeddings = OpenAIEmbeddings(model=s.embedding_model, api_key=s.openai_api_key)
    KnowledgeBase.build(s.documents_dir, embeddings, s.index_dir, s.chunk_size, s.chunk_overlap)
    print(f"Index written to {s.index_dir}")
