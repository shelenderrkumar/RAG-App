from langchain_core.messages import AIMessage

from ragchat.session import ChatSession

OVERVIEW = "Hi! Lumora forecasts retail demand. Want to learn more?"
DETAILS = "Lumora sells Forecast, Replenish and Insights [p. 2]. Want the profile by e-mail?"


class Transcript:
    def __init__(self):
        self.events = []

    async def __call__(self, event):
        self.events.append(event)

    def messages(self):
        return [e["text"] for e in self.events if e["type"] == "message"]

    def last_turn(self):
        return [e for e in self.events if e["type"] == "turn_end"][-1]["awaiting"]

    def clear(self):
        self.events.clear()


async def test_full_happy_path_sends_profile(make_graph):
    graph, outbox = make_graph(OVERVIEW, DETAILS)
    session, out = ChatSession(graph), Transcript()

    await session.start(out)
    assert out.messages() == [OVERVIEW]
    assert out.last_turn() == "await_interest"
    tokens = [e for e in out.events if e["type"] == "token"]
    final = next(e for e in out.events if e["type"] == "message")
    assert tokens and {t["id"] for t in tokens} == {final["id"]}  # UI finalises the same bubble

    out.clear()
    await session.reply("yes please", out)
    assert out.messages() == [DETAILS] and out.last_turn() == "await_email_offer"

    await session.reply("sure", out)
    assert out.last_turn() == "collect_email"

    out.clear()
    await session.reply("it's jane@", out)  # invalid -> asked again
    assert out.last_turn() == "collect_email" and "doesn't look like" in out.messages()[0]

    out.clear()
    await session.reply("jane@example.com", out)
    assert out.messages() == ["Just to confirm: should I send the profile to jane@example.com?"]

    out.clear()
    await session.reply("yes", out)
    assert "has been sent to jane@example.com" in out.messages()[0]
    assert out.last_turn() == "qa"

    [mail] = outbox.outbox
    assert mail["to"] == "jane@example.com"
    assert DETAILS in mail["body"] and mail["attachment"].name == "company_profile.pdf"


async def test_declining_details_goes_to_questions(make_graph):
    graph, outbox = make_graph(OVERVIEW, "Search query", "Starter costs $199/store/month [p. 3].")
    session, out = ChatSession(graph), Transcript()
    await session.start(out)
    await session.reply("no thanks", out)
    assert out.last_turn() == "qa"

    out.clear()
    await session.reply("How much does it cost?", out)
    assert out.messages() == ["Starter costs $199/store/month [p. 3]."]
    assert out.last_turn() == "qa" and outbox.outbox == []


async def test_condense_step_is_not_streamed_to_the_user(make_graph):
    graph, _ = make_graph(OVERVIEW, "INTERNAL standalone query", "An answer.")
    session, out = ChatSession(graph), Transcript()
    await session.start(out)
    await session.reply("no", out)
    out.clear()
    await session.reply("and who founded it?", out)
    streamed = "".join(e["text"] for e in out.events if e["type"] == "token")
    assert "INTERNAL" not in streamed and "An answer." in streamed


async def test_wrong_email_can_be_corrected(make_graph):
    graph, outbox = make_graph(OVERVIEW, DETAILS)
    session, out = ChatSession(graph), Transcript()
    await session.start(out)
    await session.reply("yes", out)
    await session.reply("yes, send it to jon@example.com", out)  # address given inline
    assert out.last_turn() == "confirm_email"
    await session.reply("no", out)
    assert out.last_turn() == "collect_email"
    await session.reply("john@example.com", out)
    await session.reply("correct", out)
    assert [m["to"] for m in outbox.outbox] == ["john@example.com"]


async def test_email_can_be_requested_later_from_qa(make_graph):
    graph, outbox = make_graph(OVERVIEW)
    session, out = ChatSession(graph), Transcript()
    await session.start(out)
    await session.reply("no", out)
    await session.reply("Actually, can you email the profile to me@example.com?", out)
    assert out.last_turn() == "confirm_email"
    await session.reply("yes", out)
    assert outbox.outbox[0]["to"] == "me@example.com"


async def test_conversations_are_isolated(make_graph):
    graph, _ = make_graph(OVERVIEW, OVERVIEW)
    first, second = ChatSession(graph), ChatSession(graph)
    await first.start(Transcript())
    await second.start(Transcript())
    await first.reply("no", Transcript())
    state = await graph.aget_state(second.config)
    assert state.interrupts[0].value == "await_interest"  # untouched by the first user
    assert all(isinstance(m, AIMessage) for m in state.values["messages"])


async def test_email_failure_is_reported_gracefully(make_graph):
    graph, outbox = make_graph(OVERVIEW, DETAILS)

    async def broken_send(**kwargs):
        raise ConnectionError("SMTP down")

    outbox.send = broken_send
    session, out = ChatSession(graph), Transcript()
    await session.start(out)
    for text in ("yes", "yes", "a@b.co"):
        await session.reply(text, out)
    out.clear()
    await session.reply("yes", out)
    assert "couldn't send" in out.messages()[0]
