"""Clustering service v2 with average-linkage and diameter cuts to prevent cluster chaining."""

import hashlib
from collections import defaultdict
from datetime import datetime
from typing import Protocol

from app.core.errors import AppError
from app.dtos.cluster_dto import (
    ClusterChannelAvatarDto,
    ClusterDetailDto,
    ClusterMessageComparisonDto,
    ClusterSummaryDto,
    SimilarityEdgeDto,
)
from app.dtos.collector_dto import StoredMessageDto
from app.repositories.cluster_repository import IClusterRepository
from app.repositories.message_repository import IMessageRepository
from app.repositories.user_repository import IParameterRepository
from app.services.narrative_classifier_service import INarrativeClassifierService
from app.services.similarity_service import ISimilarityService


def _parse_iso_seconds(iso_str: str) -> int:
    cleaned = iso_str.strip().replace("Z", "+00:00")
    try:
        return int(datetime.fromisoformat(cleaned).timestamp())
    except ValueError:
        return 0


def infer_narrative_category(normalised_text: str) -> str:
    """Assigns one of the disinformation narrative categories based on topic markers."""
    tokens = normalised_text.lower()
    if any(k in tokens for k in ("tarif", "gaz", "energie", "тариф", "газ", "свет", "inflat")):
        return "Sanctions, energy prices and economy fear"
    if any(k in tokens for k in ("bruxelles", "uniunea", "евросоюз", "ес", "брюссел")):
        return 'Anti-EU / "Europe is falling apart"'
    if any(k in tokens for k in ("nato", "нато", "militar", "учения")):
        return "Anti-NATO / anti-West"
    if any(k in tokens for k in ("alegeri", "vot", "выбор", "участк", "guvern")):
        return "Moldova government and elections delegitimisation"
    if any(k in tokens for k in ("gagauz", "transnistria", "приднестров", "гагауз", "тираспол")):
        return "Transnistria / Gagauzia and separatism"
    if any(k in tokens for k in ("banc", "depozit", "банк", "вклад")):
        return "Financial panic and banking runs"
    if any(k in tokens for k in ("mobiliz", "recrut", "mobilizare", "мобилизац", "повестк")):
        return "Forced mobilization rumors"
    return "Other / not disinformation"


class IClusteringService(Protocol):
    def detect_and_store_clusters(
        self,
        similarity_threshold: float | None = None,
        time_window_minutes: int | None = None,
    ) -> list[ClusterDetailDto]: ...
    def list_clusters(self) -> list[ClusterSummaryDto]: ...
    def get_cluster_detail(self, cluster_id: str) -> ClusterDetailDto: ...


class ClusteringService:
    """Groups similar cross-channel messages into reproducible cascades via average linkage."""

    def __init__(
        self,
        message_repo: IMessageRepository,
        cluster_repo: IClusterRepository,
        param_repo: IParameterRepository,
        similarity_service: ISimilarityService,
        narrative_classifier: INarrativeClassifierService | None = None,
    ) -> None:
        self._message_repo = message_repo
        self._cluster_repo = cluster_repo
        self._param_repo = param_repo
        self._similarity = similarity_service
        self._narrative_classifier = narrative_classifier

    def detect_and_store_clusters(
        self,
        similarity_threshold: float | None = None,
        time_window_minutes: int | None = None,
    ) -> list[ClusterDetailDto]:
        params = self._param_repo.get_latest()
        threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else params.similarity_threshold
        )
        window_mins = (
            time_window_minutes if time_window_minutes is not None else params.time_window_minutes
        )

        messages = self._message_repo.list_messages(limit=1000)
        msg_by_id: dict[str, StoredMessageDto] = {m.id: m for m in messages}

        edges = self._similarity.detect_similar_pairs(
            messages=messages,
            threshold=threshold,
            time_window_minutes=window_mins,
            parameter_version=params.parameter_version,
        )

        components = self._cluster_messages(
            edges=edges,
            msg_by_id=msg_by_id,
            min_similarity_cut=0.75,
            max_time_span_minutes=180,
        )
        clusters: list[ClusterDetailDto] = []

        for comp_msg_ids in components:
            comp_messages = sorted(
                (msg_by_id[mid] for mid in comp_msg_ids if mid in msg_by_id),
                key=lambda m: (m.posted_at, m.id),
            )
            distinct_channels = {m.channel_id for m in comp_messages}
            if len(distinct_channels) < 2:
                continue

            comp_edges = [
                e
                for e in edges
                if e.source_message_id in comp_msg_ids and e.target_message_id in comp_msg_ids
            ]
            avg_sim = (
                round(
                    sum(e.similarity_score for e in comp_edges) / len(comp_edges),
                    4,
                )
                if comp_edges
                else 1.0
            )

            first_msg = comp_messages[0]
            last_msg = comp_messages[-1]
            first_ts = _parse_iso_seconds(first_msg.posted_at)
            last_ts = _parse_iso_seconds(last_msg.posted_at)
            span_minutes = max(1, round(abs(last_ts - first_ts) / 60))

            # Deterministic cluster/cascade ID from sorted member message IDs
            sorted_ids_key = "|".join(sorted(comp_msg_ids))
            cluster_hash = hashlib.sha256(sorted_ids_key.encode("utf-8")).hexdigest()[:10]
            cluster_id = f"cl-{cluster_hash}"

            n_channels = len(distinct_channels)
            headline = f"Same message posted by {n_channels} channels in {span_minutes} minutes"
            category = infer_narrative_category(first_msg.normalised_text)
            if self._narrative_classifier is not None:
                try:
                    pred = self._narrative_classifier.classify_one(
                        target_id=cluster_id,
                        target_type="cluster",
                        raw_text=first_msg.normalised_text,
                    )
                    if pred.category != "Other / not disinformation":
                        category = pred.category
                except Exception:
                    pass
            snippet = (first_msg.raw_text or first_msg.normalised_text)[:180]

            base_words = set(first_msg.normalised_text.split())
            comparison_items: list[ClusterMessageComparisonDto] = []
            avatars: list[ClusterChannelAvatarDto] = []
            seen_channels: set[str] = set()

            for m in comp_messages:
                delay_sec = max(0, _parse_iso_seconds(m.posted_at) - first_ts)
                diff_words = [
                    w for w in m.normalised_text.split() if w not in base_words and len(w) > 2
                ]
                comparison_items.append(
                    ClusterMessageComparisonDto(
                        messageId=m.id,
                        channelId=m.channel_id,
                        handle=f"@{m.channel_id}",
                        title=m.channel_id,
                        postedAt=m.posted_at,
                        delaySeconds=delay_sec,
                        similarityScore=avg_sim if m.id != first_msg.id else 1.0,
                        isDeleted=m.is_deleted_at_source,
                        rawText=m.raw_text,
                        normalisedText=m.normalised_text,
                        normalisedHash=m.text_hash,
                        telegramUrl=f"https://t.me/{m.channel_id}/{m.telegram_message_id}",
                        changedPhrases=diff_words[:5],
                    )
                )
                if m.channel_id not in seen_channels:
                    seen_channels.add(m.channel_id)
                    avatars.append(
                        ClusterChannelAvatarDto(
                            channelId=m.channel_id,
                            handle=f"@{m.channel_id}",
                            title=m.channel_id,
                            initials=m.channel_id[:2].upper(),
                        )
                    )

            clusters.append(
                ClusterDetailDto(
                    id=cluster_id,
                    headlineSummary=headline,
                    narrativeCategory=category,
                    channelsCount=n_channels,
                    messagesCount=len(comp_messages),
                    windowMinutes=span_minutes,
                    averageSimilarity=avg_sim,
                    firstPostedAt=first_msg.posted_at,
                    lastPostedAt=last_msg.posted_at,
                    representativeSnippet=snippet,
                    channels=avatars,
                    parameterVersion=params.parameter_version,
                    messages=comparison_items,
                )
            )

        clusters.sort(key=lambda c: (c.first_posted_at, c.id), reverse=True)
        self._cluster_repo.save_edges_and_clusters(edges=edges, clusters=clusters)
        return [self._cluster_repo.get_cluster_detail(c.id) or c for c in clusters]

    def list_clusters(self) -> list[ClusterSummaryDto]:
        return self._cluster_repo.list_clusters()

    def get_cluster_detail(self, cluster_id: str) -> ClusterDetailDto:
        detail = self._cluster_repo.get_cluster_detail(cluster_id)
        if detail is None:
            raise AppError(
                code="CLUSTER_NOT_FOUND",
                message=f"Cluster '{cluster_id}' was not found.",
                status_code=404,
            )
        return detail

    @classmethod
    def _connected_components(cls, edges: list[SimilarityEdgeDto]) -> list[set[str]]:
        """Legacy helper for connected components, delegating to bounded graph partitioning."""
        adj: dict[str, set[str]] = defaultdict(set)
        nodes: set[str] = set()
        for edge in edges:
            adj[edge.source_message_id].add(edge.target_message_id)
            adj[edge.target_message_id].add(edge.source_message_id)
            nodes.add(edge.source_message_id)
            nodes.add(edge.target_message_id)

        visited: set[str] = set()
        components: list[set[str]] = []

        for node in sorted(nodes):
            if node in visited:
                continue
            comp: set[str] = set()
            queue = [node]
            visited.add(node)
            while queue:
                curr = queue.pop(0)
                comp.add(curr)
                for neighbor in sorted(adj[curr]):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            components.append(comp)

        return components

    @staticmethod
    def _cluster_messages(
        edges: list[SimilarityEdgeDto],
        msg_by_id: dict[str, StoredMessageDto],
        min_similarity_cut: float = 0.75,
        max_time_span_minutes: int = 180,
    ) -> list[set[str]]:
        """Average-linkage agglomerative clustering with diameter and time horizon constraints."""
        sim_map: dict[tuple[str, str], float] = {}
        nodes: set[str] = set()
        for edge in edges:
            u, v = edge.source_message_id, edge.target_message_id
            pair = (u, v) if u < v else (v, u)
            sim_map[pair] = max(sim_map.get(pair, 0.0), edge.similarity_score)
            nodes.add(u)
            nodes.add(v)

        clusters: list[set[str]] = [{n} for n in sorted(nodes)]

        merged = True
        while merged and len(clusters) > 1:
            merged = False
            best_pair = None
            best_sim = -1.0

            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    c1, c2 = clusters[i], clusters[j]
                    all_ts = [
                        _parse_iso_seconds(msg_by_id[m].posted_at)
                        for m in (c1 | c2)
                        if m in msg_by_id
                    ]
                    if all_ts and (max(all_ts) - min(all_ts)) > max_time_span_minutes * 60:
                        continue

                    pair_sims = []
                    valid_diameter = True
                    for u in c1:
                        for v in c2:
                            p = (u, v) if u < v else (v, u)
                            s = sim_map.get(p, 0.0)
                            pair_sims.append(s)
                            if s < 0.50:
                                valid_diameter = False
                                break
                        if not valid_diameter:
                            break

                    if not valid_diameter or not pair_sims:
                        continue

                    avg_s = sum(pair_sims) / len(pair_sims)
                    if avg_s >= min_similarity_cut and avg_s > best_sim:
                        best_sim = avg_s
                        best_pair = (i, j)

            if best_pair is not None:
                i, j = best_pair
                merged_cluster = clusters[i] | clusters[j]
                clusters = [c for idx, c in enumerate(clusters) if idx not in (i, j)]
                clusters.append(merged_cluster)
                merged = True

        return clusters
