import httpx

from app.models.schemas import GrantCandidate

AWARDS_URL = "https://api.www.sbir.gov/public/api/awards"
BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"


async def search(keyword: str, rows: int = 10) -> list[GrantCandidate]:
    """Live SBIR/STTR data. Public API has been observed rate-limited/unavailable
    (SBIR.gov's own docs note the API undergoes maintenance) — degrade gracefully,
    never let this source break the overall match request."""
    try:
        async with httpx.AsyncClient(timeout=5.0, headers={"User-Agent": BROWSER_UA}) as client:
            resp = await client.get(AWARDS_URL, params={"keyword": keyword, "rows": rows})
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return []

    if not isinstance(data, list):
        return []

    return [
        GrantCandidate(
            source="sbir.gov",
            external_id=str(award.get("award_id", award.get("firm", ""))),
            title=award.get("award_title", ""),
            agency=award.get("agency"),
            url=award.get("agency_tracking_number") and None,
            raw_snippet=award.get("abstract"),
        )
        for award in data[:rows]
    ]
