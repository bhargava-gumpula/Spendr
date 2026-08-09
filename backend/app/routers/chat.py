from fastapi import APIRouter

from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    GrantExplanation,
    GrantRef,
    ProjectProfile,
)
from app.services import claude_chat
from app.services.matching import fetch_grant_detail, run_match

router = APIRouter()


@router.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    decision = await claude_chat.route(req.messages, req.known_grants)
    intent = decision.get("intent", "chat")
    message = decision.get("message", "")

    if intent == "search":
        raw_profile = decision.get("profile") or {}
        profile = ProjectProfile(
            description=raw_profile.get("description") or "",
            field=raw_profile.get("field") or "",
            stage=raw_profile.get("stage") or "unspecified",
            team_size=int(raw_profile.get("team_size") or 1),
            location=raw_profile.get("location") or "unspecified",
            funding_needed=raw_profile.get("funding_needed") or "unspecified",
        )
        matches = await run_match(profile)
        if not matches:
            return ChatResponse(
                reply=f"{message}\n\nI couldn't find any live opportunities matching \"{profile.field}\" right now — want to try a different angle on the field or focus area?",
            )
        top = matches[:5]
        return ChatResponse(reply=message, matches=top)

    if intent == "explain_grant":
        sel = decision.get("selected_grant") or {}
        match_ref = next(
            (g for g in req.known_grants if g.source == sel.get("source") and g.external_id == sel.get("external_id")),
            None,
        )
        if match_ref is None:
            return ChatResponse(reply="I'm not sure which grant you mean — could you name it or say which one (first, second...)?")

        detail = await fetch_grant_detail(match_ref.source, match_ref.external_id, match_ref.title)
        advice = await claude_chat.advise_on_grant(req.messages, match_ref, detail)

        if advice.get("action") == "ask_question":
            # Still interviewing — just a chat reply, no verdict card yet.
            return ChatResponse(reply=advice.get("message", ""))

        return ChatResponse(
            reply=advice.get("message", ""),
            explanation=GrantExplanation(
                grant=match_ref,
                message=advice.get("message", ""),
                eligibility_summary=advice.get("eligibility_summary"),
                qualifies=advice.get("qualifies"),
                deadline_display=detail.deadline_display,
                funding_range=(f"{detail.award_floor or '?'} – {detail.award_ceiling or '?'}" if (detail.award_floor or detail.award_ceiling) else None),
                steps=advice.get("steps", []),
                confidence=advice.get("confidence", "high"),
                fetch_status=detail.fetch_status,
            ),
        )

    return ChatResponse(reply=message)
