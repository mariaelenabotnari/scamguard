"""Routes for dashboard overview metrics, timelines, and UI shell metadata."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.dependencies import AuthServiceDep, BearerTokenDep, DashboardServiceDep
from app.dtos.dashboard_dto import DashboardOverviewDto, ShellSummaryDto, TimeRangeOption

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/dashboard/overview", response_model=DashboardOverviewDto)
def get_dashboard_overview(
    dashboard_service: DashboardServiceDep,
    range: Annotated[TimeRangeOption, Query()] = "7d",
) -> DashboardOverviewDto:
    return dashboard_service.get_overview(time_range=range)


@router.get("/meta/shell-summary", response_model=ShellSummaryDto)
def get_shell_summary(
    dashboard_service: DashboardServiceDep,
    auth_service: AuthServiceDep,
    token: BearerTokenDep = None,
) -> ShellSummaryDto:
    user = auth_service.get_current_user(token) if token else None
    role = user.role if user else "visitor"
    return dashboard_service.get_shell_summary(role=role)
