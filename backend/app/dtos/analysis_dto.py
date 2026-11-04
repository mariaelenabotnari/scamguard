"""DTOs for end-to-end analysis pipeline execution."""

from pydantic import BaseModel, ConfigDict, Field


class AnalysisPipelineResultDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pipeline_run_id: str = Field(..., alias="pipelineRunId")
    started_at: str = Field(..., alias="startedAt")
    finished_at: str = Field(..., alias="finishedAt")
    clusters_detected: int = Field(..., alias="clustersDetected")
    channels_scored: int = Field(..., alias="channelsScored")
    alerts_generated: int = Field(..., alias="alertsGenerated")
    parameter_version: str = Field(..., alias="parameterVersion")
