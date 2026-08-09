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
one" or its name). Put the matched source+external_id in selected_grant.

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


EXPLAIN_TOOL = {
    "name": "explain_application",
    "description": "Explain how to apply to this specific grant, grounded only in the provided text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Friendly conversational explanation of how to apply."},
            "eligibility_summary": {"type": "string"},
            "steps": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "string", "enum": ["high", "low"]},
        },
        "required": ["message", "steps", "confidence"],
    },
}

EXPLAIN_SYSTEM = """You are a grants advisor explaining, in plain language, how someone would \
apply to one specific grant. Ground everything ONLY in the eligibility/synopsis text provided — \
if it's missing, marked unavailable, or too thin to describe real steps, say so plainly in the \
message and set confidence to "low" with a short, honest steps list (e.g. just "read the full \
opportunity page" ) instead of inventing an application process."""


async def explain_application(grant: GrantRef, detail: GrantDetail) -> dict:
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
        system=EXPLAIN_SYSTEM,
        tools=[EXPLAIN_TOOL],
        tool_choice={"type": "tool", "name": "explain_application"},
        messages=[{"role": "user", "content": f"GRANT: {grant.title}\n\n{text}"}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "explain_application":
            return block.input
    return {"message": "I couldn't put together an explanation for that one.", "steps": [], "confidence": "low"}
