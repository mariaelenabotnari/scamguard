"""HTTP routes for listing the 10 disinformation categories and running batch classification."""

from fastapi import APIRouter

from app.core.dependencies import (
    AuthServiceDep,
    BearerTokenDep,
    NarrativeClassifierServiceDep,
)
from app.dtos.narrative_dto import (
    BatchClassifyInputDto,
    NarrativeCategorySpecDto,
    NarrativePredictionDto,
)

router = APIRouter(prefix="/api/v1/narratives", tags=["narratives"])


@router.get("/categories", response_model=list[NarrativeCategorySpecDto])
def get_narrative_categories(
    classifier_service: NarrativeClassifierServiceDep,
) -> list[NarrativeCategorySpecDto]:
    return classifier_service.list_categories()


@router.post("/classify", response_model=list[NarrativePredictionDto])
def classify_texts_batch(
    payload: BatchClassifyInputDto,
    token: BearerTokenDep,
    auth_service: AuthServiceDep,
    classifier_service: NarrativeClassifierServiceDep,
) -> list[NarrativePredictionDto]:
    auth_service.require_roles(token, ("journalist", "admin"))
    return classifier_service.classify_batch(payload)
