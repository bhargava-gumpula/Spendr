from app.models.schemas import GrantCandidate, GrantDetail, ProjectProfile
from app.services.ai_client import call_function

TOOL = {
    "type": "function",
    "name": "report_matches",
    "description": "Report ranked grant matches with qualification assessment.",
    "parameters": {
        "type": "object",
        "properties": {
            "matches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "external_id": {"type": "string"},
                        "match_score": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100,
                            "description": "Relevance to this project, 0-100. Not just keyword overlap — weigh field, stage, team size, location, and funding needed.",
                        },
                        "qualifies": {
                            "type": "string",
                            "enum": ["yes", "likely", "unclear", "no"],
                            "description": "'unclear' if eligibility text was unavailable or too vague to judge — never guess yes/no without evidence.",
                        },
                        "fit_reasons": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific reasons this grant fits, citing the actual eligibility/synopsis text.",
                        },
                        "gap_reasons": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific reasons it might not fit or requirements couldn't be verified.",
                        },
                        "confidence": {
                            "type": "string",
                            "enum": ["high", "low"],
                            "description": "'low' if eligibility text was missing, truncated, or ambiguous.",
                        },
                    },
                    "required": ["external_id", "match_score", "qualifies", "fit_reasons", "gap_reasons", "confidence"],
                },
            }
        },
        "required": ["matches"],
    },
}

SYSTEM_PROMPT = """You are a grants advisor helping an early-stage founder, student, or small \
nonprofit understand which funding opportunities actually fit them. You are not a search \
engine — rank by genuine fit against the project's field, stage, team size, location, and \
funding needed, and explain your reasoning like an advisor would.

Ground every qualification judgment ONLY in the eligibility/synopsis text provided for each \
candidate. If that text is missing or marked unavailable, you must NOT guess whether the \
project qualifies — set qualifies to "unclear" and confidence to "low", and say in \
gap_reasons that eligibility couldn't be verified from the source. Never fabricate \
eligibility criteria that aren't in the provided text."""


def _candidate_block(candidate: GrantCandidate, detail: GrantDetail) -> str:
    if detail.fetch_status != "ok":
        elig = "[eligibility page unavailable — could not be fetched or parsed]"
    else:
        elig = (detail.eligibility_text or "[no eligibility text provided by source]")[:1500]

    synopsis = (detail.synopsis_text or candidate.raw_snippet or "")[:800]
    deadline = detail.deadline_display or candidate.close_date or "not listed"
    funding = ""
    if detail.award_floor or detail.award_ceiling:
        funding = f"Funding range: {detail.award_floor or '?'} - {detail.award_ceiling or '?'}\n"

    return (
        f"### {candidate.external_id} — {candidate.title}\n"
        f"Source: {candidate.source} | Agency: {candidate.agency or 'unknown'}\n"
        f"Deadline: {deadline}\n"
        f"{funding}"
        f"Eligibility: {elig}\n"
        f"Synopsis: {synopsis}\n"
    )


async def rank_and_explain(
    profile: ProjectProfile,
    candidates: list[GrantCandidate],
    details: dict[str, GrantDetail],
) -> dict[str, dict]:
    """Returns external_id -> {match_score, qualifies, fit_reasons, gap_reasons, confidence}."""
    if not candidates:
        return {}

    profile_block = (
        f"Project description: {profile.description}\n"
        f"Field: {profile.field}\n"
        f"Stage: {profile.stage}\n"
        f"Team size: {profile.team_size}\n"
        f"Location: {profile.location}\n"
        f"Funding needed: {profile.funding_needed}\n"
    )
    candidate_blocks = "\n".join(
        _candidate_block(c, details.get(c.external_id, GrantDetail(external_id=c.external_id, fetch_status="unavailable")))
        for c in candidates
    )

    result = await call_function(
        system=SYSTEM_PROMPT,
        user_content=f"PROJECT:\n{profile_block}\nCANDIDATE GRANTS:\n{candidate_blocks}",
        tool=TOOL,
    )
    matches = result.get("matches", [])
    return {m["external_id"]: m for m in matches}
