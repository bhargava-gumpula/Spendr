import httpx

from app.models.schemas import GrantCandidate, GrantDetail

SOLICITATIONS_URL = "https://api.www.sbir.gov/public/api/solicitations"
BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"

# SBIR/STTR eligibility is standardized across solicitations, unlike grants.gov.
# Used as the "eligibility text" fed to Claude for qualification checks, since
# a per-solicitation detail call isn't available/needed for this criteria.
STANDARD_ELIGIBILITY = (
    "Eligible applicants must be a for-profit small business located in the "
    "US, majority-owned and controlled by US citizens or permanent residents "
    "(or another eligible small business), with 500 or fewer employees "
    "including affiliates. The principal investigator must be primarily "
    "employed by the small business at the time of award and for the "
    "duration of the project."
)


async def search(keyword: str, rows: int = 10) -> list[GrantCandidate]:
    """Live, open SBIR/STTR solicitations. Public API has been observed
    rate-limited/unavailable (SBIR.gov's own docs note the API undergoes
    maintenance) — degrade gracefully, never let this source break the
    overall match request."""
    try:
        async with httpx.AsyncClient(timeout=6.0, headers={"User-Agent": BROWSER_UA}) as client:
            resp = await client.get(
                SOLICITATIONS_URL, params={"keyword": keyword, "rows": rows, "open": 1}
            )
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return []

    if not isinstance(data, list):
        return []

    return [
        GrantCandidate(
            source="sbir.gov",
            external_id=str(sol.get("solicitation_number", sol.get("solicitation_title", ""))),
            title=sol.get("solicitation_title", ""),
            agency=sol.get("agency"),
            close_date=sol.get("close_date"),
            url=sol.get("sbir_url") or sol.get("solicitation_agency_url"),
            raw_snippet=sol.get("solicitation_description") or sol.get("description"),
        )
        for sol in data[:rows]
    ]


def detail_for(candidate: GrantCandidate) -> GrantDetail:
    """No extra fetch needed — SBIR eligibility is standardized, and the
    search result already carries the description + close date."""
    return GrantDetail(
        external_id=candidate.external_id,
        eligibility_text=STANDARD_ELIGIBILITY,
        synopsis_text=candidate.raw_snippet,
        deadline_display=candidate.close_date,
        fetch_status="ok",
    )
