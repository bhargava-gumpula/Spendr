from pydantic import BaseModel


class ProjectProfile(BaseModel):
    description: str
    field: str
    stage: str
    team_size: int
    location: str
    funding_needed: str


class GrantCandidate(BaseModel):
    source: str  # "grants.gov" | "sbir.gov"
    external_id: str
    title: str
    agency: str | None = None
    close_date: str | None = None
    url: str | None = None
    raw_snippet: str | None = None


class GrantDetail(BaseModel):
    """Full text pulled for one candidate, used both to check qualification
    (Phase 1) and to build the requirement checklist (Phase 2)."""

    external_id: str
    eligibility_text: str | None = None
    synopsis_text: str | None = None
    deadline: str | None = None  # ISO date, if known
    deadline_display: str | None = None  # raw "Sep 01, 2026" style string from source
    award_floor: str | None = None
    award_ceiling: str | None = None
    fetch_status: str = "ok"  # "ok" | "unavailable"
    fetch_error: str | None = None


class MatchResult(BaseModel):
    source: str
    external_id: str
    title: str
    agency: str | None = None
    url: str | None = None
    deadline: str | None = None
    deadline_display: str | None = None
    days_until_deadline: int | None = None
    funding_range: str | None = None
    match_score: int
    qualifies: str  # "yes" | "likely" | "unclear" | "no"
    fit_reasons: list[str]
    gap_reasons: list[str]
    confidence: str  # "high" | "low"
