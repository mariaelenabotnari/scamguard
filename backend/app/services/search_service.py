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

        if not results:
            results = self._seed_message_hits(normalized_q, ranked_channels)

        return results

    def _default_explanation(self, channel_id: str) -> ScoreExplanationDto:
        _, _, expl = self._scoring_service.compute_channel_score(
            channel_id=channel_id,
            cluster_participation_share=40,
            copy_delay_factor=35,
            co_movement_repetition=30,
            narrative_weight=35,
            linked_clusters_count=1,
            co_moving_channels=["@moldova_puls_actual"],
            median_lead_lag_seconds=240,
            primary_narrative="General Political Commentary",
        )
        return expl

    def _seed_message_hits(
        self,
        normalized_q: str,
        ranked_channels: list[RankedChannelDto],
    ) -> list[SearchMessageHitDto]:
        ch1 = ranked_channels[0] if ranked_channels else None
        ch2 = ranked_channels[1] if len(ranked_channels) > 1 else ch1
        ch3 = ranked_channels[2] if len(ranked_channels) > 2 else ch1

        ch_radar_expl = (
            ch3.explanation if ch3 else self._default_explanation("ch-chisinau-radar")
        )

        seed_items = [
            SearchMessageHitDto(
                id="msg-501",
                channelId=ch1.id if ch1 else "ch-md-puls",
                handle=ch1.handle if ch1 else "@moldova_puls_actual",
                postedAt="2026-11-02 13:14:05",
                snippet=(
                    "URGENT: Tarifele la gaze si energie electrica vor fi dublate dupa 15 noiembrie"
                    " din cauza conditiilor impuse de Bruxelles pentru imprumutul extern."
                ),
                narrativeCategory=(
                    ch1.primary_narrative
                    if ch1
                    else "Sanctions, energy prices and economy fear"
                ),
                clusterId="CL-20261102-01",
                channelScore=ch1.score if ch1 else 90,
                riskBand=ch1.risk_band if ch1 else "high",
                explanation=ch1.explanation if ch1 else self._default_explanation("ch-md-puls"),
            ),
            SearchMessageHitDto(
                id="msg-502",
                channelId=ch2.id if ch2 else "ch-gagauz-live",
                handle=ch2.handle if ch2 else "@gagauzia_info_live",
                postedAt="2026-11-02 13:18:12",
                snippet=(
                    "ALERTA: Tarifele la gaze si energie electrica vor fi majorate cu 100% "
                    "din 15 noiembrie din cauza conditiilor impuse de Bruxelles!"
                ),
                narrativeCategory=(
                    ch2.primary_narrative
                    if ch2
                    else "Sanctions, energy prices and economy fear"
                ),
                clusterId="CL-20261102-01",
                channelScore=ch2.score if ch2 else 83,
                riskBand=ch2.risk_band if ch2 else "high",
                explanation=ch2.explanation if ch2 else self._default_explanation("ch-gagauz-live"),
            ),
            SearchMessageHitDto(
                id="msg-503",
                channelId=ch3.id if ch3 else "ch-chisinau-radar",
                handle=ch3.handle if ch3 else "@chisinau_radar24",
                postedAt="2026-11-02 11:40:10",
                snippet=(
                    "Сотни бюллетеней якобы уже подготовлены на зарубежных участках "
                    "до открытия голосования — источники сообщают о закрытом распоряжении ЦИК."
                ),
                narrativeCategory=(
                    ch3.primary_narrative
                    if ch3
                    else "Moldova government and elections delegitimisation"
                ),
                clusterId="CL-20261101-04",
                channelScore=ch3.score if ch3 else 61,
                riskBand=ch3.risk_band if ch3 else "medium",
                explanation=ch_radar_expl,
            ),
        ]

        if not normalized_q:
            return seed_items

        return [
            item
            for item in seed_items
            if normalized_q in item.snippet.lower()
            or normalized_q in item.handle.lower()
            or normalized_q in item.narrative_category.lower()
        ]
