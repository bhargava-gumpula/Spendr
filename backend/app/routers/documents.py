from fastapi import APIRouter

from app.models.schemas import DocumentChecklist, GrantRef
from app.services import web_search
from app.services.matching import fetch_grant_detail

router = APIRouter()


@router.post("/api/documents", response_model=DocumentChecklist)
async def documents(grant: GrantRef) -> DocumentChecklist:
    """Phase 2: pull the real required-documents checklist from a grant's full
    announcement/NOFO PDF. Opt-in and separate from /api/chat's eligibility
    interview — reading a full PDF via live search takes real time, so this
    only runs when the user explicitly asks for it, not on every match."""
    detail = await fetch_grant_detail(grant.source, grant.external_id, grant.title)
    return await web_search.extract_document_checklist(grant, detail)
