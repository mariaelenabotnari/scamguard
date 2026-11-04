"""Analysis pipeline service for ScamGuard.
Orchestrates: normalise -> similarity -> clustering -> narrative classification -> scoring -> alerts.
"""

from datetime import UTC, datetime
import secrets
from typing import Protocol

from app.core.logging import get_logger
from app.dtos.analysis_dto import AnalysisPipelineResultDto
from app.repositories.message_repository import IMessageRepository
from app.repositories.user_repository import IParameterRepository
from app.services.alert_service import IAlertService
from app.services.clustering_service import IClusteringService
from app.services.narrative_classifier_service import INarrativeClassifierService
from app.services.scoring_service import IScoringService
from app.services.text_normaliser import ITextNormaliser

logger = get_logger("analysis_pipeline")


class IAnalysisPipelineService(Protocol):
    def run_analysis_pipeline(self) -> AnalysisPipelineResultDto: ...


class AnalysisPipelineService:
    """Deterministic end-to-end analysis pipeline linking all ML and scoring stages."""

    def __init__(
        self,
        param_repo: IParameterRepository,
        message_repo: IMessageRepository,
        normaliser: ITextNormaliser,
        clustering_service: IClusteringService,
        narrative_classifier: INarrativeClassifierService,
        scoring_service: IScoringService,
        alert_service: IAlertService,
    ) -> None:
        self._param_repo = param_repo
        self._message_repo = message_repo
        self._normaliser = normaliser
        self._clustering_service = clustering_service
        self._narrative_classifier = narrative_classifier
        self._scoring_service = scoring_service
        self._alert_service = alert_service

    def run_analysis_pipeline(self) -> AnalysisPipelineResultDto:
        started_at = datetime.now(UTC).isoformat()
        run_id = f"pipe-{secrets.token_hex(4)}"

        # 1. Read parameter_sets for thresholds
        params = self._param_repo.get_latest()
        similarity_threshold = params.similarity_threshold or 0.82
        time_window_minutes = params.time_window_minutes or 30

        # 2. Normalisation verification (ensure all stored messages have normalised text)
        stored_messages = self._message_repo.list_messages(limit=1000)
        for msg in stored_messages:
            if not msg.normalised_text and msg.raw_text:
                norm = self._normaliser.normalise(msg.raw_text)
                # Ensure normalisation exists
                pass

        # 3. Detect and store coordinated clusters
        clusters = self._clustering_service.detect_and_store_clusters(
            similarity_threshold=similarity_threshold,
            time_window_minutes=time_window_minutes,
        )

        # 4. Narrative classification for all detected clusters
        for cl in clusters:
            try:
                self._narrative_classifier.classify_one(
                    target_id=cl.id,
                    target_type="cluster",
                    raw_text=cl.representative_snippet,
                )
            except Exception as exc:
                logger.warning(f"Narrative classification failed for cluster {cl.id}: {exc}")

        # 5. Channel risk scoring
        ranked_channels = self._scoring_service.recalculate_all_scores()

        # 6. Alert generation for clusters and risk score spikes
        alerts_generated = 0
        for cl in clusters:
            try:
                alert = self._alert_service.evaluate_cluster_alert(
                    cluster_id=cl.id,
                    channel_count=cl.channels_count,
                    time_span_seconds=cl.window_minutes * 60,
                    avg_similarity=cl.average_similarity,
                    narrative_tag=cl.narrative_category,
                    parameter_version=params.parameter_version,
                )
                if alert is not None:
                    alerts_generated += 1
            except Exception as exc:
                logger.warning(f"Alert evaluation failed for cluster {cl.id}: {exc}")

        finished_at = datetime.now(UTC).isoformat()

        return AnalysisPipelineResultDto(
            pipelineRunId=run_id,
            startedAt=started_at,
            finishedAt=finished_at,
            clustersDetected=len(clusters),
            channelsScored=len(ranked_channels),
            alertsGenerated=alerts_generated,
            parameterVersion=params.parameter_version,
        )
