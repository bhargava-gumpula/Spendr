import os

from anthropic import AsyncAnthropic

from app.models.schemas import ChatMessage, GrantDetail, GrantRef

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")

ROUTE_TOOL = {
    "name": "route_conversation",
    "description": "Decide what to do next in this grants-advisor conversation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": ["ask_question", "search", "explain_grant", "chat"],
            },
            "message": {
                "type": "string",
                "description": "What to say to the user this turn. For ask_question/chat this IS the full reply. For search/explain_grant this is a short transition line (e.g. 'Let me look for grants that fit that...').",
            },
            "profile": {
                "type": "object",
                "description": "Only when intent=search. Your best synthesis of the project from the whole conversation so far.",
                "properties": {
                    "description": {"type": "string"},
                    "field": {"type": "string", "description": "Short domain/keyword to search with, e.g. 'food security', 'clean energy'."},
                    "stage": {"type": "string"},
                    "team_size": {"type": "integer"},
                    "location": {"type": "string"},
                    "funding_needed": {"type": "string"},
                },
            },
            "selected_grant": {
                "type": "object",
                "description": "Only when intent=explain_grant. Must match one entry from the known grants list provided.",
                "properties": {
                    "source": {"type": "string"},
                    "external_id": {"type": "string"},
                },
            },
        },
        "required": ["intent", "message"],
    },
}

ROUTER_SYSTEM = """You are a warm, sharp grants advisor chatting with a founder, student, or \
nonprofit lead about funding for their project. You are not a form to fill out — have a real \
conversation.

Gather, through natural back-and-forth, what you need to search well: what the project actually \
is, its field/domain, stage, team size, location, and roughly how much funding they need. Ask \
ONE follow-up question at a time, conversationally — never dump a checklist of questions. If the \
user's first message already covers most of this, don't re-ask what's already clear.

Set intent="search" as soon as you have enough to search meaningfully (project idea + field, and \
at least a rough sense of stage/team/location/funding — approximate answers like "just me" or \
"a few thousand dollars" are fine, don't demand precision).

Set intent="explain_grant" when the user asks about, or picks, one of the grants already shown \
(match it against the known grants list by title or position — e.g. "the first one" or "the NSF \
one" or its name). Put the matched source+external_id in selected_grant. Also set \
intent="explain_grant" with the SAME selected_grant if your previous message was a question about \
that grant's specific eligibility and the user just answered it — a grant deep-dive can take \
several turns of back-and-forth before it's resolved, and it should keep going until it's resolved.

Set intent="chat" for anything else — small talk, clarification, follow-up questions that aren't \
about a specific grant.

Never invent grant names, agencies, or numbers — you only know about grants that appear in the \
known grants list; if none are known yet, you can't explain_grant."""


def _history_block(messages: list[ChatMessage]) -> str:
    return "\n".join(f"{m.role.upper()}: {m.content}" for m in messages)


def _known_grants_block(known_grants: list[GrantRef]) -> str:
    if not known_grants:
        return "(none shown yet)"
    return "\n".join(f"- source={g.source} external_id={g.external_id} title=\"{g.title}\"" for g in known_grants)


async def route(messages: list[ChatMessage], known_grants: list[GrantRef]) -> dict:
    client = AsyncAnthropic()
    response = await client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=ROUTER_SYSTEM,
        tools=[ROUTE_TOOL],
        tool_choice={"type": "tool", "name": "route_conversation"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"KNOWN GRANTS SHOWN SO FAR:\n{_known_grants_block(known_grants)}\n\n"
                    f"CONVERSATION:\n{_history_block(messages)}"
                ),
            }
        ],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "route_conversation":
            return block.input
    return {"intent": "chat", "message": "Sorry, could you say that again?"}


ADVISE_TOOL = {
    "name": "advise_on_grant",
    "description": "Continue or resolve an eligibility interview about one specific grant.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["ask_question", "give_verdict"],
                "description": "'ask_question' if there's a specific, material eligibility criterion from the text you can't confirm from the conversation yet. 'give_verdict' once you have enough, or once further questions genuinely won't resolve it.",
            },
            "message": {
                "type": "string",
                "description": "For ask_question: the single targeted question. For give_verdict: a short conversational intro to the verdict.",
            },
            "eligibility_summary": {"type": "string", "description": "Only for give_verdict."},
            "qualifies": {
                "type": "string",
                "enum": ["yes", "likely", "unclear", "no"],
                "description": "Only for give_verdict. Grounded in the eligibility text plus what the user told you.",
            },
            "steps": {"type": "array", "items": {"type": "string"}, "description": "Only for give_verdict."},
            "confidence": {"type": "string", "enum": ["high", "low"], "description": "Only for give_verdict."},
        },
        "required": ["action", "message"],
    },
}

ADVISE_SYSTEM = """You are a grants advisor doing a real eligibility interview with someone about \
one specific grant, grounded ONLY in the eligibility/synopsis text provided — never invent \
criteria that aren't in that text.

Read the eligibility text and compare it against everything you already know about the user from \
the conversation. If a specific, material criterion (e.g. organization type, citizenship, \
location, business size, incorporation status, revenue) isn't yet confirmed by anything the user \
has said, ask ONE natural, specific question about just that criterion — don't ask about things \
already covered earlier in the conversation, and don't ask generic questions the eligibility text \
doesn't actually require.

Once you've confirmed the material criteria (or asked a couple of genuinely necessary questions \
and it's still ambiguous — that's fine, real eligibility text is often vague), give the verdict: a \
qualifies rating grounded in what you now know, a short eligibility summary, and clear next steps \
to actually apply. If the requirements text was unavailable or too thin to say anything real, say \
so plainly and set confidence to "low" rather than guessing."""


async def advise_on_grant(messages: list[ChatMessage], grant: GrantRef, detail: GrantDetail) -> dict:
    if detail.fetch_status != "ok":
        text = "[requirements page unavailable — could not be fetched or parsed]"
    else:
        text = (
            f"Eligibility: {detail.eligibility_text or '[not provided by source]'}\n"
            f"Synopsis: {detail.synopsis_text or '[not provided by source]'}\n"
            f"Deadline: {detail.deadline_display or 'not listed'}\n"
            f"Funding: {detail.award_floor or '?'} - {detail.award_ceiling or '?'}"
        )

    client = AsyncAnthropic()
    response = await client.messages.create(
        model=MODEL,
        max_tokens=1200,
        system=ADVISE_SYSTEM,
        tools=[ADVISE_TOOL],
        tool_choice={"type": "tool", "name": "advise_on_grant"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"GRANT: {grant.title}\n\n{text}\n\n"
                    f"FULL CONVERSATION SO FAR (for facts already established about the user, and "
                    f"any prior back-and-forth about this grant):\n{_history_block(messages)}"
                ),
            }
        ],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "advise_on_grant":
            return block.input
    return {"action": "give_verdict", "message": "I couldn't put together an answer for that one.", "steps": [], "confidence": "low"}
