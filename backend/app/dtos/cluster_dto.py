"""DTOs for cross-channel similarity edges and coordinated message clusters."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MatchStage = Literal["exact_hash", "minhash_lsh", "semantic_embedding"]


class SimilarityEdgeDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    source_message_id: str = Field(..., alias="sourceMessageId")
    target_message_id: str = Field(..., alias="targetMessageId")
    source_channel_id: str = Field(..., alias="sourceChannelId")
    target_channel_id: str = Field(..., alias="targetChannelId")
    similarity_score: float = Field(..., alias="similarityScore")
    match_stage: MatchStage = Field(..., alias="matchStage")
    time_diff_seconds: int = Field(..., alias="timeDiffSeconds")
    parameter_version: str = Field(..., alias="parameterVersion")


class ClusterChannelAvatarDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    channel_id: str = Field(..., alias="channelId")
    handle: str
    title: str
    initials: str


class ClusterSummaryDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    headline_summary: str = Field(..., alias="headlineSummary")
    narrative_category: str = Field(..., alias="narrativeCategory")
    channels_count: int = Field(..., alias="channelsCount")
    messages_count: int = Field(..., alias="messagesCount")
    window_minutes: int = Field(..., alias="windowMinutes")
    average_similarity: float = Field(..., alias="averageSimilarity")
    first_posted_at: str = Field(..., alias="firstPostedAt")
    last_posted_at: str = Field(..., alias="lastPostedAt")
    representative_snippet: str = Field(..., alias="representativeSnippet")
    channels: list[ClusterChannelAvatarDto]
    parameter_version: str = Field(..., alias="parameterVersion")


class ClusterMessageComparisonDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message_id: str = Field(..., alias="messageId")
    channel_id: str = Field(..., alias="channelId")
    handle: str
    title: str
    posted_at: str = Field(..., alias="postedAt")
    delay_seconds: int = Field(..., alias="delaySeconds")
    similarity_score: float = Field(..., alias="similarityScore")
    is_deleted: bool = Field(default=False, alias="isDeleted")
    raw_text: str | None = Field(default=None, alias="rawText")
    normalised_text: str = Field(..., alias="normalisedText")
    normalised_hash: str = Field(..., alias="normalisedHash")
    telegram_url: str = Field(..., alias="telegramUrl")
    changed_phrases: list[str] = Field(default_factory=list, alias="changedPhrases")


class ClusterDetailDto(ClusterSummaryDto):
    messages: list[ClusterMessageComparisonDto]


class DetectClustersInputDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    similarity_threshold: float | None = Field(default=None, alias="similarityThreshold")
    time_window_minutes: int | None = Field(default=None, alias="timeWindowMinutes")
