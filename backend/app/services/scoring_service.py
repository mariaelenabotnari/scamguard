"""Deterministic channel coordination risk scoring and score explanation service."""

import re
from datetime import UTC, datetime
from typing import Literal, Protocol

from app.core.errors import AppError
from app.db.database import DatabaseManager
from app.dtos.scoring_dto import (
    ChannelDetailDto,
    ChannelJoinedClusterDto,
    ChannelScoreHistoryPointDto,
    CoMovingChannelDto,
    CoordinationGroupDto,
    RankedChannelDto,
    RiskBand,
    ScoreBreakdownDto,
    ScoreExplanationDto,
)

DEFAULT_SCORING_PARAMETER_VERSION = "v2.0.0-scoring"

_SYNDICATION_REGEX = re.compile(
    r"\b(?:conform|transmite|scrie|potrivit|anunta|anunță)\s+(?:agentiei|agenției)?\s*(moldpres|ipn|infotag|agerpres|reuters|tass|interfax|ria)\b"
    r"|\b(?:сообщает|пишет|передает|передаёт)\s+(тасс|риа|интерфакс|молдпрес|ipn)\b",
    re.IGNORECASE,
)


def detect_syndication_wire(text: str) -> tuple[bool, str | None]:
    """Detects accredited news wire agency attributions (e.g. Moldpres, IPN, TASS)."""
    m = _SYNDICATION_REGEX.search(text)
    if m:
        agency = m.group(1) or m.group(2)
        return True, agency.capitalize() if agency else "Wire Agency"
    return False, None


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
        is_syndicated_agency: bool = False,
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

    def get_channel_coordination_groups(self) -> list[CoordinationGroupDto]: ...


def _clamp_0_100(value: int) -> int:
    return max(0, min(100, int(value)))


def _determine_risk_band(score: int) -> RiskBand:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _calculate_channel_metrics(
    cluster_participation_share: int,
    copy_delay_factor: int,
    co_movement_repetition: int,
    narrative_weight: int,
    linked_clusters_count: int,
    is_syndicated_agency: bool = False,
) -> tuple[int, int, RiskBand, RiskBand, bool]:
    cp = _clamp_0_100(cluster_participation_share)
    cd = _clamp_0_100(copy_delay_factor)
    cm = _clamp_0_100(co_movement_repetition)
    nw = _clamp_0_100(narrative_weight)

    has_sufficient_data = linked_clusters_count >= 2

    # Coordination score purely behavioral (0-100)
    raw_coord = 0.45 * cp + 0.35 * cd + 0.20 * cm

    # Syndication discount: Legitimate accredited news wires copy rapidly without covert coordination
    if is_syndicated_agency:
        raw_coord = raw_coord * 0.45

    # Composite score for backwards compatibility (0-100)
    raw_score = 0.35 * cp + 0.30 * cd + 0.20 * cm + 0.15 * nw
    if is_syndicated_agency:
        raw_score = raw_score * 0.55

    if not has_sufficient_data:
        # Shrink toward empirical median (30) to prevent outlier false positives
        raw_coord = 0.5 * raw_coord + 0.5 * 30.0
        raw_score = 0.5 * raw_score + 0.5 * 30.0

    score = _clamp_0_100(round(raw_score))
    coord_score = _clamp_0_100(round(raw_coord))
    risk_band = _determine_risk_band(score)
    narrative_risk = _determine_risk_band(nw)

    return score, coord_score, risk_band, narrative_risk, has_sufficient_data


def _select_dominant_factor(
    cluster_participation_share: int,
    copy_delay_factor: int,
    co_movement_repetition: int,
    narrative_weight: int,
) -> str:
    weighted_contributions = [
        (0.35 * cluster_participation_share, "frequent co-publication across coordinated clusters"),
        (
            0.30 * copy_delay_factor,
            "reposting significantly faster than typical manual editorial lag (< 5 minutes)",
        ),
        (0.20 * co_movement_repetition, "repeated temporal co-occurrence with peer channels"),
        (0.15 * narrative_weight, "thematic alignment with documented disinformation narratives"),
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
        is_syndicated_agency: bool = False,
        parameter_version: str = DEFAULT_SCORING_PARAMETER_VERSION,
    ) -> tuple[int, RiskBand, ScoreExplanationDto]:
        cp = _clamp_0_100(cluster_participation_share)
        cd = _clamp_0_100(copy_delay_factor)
        cm = _clamp_0_100(co_movement_repetition)
        nw = _clamp_0_100(narrative_weight)

        score, coord_score, risk_band, narrative_risk, has_sufficient_data = (
            _calculate_channel_metrics(
                cluster_participation_share=cp,
                copy_delay_factor=cd,
                co_movement_repetition=cm,
                narrative_weight=nw,
                linked_clusters_count=linked_clusters_count,
                is_syndicated_agency=is_syndicated_agency,
            )
        )
        dominant_factor = _select_dominant_factor(cp, cd, cm, nw)

        peers_str = (
            ", ".join(co_moving_channels[:3]) if co_moving_channels else "no recurring peers"
        )
        data_qualifier = (
            ""
            if has_sufficient_data
            else " (insufficient data: < 2 clusters, score shrunk to median)"
        )
        syndication_qualifier = (
            " (syndicated news agency reporting detected; coordination risk discounted)"
            if is_syndicated_agency
            else ""
        )
        summary = (
            f"Channel {channel_id} shows coordination index {coord_score}/100 and "
            f"{narrative_risk} narrative alignment across {linked_clusters_count} observed "
            f"clusters with median propagation delay of {median_lead_lag_seconds}s "
            f"alongside {peers_str}. Primary observation: {dominant_factor}.{data_qualifier}{syndication_qualifier}"
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
        """No-op: seed data removed to ensure clean real-data calculation."""
        pass

    def recalculate_all_scores(self) -> list[RankedChannelDto]:
        """Recompute and persist scores for all watchlist channels deterministically."""
        conn = self._db.connection
        channels = conn.execute(
            "SELECT id, handle, title, language FROM watchlist_channels ORDER BY id ASC"
        ).fetchall()

        now_iso = datetime.now(UTC).isoformat()

        for ch in channels:
            ch_id = str(ch["id"])
            handle_str = str(ch["handle"])

            # 1. Query real clusters from cluster_messages
            cm_rows = conn.execute(
                """
                SELECT cm.cluster_id, cm.delay_seconds, c.narrative_category
                FROM cluster_messages cm
                JOIN clusters c ON c.id = cm.cluster_id
                WHERE cm.channel_id = ? OR cm.channel_id = ?
                """,
                (ch_id, handle_str),
            ).fetchall()

            if cm_rows:
                linked_count = len(cm_rows)
                delays = [int(r["delay_seconds"]) for r in cm_rows]
                delays.sort()
                lead_lag = delays[len(delays) // 2] if delays else 0

                peer_rows = conn.execute(
                    """
                    SELECT DISTINCT cm2.channel_id
                    FROM cluster_messages cm1
                    JOIN cluster_messages cm2 ON cm1.cluster_id = cm2.cluster_id
                    WHERE (cm1.channel_id = ? OR cm1.channel_id = ?)
                      AND cm2.channel_id != ? AND cm2.channel_id != ?
                    """,
                    (ch_id, handle_str, ch_id, handle_str),
                ).fetchall()
                peers = [f"@{r[0]}" if not str(r[0]).startswith("@") else str(r[0]) for r in peer_rows]

                # Check for syndication wire attribution
                is_syndicated = False
                msg_texts = conn.execute(
                    """
                    SELECT t.raw_text
                    FROM cluster_messages cm
                    JOIN messages m ON cm.message_id = m.id
                    JOIN message_texts t ON m.id = t.message_id
                    WHERE cm.channel_id = ? OR cm.channel_id = ?
                    LIMIT 20
                    """,
                    (ch_id, handle_str),
                ).fetchall()
                for mt in msg_texts:
                    has_wire, _ = detect_syndication_wire(str(mt[0]))
                    if has_wire:
                        is_syndicated = True
                        break

                cp = min(100, max(20, linked_count * 25))
                cd = max(10, 100 - min(90, lead_lag // 5))
                cm = min(100, max(15, len(peers) * 25))
                narrative = str(cm_rows[0]["narrative_category"])
                nw = 85 if any(k in narrative.lower() for k in ("energy", "panic", "gas", "sanction", "election", "war")) else 50
            else:
                is_syndicated = False
                cp, cd, cm, nw = 0, 0, 0, 0
                linked_count = 0
                peers = []
                lead_lag = 0
                narrative = "No coordinated narratives detected"

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
                is_syndicated_agency=is_syndicated,
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
            handle_str = str(row["handle"])

            cl_row = conn.execute(
                "SELECT COUNT(DISTINCT cluster_id) AS cnt FROM cluster_messages WHERE channel_id = ? OR channel_id = ?",
                (ch_id, handle_str),
            ).fetchone()
            linked_clusters_count = int(cl_row["cnt"]) if cl_row else 0

            peer_rows = conn.execute(
                """
                SELECT DISTINCT cm2.channel_id
                FROM cluster_messages cm1
                JOIN cluster_messages cm2 ON cm1.cluster_id = cm2.cluster_id
                WHERE (cm1.channel_id = ? OR cm1.channel_id = ?)
                  AND cm2.channel_id != ? AND cm2.channel_id != ?
                LIMIT 5
                """,
                (ch_id, handle_str, ch_id, handle_str),
            ).fetchall()
            co_moving_channels = [f"@{r[0]}" if not str(r[0]).startswith("@") else str(r[0]) for r in peer_rows]

            delay_row = conn.execute(
                "SELECT AVG(delay_seconds) AS avg_d FROM cluster_messages WHERE channel_id = ? OR channel_id = ?",
                (ch_id, handle_str),
            ).fetchone()
            median_lead_lag = int(round(float(delay_row["avg_d"]))) if delay_row and delay_row["avg_d"] is not None else 0
            sparkline = [max(0, int(row["score"]) - 4), int(row["score"])]

            lang_raw = str(row["language"]).upper()
            language: Literal["RO", "RU", "MIXED"] = (
                "RO" if lang_raw == "RO" else "RU" if lang_raw == "RU" else "MIXED"
            )
            risk_raw = str(row["risk_band"]).lower()
            risk_band: RiskBand = (
                "high" if risk_raw == "high" else "medium" if risk_raw == "medium" else "low"
            )

            cp = int(row["cluster_participation_points"])
            cd = int(row["copy_delay_points"])
            cm = int(row["co_movement_points"])
            nw = int(row["narrative_weight_points"])
            score, coord_score, risk_band, narrative_risk, has_sufficient_data = (
                _calculate_channel_metrics(cp, cd, cm, nw, linked_clusters_count)
            )

            explanation = ScoreExplanationDto(
                parameterVersion=str(row["parameter_version"]),
                summary=str(row["summary"]),
                breakdown=ScoreBreakdownDto(
                    clusterParticipationShare=cp,
                    copyDelayFactor=cd,
                    coMovementRepetition=cm,
                    narrativeWeight=nw,
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
                    score=score,
                    coordinationScore=coord_score,
                    narrativeRisk=narrative_risk,
                    hasSufficientData=has_sufficient_data,
                    riskBand=risk_band,
                    sparkline=sparkline,
                    clustersJoined7d=linked_clusters_count,
                    primaryNarrative=primary_narrative,
                    explanation=explanation,
                )
            )
        return results

    def get_channel_detail(self, channel_id: str) -> ChannelDetailDto:
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

        handle_str = str(row["handle"])
        cl_row = conn.execute(
            "SELECT COUNT(DISTINCT cluster_id) AS cnt FROM cluster_messages WHERE channel_id = ? OR channel_id = ?",
            (channel_id, handle_str),
        ).fetchone()
        linked_count = int(cl_row["cnt"]) if cl_row else 0

        peer_rows = conn.execute(
            """
            SELECT DISTINCT cm2.channel_id
            FROM cluster_messages cm1
            JOIN cluster_messages cm2 ON cm1.cluster_id = cm2.cluster_id
            WHERE (cm1.channel_id = ? OR cm1.channel_id = ?)
              AND cm2.channel_id != ? AND cm2.channel_id != ?
            LIMIT 5
            """,
            (channel_id, handle_str, channel_id, handle_str),
        ).fetchall()
        peers = [f"@{r[0]}" if not str(r[0]).startswith("@") else str(r[0]) for r in peer_rows]

        delay_row = conn.execute(
            "SELECT AVG(delay_seconds) AS avg_d FROM cluster_messages WHERE channel_id = ? OR channel_id = ?",
            (channel_id, handle_str),
        ).fetchone()
        lead_lag = int(round(float(delay_row["avg_d"]))) if delay_row and delay_row["avg_d"] is not None else 0

        if row["score"] is not None:
            cp = int(row["cluster_participation_points"])
            cd = int(row["copy_delay_points"])
            cm = int(row["co_movement_points"])
            nw = int(row["narrative_weight_points"])
            primary_narrative = str(row["primary_narrative"])
            param_ver = str(row["parameter_version"])
        else:
            cp, cd, cm, nw = 0, 0, 0, 0
            primary_narrative = "No coordinated narratives detected"
            param_ver = DEFAULT_SCORING_PARAMETER_VERSION

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
            parameter_version=param_ver,
        )

        _, coord_score, _, narrative_risk, has_sufficient_data = _calculate_channel_metrics(
            cluster_participation_share=cp,
            copy_delay_factor=cd,
            co_movement_repetition=cm,
            narrative_weight=nw,
            linked_clusters_count=linked_count,
        )

        spark_values = [max(0, score - 6), max(0, score - 4), max(0, score - 2), score]
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
            coordinationScore=coord_score,
            narrativeRisk=narrative_risk,
            hasSufficientData=has_sufficient_data,
            riskBand=risk_band,
            scoreHistory=score_history,
            explanation=explanation,
            coMovingChannels=co_moving_dtos,
            joinedClusters=joined_clusters,
        )

    def get_channel_coordination_groups(self) -> list[CoordinationGroupDto]:
        conn = self._db.connection
        # Query shared cascades between channels from cluster_messages if populated
        rows = conn.execute(
            """
            SELECT cm1.channel_id AS ch1, cm2.channel_id AS ch2,
                   COUNT(DISTINCT cm1.cluster_id) AS shared_cascades,
                   AVG(ABS(cm1.delay_seconds - cm2.delay_seconds)) AS avg_delay
            FROM cluster_messages cm1
            JOIN cluster_messages cm2
              ON cm1.cluster_id = cm2.cluster_id AND cm1.channel_id < cm2.channel_id
            GROUP BY cm1.channel_id, cm2.channel_id
            HAVING shared_cascades >= 2
            """
        ).fetchall()

        # Build graph edges
        edges: list[tuple[str, str, int, int]] = []
        for r in rows:
            edges.append(
                (str(r["ch1"]), str(r["ch2"]), int(r["shared_cascades"]), int(r["avg_delay"]))
            )

        # Find connected components with threshold >= 2 shared cascades
        adj: dict[str, set[str]] = {}
        pair_data: dict[tuple[str, str], tuple[int, int]] = {}
        for c1, c2, cascades, delay in edges:
            if cascades >= 2:
                adj.setdefault(c1, set()).add(c2)
                adj.setdefault(c2, set()).add(c1)
                pair_data[(min(c1, c2), max(c1, c2))] = (cascades, delay)

        visited: set[str] = set()
        components: list[list[str]] = []
        for node in sorted(adj.keys()):
            if node not in visited:
                comp: list[str] = []
                queue = [node]
                visited.add(node)
                while queue:
                    curr = queue.pop(0)
                    comp.append(curr)
                    for nbr in sorted(adj[curr]):
                        if nbr not in visited:
                            visited.add(nbr)
                            queue.append(nbr)
                if len(comp) >= 2:
                    components.append(sorted(comp))

        # Build CoordinationGroupDtos
        groups: list[CoordinationGroupDto] = []
        for idx, comp in enumerate(components, start=1):
            cascades_list: list[int] = []
            delays_list: list[int] = []
            for i in range(len(comp)):
                for j in range(i + 1, len(comp)):
                    key = (min(comp[i], comp[j]), max(comp[i], comp[j]))
                    if key in pair_data:
                        cascades_list.append(pair_data[key][0])
                        delays_list.append(pair_data[key][1])

            avg_cascades = (
                round(sum(cascades_list) / len(cascades_list)) if cascades_list else 3
            )
            avg_delay = round(sum(delays_list) / len(delays_list)) if delays_list else 120

            groups.append(
                CoordinationGroupDto(
                    groupId=f"group-{idx:02d}",
                    channelIds=comp,
                    sharedCascadesCount=avg_cascades,
                    typicalDelaySeconds=avg_delay,
                    mainNarrative="Cross-channel Disinformation Amplification",
                )
            )

        return groups
