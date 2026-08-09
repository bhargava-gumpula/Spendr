from fastapi import APIRouter

from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    GrantExplanation,
    GrantRef,
    ProjectProfile,
)
from app.services import ai_chat
from app.services.matching import fetch_grant_detail, run_match

router = APIRouter()


async def _run_interview_turn(messages, grant: GrantRef) -> ChatResponse:
    detail = await fetch_grant_detail(grant.source, grant.external_id, grant.title)
    advice = await ai_chat.advise_on_grant(messages, grant, detail)

    if advice.get("action") == "ask_question":
        # Still interviewing — keep this grant active for the next turn.
        return ChatResponse(reply=advice.get("message", ""), active_grant=grant)

    # Data-integrity guardrail: don't trust the model's self-reported confidence
    # when we know the source text was unavailable — enforce it, don't ask nicely.
    qualifies = advice.get("qualifies")
    confidence = advice.get("confidence", "high")
    if detail.fetch_status != "ok":
        qualifies = "unclear"
        confidence = "low"

    return ChatResponse(
        reply=advice.get("message", ""),
        explanation=GrantExplanation(
            grant=grant,
            message=advice.get("message", ""),
            eligibility_summary=advice.get("eligibility_summary"),
            qualifies=qualifies,
            deadline_display=detail.deadline_display,
            funding_range=(f"{detail.award_floor or '?'} – {detail.award_ceiling or '?'}" if (detail.award_floor or detail.award_ceiling) else None),
            steps=advice.get("steps", []),
            confidence=confidence,
            fetch_status=detail.fetch_status,
        ),
        # active_grant cleared: interview resolved
    )


@router.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    # Deterministic continuation: if a grant is already mid-interview, keep
    # going with it directly — don't ask an LLM router to re-decide intent
    # every turn, that's an unforced error a smaller model can get wrong.
    if req.active_grant is not None:
        return await _run_interview_turn(req.messages, req.active_grant)

    decision = await ai_chat.route(req.messages, req.known_grants)
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
        return await _run_interview_turn(req.messages, match_ref)

    return ChatResponse(reply=message)
