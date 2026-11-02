"""DTOs for 10-category disinformation narrative classification and batch inference."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TargetType = Literal["message", "cluster"]


class NarrativeCategorySpecDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    prototype_claim: str = Field(..., alias="prototypeClaim")


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
