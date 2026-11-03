"""Routes for channel coordination risk ranking, channel profiles, and alerts."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.dependencies import (
    AlertServiceDep,
    AuthServiceDep,
    BearerTokenDep,
    ScoringServiceDep,
)
from app.dtos.scoring_dto import (
    AlertItemDto,
    ChannelDetailDto,
    CoordinationGroupDto,
    RankedChannelDto,
)

scoring_router = APIRouter(prefix="/api/v1", tags=["scoring-and-alerts"])


@scoring_router.get("/coordination-groups", response_model=list[CoordinationGroupDto])
def list_coordination_groups(
    scoring_service: ScoringServiceDep,
) -> list[CoordinationGroupDto]:
    return scoring_service.get_channel_coordination_groups()


@scoring_router.get("/ranking", response_model=list[RankedChannelDto])
def list_ranked_channels(
    scoring_service: ScoringServiceDep,
    min_score: Annotated[int, Query(ge=0, le=100)] = 0,
    narrative: Annotated[str | None, Query()] = None,
) -> list[RankedChannelDto]:
    return scoring_service.list_ranked_channels(min_score=min_score, narrative=narrative)


@scoring_router.post("/ranking/recalculate", response_model=list[RankedChannelDto])
def recalculate_ranked_channels(
    scoring_service: ScoringServiceDep,
    auth_service: AuthServiceDep,
    token: BearerTokenDep,
) -> list[RankedChannelDto]:
    auth_service.require_roles(token, ("journalist", "admin"))
    return scoring_service.recalculate_all_scores()


@scoring_router.get("/channels/{channel_id}", response_model=ChannelDetailDto)
def get_channel_detail(
    channel_id: str,
    scoring_service: ScoringServiceDep,
) -> ChannelDetailDto:
    return scoring_service.get_channel_detail(channel_id)


@scoring_router.get("/alerts", response_model=list[AlertItemDto])
def list_alerts(
    alert_service: AlertServiceDep,
    severity: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
) -> list[AlertItemDto]:
    return alert_service.list_alerts(severity=severity, status=status)


@scoring_router.post("/alerts/{alert_id}/dismiss", response_model=AlertItemDto)
def dismiss_alert(
    alert_id: str,
    alert_service: AlertServiceDep,
) -> AlertItemDto:
    return alert_service.dismiss_alert(alert_id)
