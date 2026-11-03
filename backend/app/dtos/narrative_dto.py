"""DTOs for disinformation narrative classification, fake news scoring, and batch inference."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TargetType = Literal["message", "cluster"]


class NarrativeCategorySpecDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    prototype_claim: str = Field(..., alias="prototypeClaim")
    severity: str = Field(default="medium")
    sub_narratives: list[str] = Field(default_factory=list, alias="subNarratives")


class ClassifyItemInputDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    target_id: str = Field(..., alias="targetId")
    target_type: TargetType = Field(default="message", alias="targetType")
    text: str


class BatchClassifyInputDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[ClassifyItemInputDto]
    confidence_threshold: float = Field(default=0.55, alias="confidenceThreshold")


class NarrativePredictionDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    target_id: str = Field(..., alias="targetId")
    target_type: TargetType = Field(..., alias="targetType")
    category: str
    confidence: float
    matched_claim: str = Field(..., alias="matchedClaim")
    model_version: str = Field(..., alias="modelVersion")
    fake_news_score: float = Field(default=0.85, alias="fakeNewsScore")
    is_disinformation: bool = Field(default=True, alias="isDisinformation")
    sub_narrative: str | None = Field(default=None, alias="subNarrative")
