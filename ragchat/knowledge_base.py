"""Document ingestion and retrieval (PDF / Markdown -> chunks -> FAISS)."""

import logging
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)


def load_documents(source_dir: Path) -> list[Document]:
    """Load every PDF (one Document per page) and Markdown/text file in ``source_dir``."""
    from pypdf import PdfReader

    docs: list[Document] = []
    for path in sorted(source_dir.iterdir()):
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            for number, page in enumerate(PdfReader(path).pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    docs.append(
                        Document(page_content=text, metadata={"source": path.name, "page": number})
                    )
        elif suffix in {".md", ".txt"}:
            docs.append(
                Document(
                    page_content=path.read_text(encoding="utf-8"), metadata={"source": path.name}
                )
            )
    return docs


def split_documents(docs: list[Document], chunk_size: int, chunk_overlap: int) -> list[Document]:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, add_start_index=True
    )
    return splitter.split_documents(docs)


class KnowledgeBase:
    def __init__(self, vectorstore, top_k: int = 4):
        self.vectorstore = vectorstore
        self.top_k = top_k

    @classmethod
    def build(
        cls,
        source_dir: Path,
        embeddings: Embeddings,
        index_dir: Path | None = None,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
        top_k: int = 4,
    ) -> "KnowledgeBase":
        """Load a cached index from ``index_dir`` or build one from ``source_dir``."""
        from langchain_community.vectorstores import FAISS

        if index_dir is not None and (index_dir / "index.faiss").exists():
            # Safe: the index is written locally by this method, never downloaded.
            store = FAISS.load_local(
                str(index_dir), embeddings, allow_dangerous_deserialization=True
            )
            return cls(store, top_k)

        chunks = split_documents(load_documents(source_dir), chunk_size, chunk_overlap)
        if not chunks:
            raise FileNotFoundError(f"No PDF/Markdown documents found in {source_dir}")
        store = FAISS.from_documents(chunks, embeddings)
        if index_dir is not None:
            store.save_local(str(index_dir))
        logger.info("Indexed %d chunks from %s", len(chunks), source_dir)
        return cls(store, top_k)

    async def search(self, query: str) -> list[Document]:
        return await self.vectorstore.asimilarity_search(query, k=self.top_k)


def format_context(docs: list[Document]) -> str:
    """Render retrieved chunks with page labels the model can cite."""
    parts = []
    for doc in docs:
        page = doc.metadata.get("page")
        label = f"{doc.metadata.get('source', 'doc')}" + (f", p. {page}" if page else "")
        parts.append(f"[{label}]\n{doc.page_content.strip()}")
    return "\n\n".join(parts)
