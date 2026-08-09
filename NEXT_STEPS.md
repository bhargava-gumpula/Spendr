# Next Steps — Handoff Notes

Written mid-session for whoever (human or AI) picks this up next. See
[`PROJECT.md`](PROJECT.md) for full architecture/software/process documentation —
this file is just "what's open right now."

---

## 🔴 Active bug — investigate first

**Symptom (reported by user):** chat stopped responding after working for a few
messages in a row.

**What I found before being interrupted:**
- Backend was healthy the whole time — `/api/health` responded, and the backend log
  showed a long unbroken string of `200 OK` on `/api/chat` and `/api/documents`. No
  crash, no exception.
- Browser console had a real bug: **dozens of repeated React "duplicate key" warnings**
  for the same web-search grant URL:
  ```
  Encountered two children with the same key, `%s`.
  web-https://www.vta.org/programs/congestion-management-program/grants
  ```
  Key format is `${source}-${external_id}`, and for `source: "web"`,
  `external_id` is the URL. This means **the same web-search grant URL ended up in
  the same `matches` array more than once.**
- `mergeKnownGrants` in `frontend/src/pages/Chat.jsx` dedupes when *adding* to
  `knownGrants`, but the dedup bug is likely upstream — either the backend's
  `find_web_grants()` (`backend/app/services/web_search.py`) returning duplicate
  URLs from one search, or something appending the same `matches` array twice into
  `messages` state.
- I was mid-way through checking whether the tab was actually frozen (typing
  indicator, send button state, DOM node count) when the session was interrupted.
  DOM node count looked sane (330 nodes) — **not conclusively a runaway
  infinite-render loop**, but the duplicate-key warning firing 40+ times in a row is
  itself suspicious and worth root-causing, not just silencing.

**Where to start:**
1. Reproduce: run a search that returns web-sourced results, check console for the
   duplicate-key warning.
2. Check `find_web_grants()` in `web_search.py` — does the model ever return the same
   URL twice in one `report_web_grants` call? Add a dedup-by-URL when building the
   returned `GrantCandidate` list, regardless of root cause — that's a cheap, safe
   fix either way.
3. Actually confirm whether the UI was frozen or just showing a console warning with
   no functional impact — re-test by sending a fresh message and watching whether a
   response comes back within normal time (~5-10s for grants.gov/SBIR-only, ~20-30s
   if web search is triggered).
4. If it genuinely hangs: check whether `loading` state in `Chat.jsx` ever fails to
   reset to `false` (e.g. an unhandled promise rejection in `sendMessage`'s `try`
   block that isn't hitting `catch`/`finally` correctly), which would leave the
   composer permanently disabled.

---

## What's done (see PROJECT.md §6 for full status table)

- Phase 0 — scaffold
- Phase 1 — grant matching, conversational UI, eligibility interview, live web search
  (pulled forward from Phase 3)
- Phase 2 — document checklist extraction from real PDFs (opt-in button on the
  verdict card)
- UI: dark navy/blue theme, Figma-inspired landing page

## What's NOT done

- **Phase 3 remaining scope** (originally: plain-language RFP summaries; NSF/
  USAspending context folded into match explanations — largely superseded by live
  web search, may not be worth doing as originally scoped)
- **Phase 4 — Deploy to Render.** `render.yaml` exists and is believed correct
  (single web service, SPA fallback route already implemented in `main.py`) but
  **has never actually been deployed or tested on Render.** Do this only with the
  user's explicit go-ahead per their standing rule (see below).

## Known trade-offs / things to keep in mind

- Web search adds real latency: ~20-30s for a search turn, up to ~30s for the
  document-checklist read. This is inherent to live search via the model, not a bug.
- SBIR.gov's public API has been flaky/rate-limited throughout the build. The app
  degrades gracefully (empty list, not an error) when this happens — expected.
- The Azure AI Foundry resource has multiple model deployments with **separate
  quotas** — `gpt-5.5`'s deployment hit "Insufficient quota / deployment_disabled"
  during testing while `gpt-4.1-mini` (the actual configured `OPENAI_MODEL`) kept
  working fine. If something suddenly stops working, check which model is being
  hit and whether that specific deployment's quota is the issue — don't assume the
  whole endpoint/key is dead.
- `backend/.env` (not committed, gitignored) holds `OPENAI_API_KEY`,
  `OPENAI_BASE_URL` (Azure endpoint), `OPENAI_MODEL` (currently `gpt-4.1-mini`).

## Standing process rules (from the user, this session)

- **Test the full thing end-to-end after any change**, with real AI calls, not just
  mocked ones, before calling something done.
- **Never start a new phase without the user's explicit go-ahead**, even if the
  plan already lists it as next.
