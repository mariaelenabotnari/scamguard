"""DTOs for channel coordination risk scores, score explanations, channel profiles, and alerts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RiskBand = Literal["low", "medium", "high"]
AlertSeverity = Literal["high", "medium", "low"]
AlertStatus = Literal["new", "seen", "dismissed"]


class ScoreBreakdownDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cluster_participation_share: int = Field(..., alias="clusterParticipationShare")
    copy_delay_factor: int = Field(..., alias="copyDelayFactor")
    co_movement_repetition: int = Field(..., alias="coMovementRepetition")
    narrative_weight: int = Field(..., alias="narrativeWeight")
    dominant_factor: str = Field(..., alias="dominantFactor")


class ScoreExplanationDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    parameter_version: str = Field(..., alias="parameterVersion")
    summary: str
    breakdown: ScoreBreakdownDto
    linked_clusters_count: int = Field(..., alias="linkedClustersCount")
    co_moving_channels: list[str] = Field(..., alias="coMovingChannels")
    median_lead_lag_seconds: int = Field(..., alias="medianLeadLagSeconds")
    primary_narrative: str = Field(..., alias="primaryNarrative")


class RankedChannelDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    handle: str
    title: str
    language: Literal["RO", "RU", "MIXED"]
    score: int
    coordination_score: int = Field(default=0, alias="coordinationScore")
    narrative_risk: RiskBand = Field(default="low", alias="narrativeRisk")
    has_sufficient_data: bool = Field(default=True, alias="hasSufficientData")
    risk_band: RiskBand = Field(..., alias="riskBand")
    sparkline: list[int]
    clusters_joined_7d: int = Field(..., alias="clustersJoined7d")
    primary_narrative: str = Field(..., alias="primaryNarrative")
    explanation: ScoreExplanationDto


class ChannelScoreHistoryPointDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    date_label: str = Field(..., alias="dateLabel")
    score: int


class CoMovingChannelDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    channel_id: str = Field(..., alias="channelId")
    handle: str
    title: str
    shared_clusters_count: int = Field(..., alias="sharedClustersCount")
    median_time_diff_seconds: int = Field(..., alias="medianTimeDiffSeconds")
    average_similarity: float = Field(..., alias="averageSimilarity")


class ChannelJoinedClusterDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cluster_id: str = Field(..., alias="clusterId")
    headline_summary: str = Field(..., alias="headlineSummary")
    narrative_category: str = Field(..., alias="narrativeCategory")
    posted_at: str = Field(..., alias="postedAt")
    delay_seconds: int = Field(..., alias="delaySeconds")
    similarity_score: float = Field(..., alias="similarityScore")


class ChannelDetailDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    handle: str
    title: str
    language: Literal["RO", "RU", "MIXED"]
    subscribers_count: int = Field(..., alias="subscribersCount")
    status: Literal["active", "paused"]
    added_at: str = Field(..., alias="addedAt")
    added_by: str = Field(..., alias="addedBy")
    score: int
    coordination_score: int = Field(default=0, alias="coordinationScore")
    narrative_risk: RiskBand = Field(default="low", alias="narrativeRisk")
    has_sufficient_data: bool = Field(default=True, alias="hasSufficientData")
    risk_band: RiskBand = Field(..., alias="riskBand")
    score_history: list[ChannelScoreHistoryPointDto] = Field(..., alias="scoreHistory")
    explanation: ScoreExplanationDto
    co_moving_channels: list[CoMovingChannelDto] = Field(..., alias="coMovingChannels")
    joined_clusters: list[ChannelJoinedClusterDto] = Field(..., alias="joinedClusters")


class CoordinationGroupDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    group_id: str = Field(..., alias="groupId")
    channel_ids: list[str] = Field(..., alias="channelIds")
    shared_cascades_count: int = Field(..., alias="sharedCascadesCount")
    typical_delay_seconds: int = Field(..., alias="typicalDelaySeconds")
    main_narrative: str = Field(..., alias="mainNarrative")


class AlertItemDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    severity: AlertSeverity
    status: AlertStatus
    triggered_at: str = Field(..., alias="triggeredAt")
    title: str
    summary: str
    narrative_tag: str = Field(..., alias="narrativeTag")
    target_route: str = Field(..., alias="targetRoute")
    parameter_version: str = Field(..., alias="parameterVersion")
