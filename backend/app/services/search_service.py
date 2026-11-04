"""Unified search engine across channels, messages, and clusters with audit explanations."""

from typing import Protocol

from app.db.database import DatabaseManager
from app.dtos.scoring_dto import RankedChannelDto, ScoreExplanationDto
from app.dtos.search_dto import SearchMessageHitDto, UnifiedSearchResultsDto
from app.services.clustering_service import IClusteringService
from app.services.scoring_service import IScoringService


class ISearchService(Protocol):
    def search_all(self, query: str) -> UnifiedSearchResultsDto: ...


class SearchService(ISearchService):
    """Executes multi-entity search and attaches deterministic score explanations."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        scoring_service: IScoringService,
        clustering_service: IClusteringService,
    ) -> None:
        self._db = db_manager
        self._scoring_service = scoring_service
        self._clustering_service = clustering_service

    def search_all(self, query: str) -> UnifiedSearchResultsDto:
        normalized_q = query.strip().lower()

        # 1. Channels search
        all_channels = self._scoring_service.list_ranked_channels()
        if not normalized_q:
            matched_channels = all_channels
        else:
            matched_channels = [
                ch
                for ch in all_channels
                if normalized_q in ch.handle.lower()
                or normalized_q in ch.title.lower()
                or normalized_q in ch.primary_narrative.lower()
            ]

        # 2. Clusters search
        all_clusters = self._clustering_service.list_clusters()
        if not normalized_q:
            matched_clusters = all_clusters
        else:
            matched_clusters = [
                cl
                for cl in all_clusters
                if normalized_q in cl.headline_summary.lower()
                or normalized_q in cl.representative_snippet.lower()
                or normalized_q in cl.narrative_category.lower()
            ]

        # 3. Messages search
        matched_messages = self._search_messages(normalized_q, all_channels)

        return UnifiedSearchResultsDto(
            query=query.strip(),
            channels=matched_channels,
            messages=matched_messages,
            clusters=matched_clusters,
        )

    def _search_messages(
        self,
        normalized_q: str,
        ranked_channels: list[RankedChannelDto],
    ) -> list[SearchMessageHitDto]:
        channel_by_id = {ch.id: ch for ch in ranked_channels}
        channel_by_handle = {ch.handle.lower(): ch for ch in ranked_channels}

        conn = self._db.connection
        db_messages = conn.execute(
            """
            SELECT m.id, m.channel_id, m.posted_at, mt.raw_text, mn.normalised_text,
                   cm.cluster_id
            FROM messages m
            LEFT JOIN message_texts mt ON mt.message_id = m.id
            LEFT JOIN message_norm mn ON mn.message_id = m.id
            LEFT JOIN cluster_messages cm ON cm.message_id = m.id
            ORDER BY m.posted_at DESC
            LIMIT 100
            """
        ).fetchall()

        results: list[SearchMessageHitDto] = []

        if db_messages:
            for row in db_messages:
                raw_text = str(row["raw_text"] or "")
                norm_text = str(row["normalised_text"] or "")
                ch_id = str(row["channel_id"])
                ch_dto = channel_by_id.get(ch_id) or channel_by_handle.get(
                    f"@{ch_id.lower().lstrip('@')}"
                )

                text_to_match = f"{raw_text} {norm_text} {ch_id}".lower()
                if normalized_q and normalized_q not in text_to_match:
                    continue

                if ch_dto is not None:
                    score = ch_dto.score
                    band = ch_dto.risk_band
                    explanation = ch_dto.explanation
                    handle = ch_dto.handle
                    narrative = ch_dto.primary_narrative
                else:
                    score = 45
                    band = "medium"
                    explanation = self._default_explanation(ch_id)
                    handle = f"@{ch_id}"
                    narrative = "General Political Commentary"

                snippet = raw_text[:240] if raw_text else norm_text[:240]
                cluster_id = str(row["cluster_id"]) if row["cluster_id"] else None

                results.append(
                    SearchMessageHitDto(
                        id=str(row["id"]),
                        channelId=ch_id,
                        handle=handle,
                        postedAt=str(row["posted_at"]),
                        snippet=snippet,
                        narrativeCategory=narrative,
                        clusterId=cluster_id,
                        channelScore=score,
                        riskBand=band,
                        explanation=explanation,
                    )
                )

        return results

    def _default_explanation(self, channel_id: str) -> ScoreExplanationDto:
        _, _, expl = self._scoring_service.compute_channel_score(
            channel_id=channel_id,
            cluster_participation_share=0,
            copy_delay_factor=0,
            co_movement_repetition=0,
            narrative_weight=0,
            linked_clusters_count=0,
            co_moving_channels=[],
            median_lead_lag_seconds=0,
            primary_narrative="None detected",
        )
        return expl
