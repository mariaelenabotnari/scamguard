"""HTTP routes for triggering the unified analysis pipeline."""

from fastapi import APIRouter

from app.core.dependencies import (
    AnalysisPipelineServiceDep,
    AuthServiceDep,
    BearerTokenDep,
)
from app.dtos.analysis_dto import AnalysisPipelineResultDto

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


@router.post("/run", response_model=AnalysisPipelineResultDto)
def trigger_analysis_pipeline(
    token: BearerTokenDep,
    auth_service: AuthServiceDep,
    analysis_service: AnalysisPipelineServiceDep,
) -> AnalysisPipelineResultDto:
    auth_service.require_roles(token, ("journalist", "admin"))
    return analysis_service.run_analysis_pipeline()
