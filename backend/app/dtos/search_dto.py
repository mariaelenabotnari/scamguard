"""DTOs for unified full-text search across channels, messages, and clusters."""

from pydantic import BaseModel, ConfigDict, Field

from app.dtos.cluster_dto import ClusterSummaryDto
from app.dtos.scoring_dto import RankedChannelDto, RiskBand, ScoreExplanationDto


class SearchMessageHitDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    channel_id: str = Field(..., alias="channelId")
    handle: str
    posted_at: str = Field(..., alias="postedAt")
    snippet: str
    narrative_category: str = Field(..., alias="narrativeCategory")
    cluster_id: str | None = Field(default=None, alias="clusterId")
    channel_score: int = Field(..., alias="channelScore")
    risk_band: RiskBand = Field(..., alias="riskBand")
    explanation: ScoreExplanationDto


class UnifiedSearchResultsDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    query: str
    channels: list[RankedChannelDto]
    messages: list[SearchMessageHitDto]
    clusters: list[ClusterSummaryDto]
