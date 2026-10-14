import json

from ragchat.knowledge_base import load_documents
from tests.conftest import DATA


def test_every_eval_answer_exists_on_its_expected_page():
    pages = {
        d.metadata["page"]: " ".join(d.page_content.split()).lower() for d in load_documents(DATA)
    }
    for case in json.loads((DATA / "eval_questions.json").read_text()):
        assert case["answer_contains"].lower() in pages[case["expected_page"]], case["question"]
