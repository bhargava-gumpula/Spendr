from app.models.schemas import GrantCandidate, GrantDetail, ProjectProfile
from app.services.ai_client import call_with_web_search

REPORT_TOOL = {
    "type": "function",
    "name": "report_web_grants",
    "description": "Report real, currently-open grant opportunities found via web search.",
    "parameters": {
        "type": "object",
        "properties": {
            "grants": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "agency": {"type": "string", "description": "The funder/organization name."},
                        "url": {"type": "string", "description": "Direct URL to the opportunity, from search results — never invented."},
                        "summary": {"type": "string", "description": "What it funds and who's eligible, from what you actually read."},
                        "deadline_display": {"type": "string", "description": "Deadline as stated on the source, or 'not listed'."},
                    },
                    "required": ["title", "url", "summary"],
                },
            }
        },
        "required": ["grants"],
    },
}

SEARCH_SYSTEM = """You are a grants researcher searching the live web for real funding \
opportunities that grants.gov and SBIR.gov wouldn't cover — state programs, city programs, \
private foundations, corporate giving programs. Only report opportunities you actually found \
in search results, with their real URL. Never invent a grant, a URL, or a deadline. Do at most \
2-3 searches, then call report_web_grants — report whatever real opportunities you found even if \
the list is short or empty, rather than continuing to search indefinitely."""


async def find_web_grants(profile: ProjectProfile, limit: int = 3) -> list[GrantCandidate]:
    user_content = (
        f"Project: {profile.description}\n"
        f"Field: {profile.field} | Stage: {profile.stage} | Team size: {profile.team_size} | "
        f"Location: {profile.location} | Funding needed: {profile.funding_needed}\n\n"
        f"Find up to {limit} real, currently-open grant opportunities for this project from "
        f"outside grants.gov and SBIR.gov."
    )
    result = await call_with_web_search(SEARCH_SYSTEM, user_content, REPORT_TOOL)
    grants = result.get("grants", [])[:limit]

    return [
        GrantCandidate(
            source="web",
            external_id=g["url"],
            title=g.get("title", "Untitled opportunity"),
            agency=g.get("agency"),
            close_date=g.get("deadline_display"),
            url=g.get("url"),
            raw_snippet=g.get("summary"),
        )
        for g in grants
        if g.get("url")
    ]


DETAIL_TOOL = {
    "type": "function",
    "name": "report_web_grant_detail",
    "description": "Report what you found about this specific grant's eligibility and application process.",
    "parameters": {
        "type": "object",
        "properties": {
            "found": {"type": "boolean", "description": "False if you could not access/verify real info about this specific grant."},
            "eligibility_text": {"type": "string"},
            "synopsis_text": {"type": "string"},
            "deadline_display": {"type": "string"},
            "award_floor": {"type": "string"},
            "award_ceiling": {"type": "string"},
        },
        "required": ["found"],
    },
}

DETAIL_SYSTEM = """You are looking up real details for one specific grant opportunity found \
earlier via web search. Search for and read its actual page. Report only what you can verify \
from real sources — if you can't access or confirm real details, set found=false rather than \
guessing."""


async def fetch_web_detail(title: str, url: str) -> GrantDetail:
    result = await call_with_web_search(
        DETAIL_SYSTEM,
        f"Grant: {title}\nURL: {url}\n\nLook up its eligibility criteria and application process.",
        DETAIL_TOOL,
        max_tool_calls=3,
    )
    if not result or not result.get("found"):
        return GrantDetail(external_id=url, fetch_status="unavailable")

    return GrantDetail(
        external_id=url,
        eligibility_text=result.get("eligibility_text"),
        synopsis_text=result.get("synopsis_text"),
        deadline_display=result.get("deadline_display"),
        award_floor=result.get("award_floor"),
        award_ceiling=result.get("award_ceiling"),
        fetch_status="ok",
    )
