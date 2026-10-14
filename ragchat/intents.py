"""Cheap, deterministic parsing of user replies, with an LLM fallback for the rest."""

import re
from typing import Literal

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

_YES = set(
    [
        "yes",
        "y",
        "yeah",
        "yep",
        "yup",
        "sure",
        "ok",
        "okay",
        "please",
        "of course",
        "definitely",
        "absolutely",
        "go ahead",
        "sounds good",
        "why not",
        "correct",
        "right",
        "thats right",
    ]
)
_NO = set(
    [
        "no",
        "n",
        "nope",
        "nah",
        "not now",
        "no thanks",
        "no thank you",
        "not really",
        "maybe later",
        "wrong",
    ]
)


def extract_email(text: str) -> str | None:
    match = EMAIL_RE.search(text)
    return match.group(0).rstrip(".").lower() if match else None


def quick_yes_no(text: str) -> bool | None:
    """Return True/False for unambiguous short replies, None when an LLM should decide."""
    normalized = re.sub(r"[^a-z ]", "", text.lower()).strip()
    if normalized in _YES or normalized.startswith(("yes ", "sure ")):
        return True
    if normalized in _NO or normalized.startswith(("no ", "nope ")):
        return False
    return None


class YesNo(BaseModel):
    """Whether the user's reply accepts the assistant's offer."""

    answer: Literal["yes", "no"] = Field(description="'yes' if the user accepts, else 'no'")


async def classify_yes_no(llm: BaseChatModel, offer: str, reply: str) -> bool:
    if (quick := quick_yes_no(reply)) is not None:
        return quick
    classifier = llm.with_structured_output(YesNo).with_config(tags=["internal"])
    result = await classifier.ainvoke(
        [
            ("system", "Decide whether the user's reply accepts the assistant's offer."),
            ("user", f"Offer: {offer}\nReply: {reply}"),
        ]
    )
    return result.answer == "yes"
