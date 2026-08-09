import asyncio

from app.models.schemas import GrantDetail, MatchResult, ProjectProfile
from app.services import ai_match, grants_gov, sbir, web_search
from app.services.dates import days_until, parse_deadline

MAX_CANDIDATES = 14


async def run_match(profile: ProjectProfile) -> list[MatchResult]:
    keyword = profile.field

    # Run all three sources in parallel — web search is the slow one
    # (real search, bounded to a few rounds), so total latency is bounded
    # by it rather than the sum of all three.
    grants_gov_hits, sbir_hits, web_hits = await asyncio.gather(
        grants_gov.search(keyword, rows=10),
        sbir.search(keyword, rows=6),
        web_search.find_web_grants(profile),
    )
    candidates = (grants_gov_hits + sbir_hits + web_hits)[:MAX_CANDIDATES]

    if not candidates:
        return []

    grants_gov_ids = [c.external_id for c in candidates if c.source == "grants.gov"]
    fetched = await asyncio.gather(*[grants_gov.fetch_detail(cid) for cid in grants_gov_ids])
    details: dict[str, GrantDetail] = {d.external_id: d for d in fetched}
    for c in candidates:
        if c.source == "sbir.gov":
            details[c.external_id] = sbir.detail_for(c)
        elif c.source == "web":
            # The search summary IS the grounded text — re-searching per
            # candidate just for ranking would be too slow to be worth it.
            details[c.external_id] = GrantDetail(
                external_id=c.external_id,
                eligibility_text=c.raw_snippet,
                synopsis_text=c.raw_snippet,
                deadline_display=c.close_date,
                fetch_status="ok",
            )

    scored = await ai_match.rank_and_explain(profile, candidates, details)

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

        # Data-integrity guardrail: don't trust the model's self-reported
        # confidence when we know the source text was unavailable.
        qualifies = s["qualifies"]
        confidence = s["confidence"]
        gap_reasons = s["gap_reasons"]
        if detail is None or detail.fetch_status != "ok":
            qualifies = "unclear"
            confidence = "low"
            if not any("unavailable" in g.lower() or "fetch" in g.lower() for g in gap_reasons):
                gap_reasons = [*gap_reasons, "Eligibility page unavailable — could not be verified from the source."]

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
                qualifies=qualifies,
                fit_reasons=s["fit_reasons"],
                gap_reasons=gap_reasons,
                confidence=confidence,
            )
        )

    results.sort(key=lambda r: r.match_score, reverse=True)
    return results


async def fetch_grant_detail(source: str, external_id: str, title: str) -> GrantDetail:
    """Re-fetch full detail for one previously-shown grant (stateless design —
    the frontend only carries a lightweight reference, not the full text)."""
    if source == "grants.gov":
        return await grants_gov.fetch_detail(external_id)
    if source == "web":
        # external_id is the URL for web-sourced candidates. Worth a fresh,
        # more targeted lookup here — this is a deliberate one-off user
        # action, not blocking a results list.
        return await web_search.fetch_web_detail(title, external_id)
    from app.models.schemas import GrantCandidate

    stub = GrantCandidate(source=source, external_id=external_id, title=title)
    return sbir.detail_for(stub)
