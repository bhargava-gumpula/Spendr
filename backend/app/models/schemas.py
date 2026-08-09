from pydantic import BaseModel


class ProjectProfile(BaseModel):
    description: str
    field: str
    stage: str
    team_size: int
    location: str
    funding_needed: str


class GrantCandidate(BaseModel):
    source: str  # "grants.gov" | "sbir.gov" | "nsf.gov"
    external_id: str
    title: str
    agency: str | None = None
    close_date: str | None = None
    url: str | None = None
    raw_snippet: str | None = None
