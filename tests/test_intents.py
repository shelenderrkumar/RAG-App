import pytest

from ragchat.intents import YesNo, classify_yes_no, extract_email, quick_yes_no


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("sure, it's Jane.Doe@Example.com.", "jane.doe@example.com"),
        ("my email is a_b+tag@mail.co.uk", "a_b+tag@mail.co.uk"),
        ("I don't have one", None),
        ("jane at example dot com", None),
    ],
)
def test_extract_email(text, expected):
    assert extract_email(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [("Yes!", True), ("sure thing", True), ("Nope.", False), ("no thanks", False),
     ("tell me about pricing first", None)],
)  # fmt: skip
def test_quick_yes_no(text, expected):
    assert quick_yes_no(text) is expected


class StructuredStub:
    """Minimal stand-in for an LLM's structured-output path."""

    def __init__(self, answer):
        self.answer, self.calls = answer, 0

    def with_structured_output(self, schema):
        assert schema is YesNo
        return self

    def with_config(self, **kwargs):
        return self

    async def ainvoke(self, messages):
        self.calls += 1
        return YesNo(answer=self.answer)


async def test_llm_fallback_only_for_ambiguous_replies():
    llm = StructuredStub("yes")
    assert await classify_yes_no(llm, "Want more?", "yes") is True
    assert llm.calls == 0  # fast path, no model call
    assert await classify_yes_no(llm, "Want more?", "I'd love to hear about pricing") is True
    assert llm.calls == 1
