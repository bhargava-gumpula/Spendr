# Granted

Plain-language project description in, matched grants + demystified requirement checklists out.

## Local dev

Backend:
```
cd backend
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env  # fill in ANTHROPIC_API_KEY
./venv/bin/uvicorn app.main:app --reload --port 8000
```

Frontend:
```
cd frontend
npm install
npm run dev
```

Smoke-test the three data sources are reachable:
```
curl "http://localhost:8000/api/smoke-test?keyword=education"
```

## Deploy

Single Render web service (`render.yaml`) builds the React app and serves it as static
files from the FastAPI backend. Set `ANTHROPIC_API_KEY` in the Render dashboard.

## Data sources (Phase 1)

- **grants.gov** — live, open funding opportunities. No auth.
- **SBIR.gov** — live SBIR/STTR solicitations. No auth, but the public API has been
  observed rate-limited/unavailable — wrapped to degrade gracefully (returns empty list,
  never breaks the request).
- **NSF Award Search** — historical NSF awards. No auth. Used as supporting evidence in
  match explanations, not as an application target (it's already-funded, closed data).
