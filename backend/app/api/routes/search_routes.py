"""Routes for unified search across channels, messages, and clusters."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.dependencies import SearchServiceDep
from app.dtos.search_dto import UnifiedSearchResultsDto

router = APIRouter(prefix="/api/v1", tags=["search"])


@router.get("/search", response_model=UnifiedSearchResultsDto)
def search_all(
    search_service: SearchServiceDep,
    q: Annotated[str, Query(description="Search keywords")] = "",
) -> UnifiedSearchResultsDto:
    return search_service.search_all(query=q)
