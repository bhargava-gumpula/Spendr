from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import chat as chat_router
from app.routers import match as match_router
from app.services import grants_gov, nsf, sbir

app = FastAPI(title="Granted API")
app.include_router(match_router.router)
app.include_router(chat_router.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/smoke-test")
async def smoke_test(keyword: str = "education"):
    """Confirms all three source APIs are reachable right now. Dev-only sanity check."""
    results = {}
    for name, fn in [("grants_gov", grants_gov.search), ("sbir", sbir.search), ("nsf", nsf.search)]:
        try:
            candidates = await fn(keyword, rows=2)
            results[name] = {"ok": True, "count": len(candidates)}
        except Exception as exc:
            results[name] = {"ok": False, "error": str(exc)}
    return results


# Serve built React app in production (single Render web service).
# The frontend is a client-side-routed SPA (/, /chat), so any path that
# isn't an actual built asset falls back to index.html rather than 404ing.
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        candidate = frontend_dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(frontend_dist / "index.html")
