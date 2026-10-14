from ragchat.knowledge_base import format_context, load_documents, split_documents
from tests.conftest import DATA


def test_pdf_is_loaded_page_by_page():
    docs = load_documents(DATA)
    assert [d.metadata["page"] for d in docs] == [1, 2, 3]
    assert "Lumora Analytics" in docs[0].page_content


def test_chunks_keep_page_metadata():
    chunks = split_documents(load_documents(DATA), chunk_size=300, chunk_overlap=50)
    assert len(chunks) > 3
    assert all("page" in c.metadata and "start_index" in c.metadata for c in chunks)
    assert all(len(c.page_content) <= 300 for c in chunks)


async def test_search_and_citation_labels(knowledge_base):
    docs = await knowledge_base.search("pricing")
    assert len(docs) == 2
    assert "[company_profile.pdf, p. " in format_context(docs)
