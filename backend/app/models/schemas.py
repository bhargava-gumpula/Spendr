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
    opportunity_number: str | None = None  # e.g. "USDA-NRCS-NHQ-WMBP-NOFO0001458" — helps target PDF search
    attachment_filenames: list[str] = []  # real NOFO/RFP PDF filenames, if any are attached
    fetch_status: str = "ok"  # "ok" | "unavailable"
    fetch_error: str | None = None


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class GrantRef(BaseModel):
    source: str
    external_id: str
    title: str
    url: str | None = None
    agency: str | None = None


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    known_grants: list[GrantRef] = []
    active_grant: GrantRef | None = None  # grant currently mid eligibility-interview, if any


class GrantExplanation(BaseModel):
    grant: GrantRef
    message: str
    eligibility_summary: str | None = None
    qualifies: str | None = None  # "yes" | "likely" | "unclear" | "no"
    deadline_display: str | None = None
    funding_range: str | None = None
    steps: list[str] = []
    confidence: str = "high"  # "high" | "low"
    fetch_status: str = "ok"  # "ok" | "unavailable"


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


class ChatResponse(BaseModel):
    reply: str
    matches: list[MatchResult] | None = None
    explanation: GrantExplanation | None = None
    active_grant: GrantRef | None = None  # echoes back which grant (if any) is still mid-interview


class DocumentChecklist(BaseModel):
    """Phase 2: the required-documents list pulled from a grant's actual full
    NOFO/RFP PDF — distinct from GrantExplanation.steps, which mixes
    eligibility fix-its with next actions rather than being a clean list."""

    grant: GrantRef
    found: bool
    required_documents: list[str] = []
    application_steps: list[str] = []
    source_url: str | None = None
    confidence: str = "high"  # "high" | "low"
