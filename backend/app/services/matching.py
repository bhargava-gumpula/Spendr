import asyncio

from app.models.schemas import GrantDetail, MatchResult, ProjectProfile
from app.services import claude_match, grants_gov, sbir
from app.services.dates import days_until, parse_deadline

MAX_CANDIDATES = 14


async def run_match(profile: ProjectProfile) -> list[MatchResult]:
    keyword = profile.field

    grants_gov_hits, sbir_hits = await asyncio.gather(
        grants_gov.search(keyword, rows=10),
        sbir.search(keyword, rows=6),
    )
    candidates = (grants_gov_hits + sbir_hits)[:MAX_CANDIDATES]

    if not candidates:
        return []

    grants_gov_ids = [c.external_id for c in candidates if c.source == "grants.gov"]
    fetched = await asyncio.gather(*[grants_gov.fetch_detail(cid) for cid in grants_gov_ids])
    details: dict[str, GrantDetail] = {d.external_id: d for d in fetched}
    for c in candidates:
        if c.source == "sbir.gov":
            details[c.external_id] = sbir.detail_for(c)

    scored = await claude_match.rank_and_explain(profile, candidates, details)

    results: list[MatchResult] = []
    for c in candidates:
        s = scored.get(c.external_id)
        detail = details.get(c.external_id)
        deadline_display = (detail.deadline_display if detail else None) or c.close_date
        deadline_date = parse_deadline(deadline_display)

        funding_range = None
        if detail and (detail.award_floor or detail.award_ceiling):
            funding_range = f"{detail.award_floor or '?'} – {detail.award_ceiling or '?'}"

        if s is None:
            results.append(
                MatchResult(
                    source=c.source,
                    external_id=c.external_id,
                    title=c.title,
                    agency=c.agency,
                    url=c.url,
                    deadline=deadline_date.isoformat() if deadline_date else None,
                    deadline_display=deadline_display,
                    days_until_deadline=days_until(deadline_date),
                    funding_range=funding_range,
                    match_score=0,
                    qualifies="unclear",
                    fit_reasons=[],
                    gap_reasons=["Could not be scored by the matching model."],
                    confidence="low",
                )
            )
            continue

        results.append(
            MatchResult(
                source=c.source,
                external_id=c.external_id,
                title=c.title,
                agency=c.agency,
                url=c.url,
                deadline=deadline_date.isoformat() if deadline_date else None,
                deadline_display=deadline_display,
                days_until_deadline=days_until(deadline_date),
                funding_range=funding_range,
                match_score=s["match_score"],
                qualifies=s["qualifies"],
                fit_reasons=s["fit_reasons"],
                gap_reasons=s["gap_reasons"],
                confidence=s["confidence"],
            )
        )

    results.sort(key=lambda r: r.match_score, reverse=True)
    return results


async def fetch_grant_detail(source: str, external_id: str, title: str) -> GrantDetail:
    """Re-fetch full detail for one previously-shown grant (stateless design —
    the frontend only carries a lightweight reference, not the full text)."""
    if source == "grants.gov":
        return await grants_gov.fetch_detail(external_id)
    from app.models.schemas import GrantCandidate

    stub = GrantCandidate(source=source, external_id=external_id, title=title)
    return sbir.detail_for(stub)
