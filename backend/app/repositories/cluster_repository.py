"""Repository layer for similarity edges and coordinated message clusters."""

from typing import Protocol, cast

from app.db.database import DatabaseManager
from app.dtos.cluster_dto import (
    ClusterChannelAvatarDto,
    ClusterChannelParticipantDto,
    ClusterDetailDto,
    ClusterMessageComparisonDto,
    ClusterSummaryDto,
    SimilarityEdgeDto,
)
from app.services.timeline_service import (
    build_dynamic_timeline,
    format_chisinau_datetime,
    format_chisinau_time,
    parse_utc_timestamp,
)


class IClusterRepository(Protocol):
    def save_edges_and_clusters(
        self,
        edges: list[SimilarityEdgeDto],
        clusters: list[ClusterDetailDto],
    ) -> None: ...
    def list_clusters(self) -> list[ClusterSummaryDto]: ...
    def get_cluster_detail(self, cluster_id: str) -> ClusterDetailDto | None: ...


class SqliteClusterRepository:
    """Persists similarity graph edges and deterministic connected-component clusters."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db = db_manager
        self._db.run_migrations()

    def save_edges_and_clusters(
        self,
        edges: list[SimilarityEdgeDto],
        clusters: list[ClusterDetailDto],
    ) -> None:
        cursor = self._db.connection.cursor()
        for edge in edges:
            cursor.execute(
                """
                INSERT OR REPLACE INTO similarity_edges (
                    id, source_message_id, target_message_id,
                    source_channel_id, target_channel_id,
                    similarity_score, match_stage, time_diff_seconds, parameter_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    edge.id,
                    edge.source_message_id,
                    edge.target_message_id,
                    edge.source_channel_id,
                    edge.target_channel_id,
                    edge.similarity_score,
                    edge.match_stage,
                    edge.time_diff_seconds,
                    edge.parameter_version,
                ),
            )

        new_cluster_ids = {c.id for c in clusters}
        cursor.execute("SELECT id FROM clusters")
        existing_ids = {row[0] for row in cursor.fetchall()}
        stale_ids = existing_ids - new_cluster_ids
        for stale in stale_ids:
            cursor.execute("DELETE FROM cluster_messages WHERE cluster_id = ?", (stale,))
            cursor.execute("DELETE FROM clusters WHERE id = ?", (stale,))

        for cluster in clusters:
            cursor.execute(
                """
                INSERT OR REPLACE INTO clusters (
                    id, headline_summary, narrative_category,
                    channels_count, messages_count, window_minutes,
                    average_similarity, first_posted_at, last_posted_at,
                    representative_snippet, parameter_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cluster.id,
                    cluster.headline_summary,
                    cluster.narrative_category,
                    cluster.channels_count,
                    cluster.messages_count,
                    cluster.window_minutes,
                    cluster.average_similarity,
                    cluster.first_posted_at,
                    cluster.last_posted_at,
                    cluster.representative_snippet,
                    cluster.parameter_version,
                ),
            )
            cursor.execute(
                "DELETE FROM cluster_messages WHERE cluster_id = ?",
                (cluster.id,),
            )
            for msg in cluster.messages:
                cursor.execute(
                    """
                    INSERT INTO cluster_messages (
                        cluster_id, message_id, channel_id, delay_seconds, similarity_to_centroid
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        cluster.id,
                        msg.message_id,
                        msg.channel_id,
                        msg.delay_seconds,
                        msg.similarity_score,
                    ),
                )
        self._db.connection.commit()

    def list_clusters(self) -> list[ClusterSummaryDto]:
        cursor = self._db.connection.cursor()
        cursor.execute("SELECT * FROM clusters ORDER BY first_posted_at DESC, id ASC")
        rows = cursor.fetchall()
        return [self._row_to_summary(row) for row in rows]

    def get_cluster_detail(self, cluster_id: str) -> ClusterDetailDto | None:
        cursor = self._db.connection.cursor()
        cursor.execute("SELECT * FROM clusters WHERE id = ? LIMIT 1", (cluster_id,))
        row = cursor.fetchone()
        if not row:
            return None
        summary = self._row_to_summary(row)
        raw_records = self._load_raw_cluster_records(cluster_id)
        return build_dynamic_timeline(summary, raw_records)

    def _row_to_summary(self, row: object) -> ClusterSummaryDto:
        mapping = cast(dict[str, object], row)
        cluster_id = str(mapping["id"])
        channels = self._load_cluster_channels(cluster_id)
        participants = self._load_cluster_participants(cluster_id)
        win_min = int(str(mapping["window_minutes"]))
        first_posted = str(mapping["first_posted_at"])
        last_posted = str(mapping["last_posted_at"])

        # Format first and last posted times in Europe/Chisinau
        first_display = format_chisinau_datetime(parse_utc_timestamp(first_posted))
        last_display = format_chisinau_datetime(parse_utc_timestamp(last_posted))

        return ClusterSummaryDto(
            id=cluster_id,
            headlineSummary=str(mapping["headline_summary"]),
            narrativeCategory=str(mapping["narrative_category"]),
            narrativeConfidence=0.92,
            channelsCount=int(str(mapping["channels_count"])),
            messagesCount=int(str(mapping["messages_count"])),
            windowMinutes=win_min,
            spanMinutes=win_min,
            averageSimilarity=float(str(mapping["average_similarity"])),
            matchType="semantic",
            firstPostedAt=first_display,
            lastPostedAt=last_display,
            representativeSnippet=str(mapping["representative_snippet"]),
            channels=channels,
            participants=participants,
            parameterVersion=str(mapping["parameter_version"]),
        )

    def _load_cluster_participants(self, cluster_id: str) -> list[ClusterChannelParticipantDto]:
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            SELECT
                cm.channel_id, cm.delay_seconds, cm.similarity_to_centroid,
                m.posted_at,
                COALESCE(w.handle, '@' || cm.channel_id) AS handle,
                COALESCE(w.title, cm.channel_id) AS title
            FROM cluster_messages cm
            INNER JOIN messages m ON m.id = cm.message_id
            LEFT JOIN watchlist_channels w ON w.id = cm.channel_id
            WHERE cm.cluster_id = ?
            ORDER BY m.posted_at ASC
            """,
            (cluster_id,),
        )
        participants: list[ClusterChannelParticipantDto] = []
        for row in cursor.fetchall():
            mapping = cast(dict[str, object], row)
            title_str = str(mapping["title"])
            words = [w for w in title_str.replace("@", "").split() if w]
            initials = (
                (words[0][0] + (words[1][0] if len(words) > 1 else words[0][-1])).upper()
                if words
                else "CH"
            )
            dt_utc = parse_utc_timestamp(str(mapping["posted_at"]))
            participants.append(
                ClusterChannelParticipantDto(
                    channelId=str(mapping["channel_id"]),
                    handle=str(mapping["handle"]),
                    title=title_str,
                    initials=initials,
                    postedAt=format_chisinau_time(dt_utc),
                    delaySeconds=int(str(mapping["delay_seconds"])),
                    similarityScore=float(str(mapping["similarity_to_centroid"])),
                )
            )
        return participants

    def _load_cluster_channels(self, cluster_id: str) -> list[ClusterChannelAvatarDto]:
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            SELECT DISTINCT
                cm.channel_id,
                COALESCE(w.handle, '@' || cm.channel_id) AS handle,
                COALESCE(w.title, cm.channel_id) AS title
            FROM cluster_messages cm
            LEFT JOIN watchlist_channels w ON w.id = cm.channel_id
            WHERE cm.cluster_id = ?
            ORDER BY cm.channel_id ASC
            """,
            (cluster_id,),
        )
        avatars: list[ClusterChannelAvatarDto] = []
        for row in cursor.fetchall():
            mapping = cast(dict[str, object], row)
            title_str = str(mapping["title"])
            words = [w for w in title_str.replace("@", "").split() if w]
            initials = (
                (words[0][0] + (words[1][0] if len(words) > 1 else words[0][-1])).upper()
                if words
                else "CH"
            )
            avatars.append(
                ClusterChannelAvatarDto(
                    channelId=str(mapping["channel_id"]),
                    handle=str(mapping["handle"]),
                    title=title_str,
                    initials=initials,
                )
            )
        return avatars

    def _load_raw_cluster_records(self, cluster_id: str) -> list[dict[str, object]]:
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            SELECT
                cm.message_id, cm.channel_id, cm.delay_seconds,
                cm.similarity_to_centroid AS similarity_score,
                m.telegram_message_id, m.posted_at, m.is_deleted_at_source,
                t.raw_text,
                n.normalised_text, n.text_hash,
                COALESCE(w.handle, '@' || cm.channel_id) AS handle,
                COALESCE(w.title, cm.channel_id) AS title
            FROM cluster_messages cm
            INNER JOIN messages m ON m.id = cm.message_id
            INNER JOIN message_norm n ON n.message_id = cm.message_id
            LEFT JOIN message_texts t ON t.message_id = cm.message_id
            LEFT JOIN watchlist_channels w ON w.id = cm.channel_id
            WHERE cm.cluster_id = ?
            ORDER BY m.posted_at ASC, cm.message_id ASC
            """,
            (cluster_id,),
        )
        rows = cursor.fetchall()
        return [dict(cast(dict[str, object], r)) for r in rows]

    def _load_cluster_messages(self, cluster_id: str) -> list[ClusterMessageComparisonDto]:
        raw = self._load_raw_cluster_records(cluster_id)
        if not raw:
            return []
        first_norm = str(raw[0].get("normalised_text", ""))
        base_words = set(first_norm.split())
        comparisons: list[ClusterMessageComparisonDto] = []

        for mapping in raw:
            handle = str(mapping["handle"])
            tg_id = int(str(mapping.get("telegram_message_id", 1)))
            norm_text = str(mapping.get("normalised_text", ""))
            raw_val = mapping.get("raw_text")
            diff_words = [w for w in norm_text.split() if w not in base_words and len(w) > 2]
            comparisons.append(
                ClusterMessageComparisonDto(
                    messageId=str(mapping["message_id"]),
                    channelId=str(mapping["channel_id"]),
                    handle=handle,
                    title=str(mapping["title"]),
                    postedAt=str(mapping["posted_at"]),
                    delaySeconds=int(str(mapping["delay_seconds"])),
                    similarityScore=float(str(mapping["similarity_score"])),
                    isDeleted=bool(int(str(mapping["is_deleted_at_source"]))),
                    rawText=str(raw_val) if raw_val is not None else None,
                    normalisedText=norm_text,
                    normalisedHash=str(mapping["text_hash"]),
                    telegramUrl=f"https://t.me/{handle.lstrip('@')}/{tg_id}",
                    changedPhrases=diff_words[:5],
                )
            )
        return comparisons
