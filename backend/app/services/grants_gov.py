import httpx

from app.models.schemas import GrantCandidate

SEARCH_URL = "https://api.grants.gov/v1/api/search2"


async def search(keyword: str, rows: int = 10) -> list[GrantCandidate]:
    """Live, open funding opportunities. No auth required."""
    payload = {"keyword": keyword, "rows": rows, "oppStatuses": "forecasted|posted"}
    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.post(SEARCH_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()

    hits = data.get("data", {}).get("oppHits", [])
    return [
        GrantCandidate(
            source="grants.gov",
            external_id=hit["id"],
            title=hit.get("title", ""),
            agency=hit.get("agency"),
            close_date=hit.get("closeDate"),
            url=f"https://www.grants.gov/search-results-detail/{hit['id']}",
        )
        for hit in hits
    ]
