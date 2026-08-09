from fastapi import APIRouter

from app.models.schemas import MatchResult, ProjectProfile
from app.services.matching import run_match

router = APIRouter()


@router.post("/api/match", response_model=list[MatchResult])
async def match(profile: ProjectProfile) -> list[MatchResult]:
    return await run_match(profile)
