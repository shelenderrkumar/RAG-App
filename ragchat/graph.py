"""Conversation state machine.

    overview ──► await_interest ──yes──► details ──► await_email_offer ──yes──► collect_email
                      │no                                  │no                    ▲      │
                      ▼                                    ▼                      │no    ▼
                     qa ◄──────────── send_profile ◄──yes── confirm_email ────────┘
                     ▲│ (free-form questions answered with RAG, loops forever)
                     └┘

Every node that needs the user's input calls ``interrupt()`` *first*, so the graph pauses,
the server sends the assistant's question, and the run resumes with
``Command(resume=<user text>)``. State is checkpointed per conversation ``thread_id``.
"""

import logging
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.types import Command, interrupt

from ragchat import prompts
from ragchat.email_sender import EmailSender
from ragchat.intents import classify_yes_no, extract_email
from ragchat.knowledge_base import KnowledgeBase, format_context

logger = logging.getLogger(__name__)

HISTORY_WINDOW = 8  # messages of history sent to the model for follow-up questions


class ChatState(MessagesState):
    email: str | None
    email_sent: bool
    profile_summary: str


def _last_ai_text(state: ChatState) -> str:
    return next((m.content for m in reversed(state["messages"]) if isinstance(m, AIMessage)), "")


def build_graph(
    llm: BaseChatModel,
    knowledge_base: KnowledgeBase,
    email_sender: EmailSender,
    company: str,
    profile_pdf=None,
    checkpointer=None,
):
    async def generate(system_prompt: str, query: str, history=()) -> AIMessage:
        docs = await knowledge_base.search(query)
        system = SystemMessage(system_prompt.format(company=company, context=format_context(docs)))
        response = await llm.ainvoke([system, *history])
        return AIMessage(content=response.content, id=response.id)

    # --- assistant turns -------------------------------------------------------------
    async def overview(state: ChatState):
        message = await generate(prompts.OVERVIEW, f"{company} overview mission what we do")
        return {"messages": [message], "email": None, "email_sent": False}

    async def details(state: ChatState):
        message = await generate(
            prompts.DETAILS, f"{company} products services history leadership customers"
        )
        return {"messages": [message], "profile_summary": message.content}

    async def send_profile(state: ChatState):
        body = (
            f"Hello,\n\nThank you for your interest in {company}. Our company profile is "
            f"attached; here is a short summary:\n\n{state.get('profile_summary', '')}\n\n"
            f"Best regards,\n{company}"
        )
        try:
            await email_sender.send(
                to=state["email"],
                subject=f"{company} - Company Profile",
                body=body,
                attachment=profile_pdf,
            )
        except Exception:
            logger.exception("Failed to send profile to %s", state["email"])
            text = "Sorry, I couldn't send the e-mail right now. Please try again later."
            return {"messages": [AIMessage(text)]}
        return {
            "messages": [
                AIMessage(
                    f"Done! The company profile has been sent to {state['email']}. "
                    "Is there anything else you'd like to know?"
                )
            ],
            "email_sent": True,
        }

    # --- user turns (each pauses the graph until the user replies) ----------------------
    async def await_interest(state: ChatState) -> Command[Literal["details", "qa"]]:
        reply = interrupt("await_interest")
        wants_more = await classify_yes_no(llm, _last_ai_text(state), reply)
        if wants_more:
            return Command(goto="details", update={"messages": [HumanMessage(reply)]})
        return Command(
            goto="qa",
            update={
                "messages": [
                    HumanMessage(reply),
                    AIMessage("No problem! Feel free to ask me anything about the company."),
                ]
            },
        )

    async def await_email_offer(state: ChatState) -> Command[Literal["collect_email", "qa"]]:
        reply = interrupt("await_email_offer")
        if email := extract_email(reply):  # "sure, it's jane@x.com" skips a step
            return Command(goto="confirm_email", update=_confirm(reply, email))
        if await classify_yes_no(llm, _last_ai_text(state), reply):
            ask = AIMessage("Great! What e-mail address should I send it to?")
            return Command(goto="collect_email", update={"messages": [HumanMessage(reply), ask]})
        ok = AIMessage("No problem! Is there anything else you'd like to know about us?")
        return Command(goto="qa", update={"messages": [HumanMessage(reply), ok]})

    async def collect_email(state: ChatState) -> Command[Literal["confirm_email", "collect_email"]]:
        reply = interrupt("collect_email")
        if email := extract_email(reply):
            return Command(goto="confirm_email", update=_confirm(reply, email))
        retry = AIMessage(
            "Hmm, that doesn't look like an e-mail address. Could you type it again "
            "(for example, name@example.com)?"
        )
        return Command(goto="collect_email", update={"messages": [HumanMessage(reply), retry]})

    async def confirm_email(state: ChatState) -> Command[Literal["send_profile", "collect_email"]]:
        reply = interrupt("confirm_email")
        if (email := extract_email(reply)) and email != state["email"]:
            return Command(goto="confirm_email", update=_confirm(reply, email))
        if await classify_yes_no(llm, _last_ai_text(state), reply):
            return Command(goto="send_profile", update={"messages": [HumanMessage(reply)]})
        ask = AIMessage("Sorry about that! What's the correct e-mail address?")
        return Command(goto="collect_email", update={"messages": [HumanMessage(reply), ask]})

    async def qa(state: ChatState) -> Command[Literal["qa", "collect_email"]]:
        question = interrupt("qa")
        human = HumanMessage(question)
        if "email" in question.lower().replace("-", "") and not state.get("email_sent"):
            if email := extract_email(question):
                return Command(goto="confirm_email", update=_confirm(question, email))
            ask = AIMessage("Happy to send you our company profile. What's your e-mail address?")
            return Command(goto="collect_email", update={"messages": [human, ask]})

        history = [*state["messages"][-HISTORY_WINDOW:], human]
        query = question
        if len(history) > 2:  # resolve follow-ups like "how much does it cost?"
            condensed = await llm.with_config(tags=["internal"]).ainvoke(
                [SystemMessage(prompts.CONDENSE), *history]
            )
            query = condensed.content
        answer = await generate(prompts.ANSWER, query, history)
        return Command(goto="qa", update={"messages": [human, answer]})

    builder = StateGraph(ChatState)
    for node in (overview, await_interest, details, await_email_offer, collect_email,
                 confirm_email, send_profile, qa):  # fmt: skip
        builder.add_node(node)
    builder.add_edge(START, "overview")
    builder.add_edge("overview", "await_interest")
    builder.add_edge("details", "await_email_offer")
    builder.add_edge("send_profile", "qa")
    return builder.compile(checkpointer=checkpointer or InMemorySaver())


def _confirm(reply: str, email: str) -> dict:
    return {
        "email": email,
        "messages": [
            HumanMessage(reply),
            AIMessage(f"Just to confirm: should I send the profile to {email}?"),
        ],
    }
