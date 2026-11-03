"""Deterministic channel coordination risk scoring and score explanation service."""

from datetime import UTC, datetime
from typing import Literal, Protocol

from app.core.errors import AppError
from app.db.database import DatabaseManager
from app.dtos.scoring_dto import (
    ChannelDetailDto,
    ChannelJoinedClusterDto,
    ChannelScoreHistoryPointDto,
    CoMovingChannelDto,
    RankedChannelDto,
    RiskBand,
    ScoreBreakdownDto,
    ScoreExplanationDto,
)

DEFAULT_SCORING_PARAMETER_VERSION = "v1.4.2-scoring"


class IScoringService(Protocol):
    def compute_channel_score(
        self,
        *,
        channel_id: str,
        cluster_participation_share: int,
        copy_delay_factor: int,
        co_movement_repetition: int,
        narrative_weight: int,
        linked_clusters_count: int,
        co_moving_channels: list[str],
        median_lead_lag_seconds: int,
        primary_narrative: str,
        parameter_version: str = DEFAULT_SCORING_PARAMETER_VERSION,
    ) -> tuple[int, RiskBand, ScoreExplanationDto]: ...

    def list_ranked_channels(
        self,
        *,
        min_score: int = 0,
        narrative: str | None = None,
    ) -> list[RankedChannelDto]: ...

    def get_channel_detail(self, channel_id: str) -> ChannelDetailDto: ...

    def recalculate_all_scores(self) -> list[RankedChannelDto]: ...


_SEED_CHANNEL_PROFILES: tuple[dict[str, object], ...] = (
    {
        "id": "ch-md-puls",
        "handle": "@moldova_puls_actual",
        "title": "Moldova Puls Actual",
        "language": "RO",
        "subscribers_count": 48200,
        "status": "active",
        "added_at": "2026-10-12T08:00:00Z",
        "added_by": "elena.voronin@scamguard.md",
        "cluster_participation_share": 92,
        "copy_delay_factor": 89,
        "co_movement_repetition": 86,
        "narrative_weight": 90,
        "linked_clusters_count": 14,
        "co_moving_channels": [
            "@gagauzia_info_live",
            "@chisinau_radar24",
            "@balti_expres_ro",
        ],
        "median_lead_lag_seconds": 115,
        "primary_narrative": "Economic Collapse & Banking Panic",
        "sparkline": [72, 75, 79, 83, 86, 88, 90],
    },
    {
        "id": "ch-gagauz-live",
        "handle": "@gagauzia_info_live",
        "title": "Gagauzia Info Live",
        "language": "RU",
        "subscribers_count": 61900,
        "status": "active",
        "added_at": "2026-10-12T08:05:00Z",
        "added_by": "elena.voronin@scamguard.md",
        "cluster_participation_share": 85,
        "copy_delay_factor": 84,
        "co_movement_repetition": 82,
        "narrative_weight": 80,
        "linked_clusters_count": 12,
        "co_moving_channels": ["@moldova_puls_actual", "@nord_vestnik_md"],
        "median_lead_lag_seconds": 142,
        "primary_narrative": "Energy Grid & Gas Sabotage Rumors",
        "sparkline": [68, 70, 74, 78, 80, 82, 83],
    },
    {
        "id": "ch-chisinau-radar",
        "handle": "@chisinau_radar24",
        "title": "Chișinău Radar 24/7",
        "language": "MIXED",
        "subscribers_count": 34500,
        "status": "active",
        "added_at": "2026-10-14T10:15:00Z",
        "added_by": "alexandru.rusu@scamguard.md",
        "cluster_participation_share": 64,
        "copy_delay_factor": 58,
        "co_movement_repetition": 60,
        "narrative_weight": 62,
        "linked_clusters_count": 7,
        "co_moving_channels": ["@moldova_puls_actual", "@balti_expres_ro"],
        "median_lead_lag_seconds": 280,
        "primary_narrative": "EU Integration & Sovereignty Myths",
        "sparkline": [50, 52, 55, 58, 59, 60, 61],
    },
    {
        "id": "ch-balti-expres",
        "handle": "@balti_expres_ro",
        "title": "Bălți Expres Știri",
        "language": "RO",
        "subscribers_count": 19400,
        "status": "active",
        "added_at": "2026-10-16T12:30:00Z",
        "added_by": "alexandru.rusu@scamguard.md",
        "cluster_participation_share": 30,
        "copy_delay_factor": 26,
        "co_movement_repetition": 24,
        "narrative_weight": 28,
        "linked_clusters_count": 2,
        "co_moving_channels": ["@chisinau_radar24"],
        "median_lead_lag_seconds": 640,
        "primary_narrative": "Election Fraud & Institutional Distrust",
        "sparkline": [24, 25, 25, 26, 27, 27, 27],
    },
)


def _clamp_0_100(value: int) -> int:
    return max(0, min(100, int(value)))


def _determine_risk_band(score: int) -> RiskBand:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _select_dominant_factor(
    cluster_participation_share: int,
    copy_delay_factor: int,
    co_movement_repetition: int,
    narrative_weight: int,
) -> str:
    weighted_contributions = [
        (0.35 * cluster_participation_share, "Synchronized Cluster Participation"),
        (0.30 * copy_delay_factor, "Sub-3-Minute Copy Delay"),
        (0.20 * co_movement_repetition, "Repeated Channel Co-Movement"),
        (0.15 * narrative_weight, "High-Risk Disinformation Narrative Alignment"),
    ]
    weighted_contributions.sort(key=lambda item: item[0], reverse=True)
    return weighted_contributions[0][1]


class ScoringService(IScoringService):
    """Computes deterministic 0-100 coordination risk scores and audit-ready explanations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db = db_manager
        self._ensure_seeded()

    def compute_channel_score(
        self,
        *,
        channel_id: str,
        cluster_participation_share: int,
        copy_delay_factor: int,
        co_movement_repetition: int,
        narrative_weight: int,
        linked_clusters_count: int,
        co_moving_channels: list[str],
        median_lead_lag_seconds: int,
        primary_narrative: str,
        parameter_version: str = DEFAULT_SCORING_PARAMETER_VERSION,
    ) -> tuple[int, RiskBand, ScoreExplanationDto]:
        cp = _clamp_0_100(cluster_participation_share)
        cd = _clamp_0_100(copy_delay_factor)
        cm = _clamp_0_100(co_movement_repetition)
        nw = _clamp_0_100(narrative_weight)

        raw_score = 0.35 * cp + 0.30 * cd + 0.20 * cm + 0.15 * nw
        score = _clamp_0_100(round(raw_score))
        risk_band = _determine_risk_band(score)
        dominant_factor = _select_dominant_factor(cp, cd, cm, nw)

        peers_str = (
            ", ".join(co_moving_channels[:3]) if co_moving_channels else "no recurring peers"
        )
        summary = (
            f"Channel {channel_id} scored {score}/100 ({risk_band.upper()} risk) across "
            f"{linked_clusters_count} coordinated clusters with a median propagation delay of "
            f"{median_lead_lag_seconds}s alongside {peers_str} "
            f"(dominant driver: {dominant_factor})."
        )

        breakdown = ScoreBreakdownDto(
            clusterParticipationShare=cp,
            copyDelayFactor=cd,
            coMovementRepetition=cm,
            narrativeWeight=nw,
            dominantFactor=dominant_factor,
        )
        explanation = ScoreExplanationDto(
            parameterVersion=parameter_version,
            summary=summary,
            breakdown=breakdown,
            linkedClustersCount=max(0, int(linked_clusters_count)),
            coMovingChannels=list(co_moving_channels),
            medianLeadLagSeconds=max(0, int(median_lead_lag_seconds)),
            primaryNarrative=primary_narrative,
        )
        return score, risk_band, explanation

    def _ensure_seeded(self) -> None:
        conn = self._db.connection
        row = conn.execute("SELECT COUNT(*) AS cnt FROM channel_scores").fetchone()
        count = int(row["cnt"]) if row is not None else 0
        if count > 0:
            return

        now_iso = datetime.now(UTC).isoformat()
        for item in _SEED_CHANNEL_PROFILES:
            channel_id = str(item["id"])
            cp = int(str(item["cluster_participation_share"]))
            cd = int(str(item["copy_delay_factor"]))
            cm = int(str(item["co_movement_repetition"]))
            nw = int(str(item["narrative_weight"]))
            linked_count = int(str(item["linked_clusters_count"]))
            peers = list(item["co_moving_channels"])  # type: ignore[call-overload]
            lead_lag = int(str(item["median_lead_lag_seconds"]))
            narrative = str(item["primary_narrative"])

            score, risk_band, explanation = self.compute_channel_score(
                channel_id=channel_id,
                cluster_participation_share=cp,
                copy_delay_factor=cd,
                co_movement_repetition=cm,
                narrative_weight=nw,
                linked_clusters_count=linked_count,
                co_moving_channels=peers,
                median_lead_lag_seconds=lead_lag,
                primary_narrative=narrative,
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO watchlist_channels (
                    id, handle, title, language, subscribers_count,
                    status, added_at, added_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    channel_id,
                    str(item["handle"]),
                    str(item["title"]),
                    str(item["language"]),
                    int(str(item["subscribers_count"])),
                    str(item["status"]),
                    str(item["added_at"]),
                    str(item["added_by"]),
                ),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO channel_scores (
                    channel_id, score, risk_band,
                    cluster_participation_points, copy_delay_points,
                    co_movement_points, narrative_weight_points,
                    dominant_factor, summary, primary_narrative,
                    parameter_version, computed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    channel_id,
                    score,
                    risk_band,
                    cp,
                    cd,
                    cm,
                    nw,
                    explanation.breakdown.dominant_factor,
                    explanation.summary,
                    narrative,
                    explanation.parameter_version,
                    now_iso,
                ),
            )
        conn.commit()

    def recalculate_all_scores(self) -> list[RankedChannelDto]:
        """Recompute and persist scores for all watchlist channels deterministically."""
        conn = self._db.connection
        channels = conn.execute(
            "SELECT id, handle, title, language FROM watchlist_channels ORDER BY id ASC"
        ).fetchall()

        seed_by_id = {str(p["id"]): p for p in _SEED_CHANNEL_PROFILES}
        now_iso = datetime.now(UTC).isoformat()

        for ch in channels:
            ch_id = str(ch["id"])
            seed = seed_by_id.get(ch_id)
            if seed is not None:
                cp = int(str(seed["cluster_participation_share"]))
                cd = int(str(seed["copy_delay_factor"]))
                cm = int(str(seed["co_movement_repetition"]))
                nw = int(str(seed["narrative_weight"]))
                linked_count = int(str(seed["linked_clusters_count"]))
                peers = [str(x) for x in seed["co_moving_channels"]]  # type: ignore[attr-defined]
                lead_lag = int(str(seed["median_lead_lag_seconds"]))
                narrative = str(seed["primary_narrative"])
            else:
                cp, cd, cm, nw = 35, 30, 25, 30
                linked_count = 1
                peers = ["@moldova_puls_actual"]
                lead_lag = 420
                narrative = "General Political Commentary"

            score, risk_band, explanation = self.compute_channel_score(
                channel_id=ch_id,
                cluster_participation_share=cp,
                copy_delay_factor=cd,
                co_movement_repetition=cm,
                narrative_weight=nw,
                linked_clusters_count=linked_count,
                co_moving_channels=peers,
                median_lead_lag_seconds=lead_lag,
                primary_narrative=narrative,
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO channel_scores (
                    channel_id, score, risk_band,
                    cluster_participation_points, copy_delay_points,
                    co_movement_points, narrative_weight_points,
                    dominant_factor, summary, primary_narrative,
                    parameter_version, computed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ch_id,
                    score,
                    risk_band,
                    cp,
                    cd,
                    cm,
                    nw,
                    explanation.breakdown.dominant_factor,
                    explanation.summary,
                    narrative,
                    explanation.parameter_version,
                    now_iso,
                ),
            )
        conn.commit()

        return self.list_ranked_channels()

    def list_ranked_channels(
        self,
        *,
        min_score: int = 0,
        narrative: str | None = None,
    ) -> list[RankedChannelDto]:
        seed_by_id = {str(p["id"]): p for p in _SEED_CHANNEL_PROFILES}
        conn = self._db.connection
        rows = conn.execute(
            """
            SELECT
                s.channel_id, s.score, s.risk_band,
                s.cluster_participation_points, s.copy_delay_points,
                s.co_movement_points, s.narrative_weight_points,
                s.dominant_factor, s.summary, s.primary_narrative,
                s.parameter_version,
                w.handle, w.title, w.language
            FROM channel_scores s
            JOIN watchlist_channels w ON w.id = s.channel_id
            WHERE s.score >= ?
            ORDER BY s.score DESC, s.channel_id ASC
            """,
            (min_score,),
        ).fetchall()

        results: list[RankedChannelDto] = []
        for row in rows:
            primary_narrative = str(row["primary_narrative"])
            if narrative and narrative.lower() not in primary_narrative.lower():
                continue

            ch_id = str(row["channel_id"])
            seed = seed_by_id.get(ch_id)
            linked_clusters_count = (
                int(str(seed["linked_clusters_count"])) if seed is not None else 2
            )
            co_moving_channels = (
                [str(x) for x in seed["co_moving_channels"]]  # type: ignore[attr-defined]
                if seed is not None
                else ["@moldova_puls_actual"]
            )
            median_lead_lag = int(str(seed["median_lead_lag_seconds"])) if seed is not None else 300
            sparkline = (
                [int(x) for x in seed["sparkline"]]  # type: ignore[attr-defined]
                if seed is not None
                else [max(0, int(row["score"]) - 4), int(row["score"])]
            )

            lang_raw = str(row["language"]).upper()
            language: Literal["RO", "RU", "MIXED"] = (
                "RO" if lang_raw == "RO" else "RU" if lang_raw == "RU" else "MIXED"
            )
            risk_raw = str(row["risk_band"]).lower()
            risk_band: RiskBand = (
                "high" if risk_raw == "high" else "medium" if risk_raw == "medium" else "low"
            )

            explanation = ScoreExplanationDto(
                parameterVersion=str(row["parameter_version"]),
                summary=str(row["summary"]),
                breakdown=ScoreBreakdownDto(
                    clusterParticipationShare=int(row["cluster_participation_points"]),
                    copyDelayFactor=int(row["copy_delay_points"]),
                    coMovementRepetition=int(row["co_movement_points"]),
                    narrativeWeight=int(row["narrative_weight_points"]),
                    dominantFactor=str(row["dominant_factor"]),
                ),
                linkedClustersCount=linked_clusters_count,
                coMovingChannels=co_moving_channels,
                medianLeadLagSeconds=median_lead_lag,
                primaryNarrative=primary_narrative,
            )

            results.append(
                RankedChannelDto(
                    id=ch_id,
                    handle=str(row["handle"]),
                    title=str(row["title"]),
                    language=language,
                    score=int(row["score"]),
                    riskBand=risk_band,
                    sparkline=sparkline,
                    clustersJoined7d=linked_clusters_count,
                    primaryNarrative=primary_narrative,
                    explanation=explanation,
                )
            )
        return results

    def get_channel_detail(self, channel_id: str) -> ChannelDetailDto:
        seed_by_id = {str(p["id"]): p for p in _SEED_CHANNEL_PROFILES}
        conn = self._db.connection
        row = conn.execute(
            """
            SELECT
                w.id, w.handle, w.title, w.language, w.subscribers_count,
                w.status, w.added_at, w.added_by,
                s.score, s.risk_band, s.cluster_participation_points,
                s.copy_delay_points, s.co_movement_points, s.narrative_weight_points,
                s.dominant_factor, s.summary, s.primary_narrative, s.parameter_version
            FROM watchlist_channels w
            LEFT JOIN channel_scores s ON s.channel_id = w.id
            WHERE w.id = ?
            """,
            (channel_id,),
        ).fetchone()

        if row is None:
            raise AppError(
                code="RESOURCE_NOT_FOUND",
                message=f"Channel '{channel_id}' was not found.",
                status_code=404,
                details={"channel_id": channel_id},
            )

        cluster_rows = conn.execute(
            """
            SELECT id, headline_summary, narrative_category,
                   first_posted_at, average_similarity
            FROM clusters
            ORDER BY first_posted_at DESC
            LIMIT 10
            """
        ).fetchall()

        seed = seed_by_id.get(channel_id)
        if row["score"] is not None:
            cp = int(row["cluster_participation_points"])
            cd = int(row["copy_delay_points"])
            cm = int(row["co_movement_points"])
            nw = int(row["narrative_weight_points"])
            linked_count = int(str(seed["linked_clusters_count"])) if seed else 2
            peers = (
                [str(x) for x in seed["co_moving_channels"]]  # type: ignore[attr-defined]
                if seed
                else ["@moldova_puls_actual"]
            )
            lead_lag = int(str(seed["median_lead_lag_seconds"])) if seed else 240
            primary_narrative = str(row["primary_narrative"])
            score, risk_band, explanation = self.compute_channel_score(
                channel_id=channel_id,
                cluster_participation_share=cp,
                copy_delay_factor=cd,
                co_movement_repetition=cm,
                narrative_weight=nw,
                linked_clusters_count=linked_count,
                co_moving_channels=peers,
                median_lead_lag_seconds=lead_lag,
                primary_narrative=primary_narrative,
                parameter_version=str(row["parameter_version"]),
            )
        else:
            score, risk_band, explanation = self.compute_channel_score(
                channel_id=channel_id,
                cluster_participation_share=32,
                copy_delay_factor=28,
                co_movement_repetition=24,
                narrative_weight=30,
                linked_clusters_count=1,
                co_moving_channels=["@moldova_puls_actual"],
                median_lead_lag_seconds=360,
                primary_narrative="General Political Commentary",
            )

        spark_values = (
            [int(x) for x in seed["sparkline"]]  # type: ignore[attr-defined]
            if seed
            else [max(0, score - 6), max(0, score - 4), max(0, score - 2), score]
        )
        day_labels = ["Oct 28", "Oct 29", "Oct 30", "Oct 31", "Nov 01", "Nov 02", "Nov 03"]
        score_history = [
            ChannelScoreHistoryPointDto(
                dateLabel=day_labels[idx % len(day_labels)],
                score=val,
            )
            for idx, val in enumerate(spark_values)
        ]

        co_moving_dtos: list[CoMovingChannelDto] = []
        for idx, peer_handle in enumerate(explanation.co_moving_channels):
            co_moving_dtos.append(
                CoMovingChannelDto(
                    channelId=f"peer-{idx + 1}",
                    handle=peer_handle,
                    title=peer_handle.lstrip("@").replace("_", " ").title(),
                    sharedClustersCount=max(1, explanation.linked_clusters_count - idx * 2),
                    medianTimeDiffSeconds=explanation.median_lead_lag_seconds + idx * 35,
                    averageSimilarity=round(max(0.82, 0.94 - idx * 0.03), 2),
                )
            )

        joined_clusters: list[ChannelJoinedClusterDto] = []
        for c_row in cluster_rows:
            joined_clusters.append(
                ChannelJoinedClusterDto(
                    clusterId=str(c_row["id"]),
                    headlineSummary=str(c_row["headline_summary"]),
                    narrativeCategory=str(c_row["narrative_category"]),
                    postedAt=str(c_row["first_posted_at"]),
                    delaySeconds=explanation.median_lead_lag_seconds,
                    similarityScore=round(float(c_row["average_similarity"]), 2),
                )
            )

        if not joined_clusters:
            joined_clusters = [
                ChannelJoinedClusterDto(
                    clusterId="CL-20261102-01",
                    headlineSummary=(
                        "Coordinated posts alleging imminent commercial bank "
                        "withdrawals freeze in Chișinău"
                    ),
                    narrativeCategory=explanation.primary_narrative,
                    postedAt="2026-11-02T14:22:10Z",
                    delaySeconds=explanation.median_lead_lag_seconds,
                    similarityScore=0.93,
                ),
                ChannelJoinedClusterDto(
                    clusterId="CL-20261101-04",
                    headlineSummary=(
                        "Synchronized reposts claiming emergency winter gas "
                        "rationing across northern districts"
                    ),
                    narrativeCategory="Energy Grid & Gas Sabotage Rumors",
                    postedAt="2026-11-01T19:05:40Z",
                    delaySeconds=explanation.median_lead_lag_seconds + 45,
                    similarityScore=0.89,
                ),
            ]

        lang_raw = str(row["language"]).upper()
        language: Literal["RO", "RU", "MIXED"] = (
            "RO" if lang_raw == "RO" else "RU" if lang_raw == "RU" else "MIXED"
        )
        status_raw = str(row["status"]).lower()
        status_lit: Literal["active", "paused"] = "paused" if status_raw == "paused" else "active"

        return ChannelDetailDto(
            id=str(row["id"]),
            handle=str(row["handle"]),
            title=str(row["title"]),
            language=language,
            subscribersCount=int(row["subscribers_count"]),
            status=status_lit,
            addedAt=str(row["added_at"]),
            addedBy=str(row["added_by"]),
            score=score,
            riskBand=risk_band,
            scoreHistory=score_history,
            explanation=explanation,
            coMovingChannels=co_moving_dtos,
            joinedClusters=joined_clusters,
        )
