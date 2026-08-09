import httpx

from app.models.schemas import GrantCandidate

AWARDS_URL = "https://api.nsf.gov/services/v1/awards.json"


async def search(keyword: str, rows: int = 10) -> list[GrantCandidate]:
    """Historical NSF awards (already funded) — supporting evidence for match
    explanations, not a live application target. No auth required."""
    params = {
        "keyword": keyword,
        "printFields": "id,title,awardeeName,fundsObligatedAmt,date",
        "rpp": rows,
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(AWARDS_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return []

    awards = data.get("response", {}).get("award", [])
    return [
        GrantCandidate(
            source="nsf.gov",
            external_id=award.get("id", ""),
            title=award.get("title", ""),
            agency="NSF",
            raw_snippet=f"Awarded to {award.get('awardeeName', 'unknown')}: ${award.get('fundsObligatedAmt', '?')}",
        )
        for award in awards
    ]
