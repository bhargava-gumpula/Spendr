import httpx

from app.models.schemas import GrantCandidate, GrantDetail

SEARCH_URL = "https://api.grants.gov/v1/api/search2"
DETAIL_URL = "https://api.grants.gov/v1/api/fetchOpportunity"


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


async def fetch_detail(opportunity_id: str) -> GrantDetail:
    """Full synopsis incl. eligibility text and deadline — used both to check
    qualification at match time and to build the Phase 2 checklist. If this
    fails, the caller must say so rather than guess at eligibility."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(DETAIL_URL, json={"opportunityId": int(opportunity_id)})
            resp.raise_for_status()
            payload = resp.json()
        data = payload["data"]
        syn = data["synopsis"]
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        return GrantDetail(external_id=opportunity_id, fetch_status="unavailable", fetch_error=str(exc))

    filenames = [
        att.get("fileName")
        for folder in (data.get("synopsisAttachmentFolders") or [])
        for att in (folder.get("synopsisAttachments") or [])
        if att.get("fileName")
    ]

    return GrantDetail(
        external_id=opportunity_id,
        eligibility_text=syn.get("applicantEligibilityDesc"),
        synopsis_text=syn.get("synopsisDesc"),
        deadline_display=syn.get("responseDateStr") or syn.get("responseDate"),
        award_floor=syn.get("awardFloorFormatted"),
        award_ceiling=syn.get("awardCeilingFormatted"),
        opportunity_number=data.get("opportunityNumber"),
        attachment_filenames=filenames,
        fetch_status="ok",
    )
